"""Update the clone from the repository without touching the user's data.

`check` fetches and reports what an update would bring; it changes nothing in the
working tree or the database. The pull itself is a visible git step the agent runs
(`git pull --ff-only origin main`). `finish` then leaves everything working:
packages, database schema, command names, the tools of enabled providers. Every step
is safe to run twice.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from . import config, db, doctor, installer, offers, skills
from .errors import JobTrackerError
from .paths import Paths, repo_root
from .workspace import is_initialized

REMOTE = "origin"
BRANCH = "main"
UPSTREAM = f"{REMOTE}/{BRANCH}"
MAX_SUBJECTS = 40

Runner = Callable[[list[str]], tuple[int, str]]


def _git(root: Path, *args: str, check: bool = True) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=300)
    except (OSError, subprocess.SubprocessError) as error:
        raise JobTrackerError("git_failed", f"git {args[0]} could not run: {error}") from error
    if check and result.returncode != 0:
        raise JobTrackerError("git_failed",
                              f"git {' '.join(args)} failed: {result.stderr.strip()[:400]}")
    return result.stdout


def _provider_files(names: list[str]) -> set[str]:
    skipped = {"_template.md", "contributing.md", "readme.md"}
    return {Path(n).name for n in names
            if n.endswith(".md") and "/" not in n.removeprefix("providers/")
            and Path(n).name.lower() not in skipped}


def _remote_schema(root: Path) -> int:
    listing = _git(root, "ls-tree", "--name-only", UPSTREAM, "src/jobtracker/core/migrations/")
    numbers = [int(m.group(1)) for line in listing.splitlines()
               if (m := re.match(r"^(\d{4})_.*\.sql$", Path(line).name))]
    return max(numbers, default=0)


def check(paths: Paths, root: Path | None = None) -> dict:
    """Fetch and describe the update. Never changes the working tree or the database."""
    root = root or repo_root()
    if not (root / ".git").exists():
        raise JobTrackerError("not_a_clone",
                              "This folder is not a git clone, so it cannot update itself.")
    _git(root, "fetch", "--quiet", REMOTE)
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    current = _git(root, "rev-parse", "HEAD").strip()
    remote = _git(root, "rev-parse", UPSTREAM).strip()
    behind = int(_git(root, "rev-list", "--count", f"HEAD..{UPSTREAM}").strip())
    ahead = int(_git(root, "rev-list", "--count", f"{UPSTREAM}..HEAD").strip())
    subjects = _git(root, "log", f"--max-count={MAX_SUBJECTS}", "--no-merges",
                    "--format=%h %s", f"HEAD..{UPSTREAM}").splitlines()
    tracked = [line[3:] for line in _git(root, "status", "--porcelain",
                                         "--untracked-files=no").splitlines() if line.strip()]
    here = _provider_files([p.name for p in (root / "providers").glob("*.md")])
    there = _provider_files(_git(root, "ls-tree", "--name-only", UPSTREAM,
                                 "providers/").splitlines())
    return {
        "branch": branch,
        "on_main": branch == BRANCH,
        "current": current,
        "remote": remote,
        "up_to_date": behind == 0,
        "behind": behind,
        "new_commits": subjects,
        "ahead": ahead,
        "fast_forward": branch == BRANCH and ahead == 0,
        "tracked_changes": tracked,
        "new_providers": sorted(p.removesuffix(".md") for p in there - here),
        "schema_from": db.stored_schema_version(paths.database),
        "schema_to": _remote_schema(root),
        "pull": f"git pull --ff-only {REMOTE} {BRANCH}",
        "restore": f"git reset --hard {current}",
    }


def _run(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=1800, check=False)
    return result.returncode, (result.stdout + result.stderr)[-4000:]


def _reinstall_command(root: Path) -> list[str] | None:
    """`uv sync --inexact` when the clone uses uv (it keeps the tools providers added),
    otherwise pip into the environment that runs this command; None without one."""
    if (root / "uv.lock").is_file() and shutil.which("uv") and (root / ".venv").is_dir():
        return ["uv", "sync", "--inexact"]
    if sys.prefix != sys.base_prefix:
        return [sys.executable, "-m", "pip", "install", "--quiet", "-e", str(root)]
    return None


def _newest_backup(paths: Paths) -> str | None:
    if not paths.backups.is_dir():
        return None
    found = sorted(paths.backups.glob("jobtracker-v*.db"), key=lambda p: p.stat().st_mtime)
    return str(found[-1]) if found else None


def finish(paths: Paths, root: Path | None = None, *, runner: Runner = _run,
           install_tools: Callable[[Paths], dict] | None = None) -> dict:
    """After the pull: reinstall, migrate, refresh command names, install the tools of
    enabled providers, and run the diagnostics. Stops at the first failing step."""
    root = root or repo_root()
    steps: list[dict] = []

    def done(step: str, ok: bool, **detail) -> bool:
        steps.append({"step": step, "ok": ok, **detail})
        return ok

    def result() -> dict:
        failed = next((s["step"] for s in steps if not s["ok"]), None)
        return {"ok_all": failed is None, "failed_step": failed, "steps": steps,
                "backup": _newest_backup(paths)}

    command = _reinstall_command(root)
    if command is None:
        done("packages", False, detail="no project environment (.venv) to install into",
             fix="Run /setup: it creates the project's environment.")
        return result()
    code, output = runner(command)
    if not done("packages", code == 0, command=" ".join(command),
                **({} if code == 0 else {"detail": output.strip()[-800:]})):
        return result()

    if not is_initialized(paths):
        done("database", True, detail="no workspace yet; /setup creates it")
        return result()
    before = db.stored_schema_version(paths.database)
    try:
        with db.session(paths) as conn:
            pending = offers.pending(conn, paths)
    except Exception as error:  # a failed migration leaves the backup to restore
        done("database", False, schema_from=before, detail=str(error)[:800])
        return result()
    done("database", True, schema_from=before, schema_to=db.current_schema_version())

    language = str(config.load(paths.config)["language"])
    done("command_names", True, **skills.sync(language))

    install = install_tools or (lambda p: installer.install(p, enabled=True))
    try:
        tools = install(paths)
    except JobTrackerError as error:
        done("provider_tools", False, detail=error.message)
        return result()
    failed_tools = [t for t in tools.get("providers", []) if not t.get("ok", True)]
    if not done("provider_tools", not failed_tools, result=tools):
        return result()

    report = doctor.run(paths)
    failing = [c for c in report["checks"] if c["status"] == "fail"]
    done("diagnostics", not failing, failing=failing)
    final = result()
    final["offers"] = pending
    return final
