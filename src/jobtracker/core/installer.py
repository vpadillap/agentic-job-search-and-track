"""Install what an enabled provider needs, so a search never fails because a tool is
missing: the agent runs `jt providers install`, the user never installs by hand.

Only the tools listed here are installed, into the Python that runs this command (the
project's own environment). Each install ends with a check that the tool really works,
and a tool whose package is already there counts only when that check passes; otherwise
its browser is installed again (browsers go to the folder `browsers.configure` chose).
"""
from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable

from . import browsers, doctor, providers
from .errors import JobTrackerError
from .paths import Paths

Runner = Callable[[list[str]], tuple[int, str]]

SMOKE_SCRAPLING = ("from scrapling.fetchers import StealthySession\n"
                   "s = StealthySession(headless=True)\n"
                   "s.__enter__()\n"
                   "s.__exit__(None, None, None)\n"
                   "print('ok')\n")
SMOKE_PLAYWRIGHT = ("from playwright.sync_api import sync_playwright\n"
                    "with sync_playwright() as p:\n"
                    "    p.chromium.launch(headless=True).close()\n"
                    "print('ok')\n")


def steps(tool: str) -> dict | None:
    """The commands that install `tool` (its package, then its browser) and the check
    that proves the browser really starts."""
    python = sys.executable
    known = {
        "scrapling": {
            "size": "about 150 MB (the package and its browser)",
            "package": [[python, "-m", "pip", "install", "scrapling[fetchers]"]],
            "browser": [[python, "-m", "patchright", "install", "chromium"]],
            "check": [python, "-c", SMOKE_SCRAPLING],
        },
        "playwright": {
            "size": "about 150 MB (the package and Chromium)",
            "package": [[python, "-m", "pip", "install", "playwright"]],
            "browser": [[python, "-m", "playwright", "install", "chromium"]],
            "check": [python, "-c", SMOKE_PLAYWRIGHT],
        },
    }
    return known.get(tool)


def _failure(command: list[str], output: str) -> str:
    """One readable line: which step failed and the error it gave (a browser's launch
    log is long; its first `Error` line says why)."""
    step = "the browser check" if command[1:2] == ["-c"] else f"`{' '.join(command[1:4])}…`"
    lines = [line.strip() for line in output.strip().splitlines() if line.strip()]
    errors = [line for line in lines if "Error" in line]
    reason = errors[-1] if errors else (lines[-1] if lines else "no output")
    return f"{step} failed: {reason[:400]}"


def run_command(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=1800,
                            check=False)
    return result.returncode, (result.stdout + result.stderr)[-50000:]  # _failure shortens it


def install(paths: Paths, provider_id: str | None = None, *, enabled: bool = False,
            runner: Runner = run_command) -> dict:
    """Install the missing tools of one provider, or of every enabled provider."""
    listed = {str(p["id"]): p for p in providers.list_providers()}
    if enabled:
        targets = sorted(doctor._enabled_provider_ids(paths) & set(listed))
    elif provider_id:
        if provider_id not in listed:
            raise JobTrackerError("not_found", f"There is no provider '{provider_id}'")
        targets = [provider_id]
    else:
        raise JobTrackerError("usage", "give a provider id, or --enabled")
    report = []
    done: dict[str, dict] = {}
    working: set[str] = set()  # checked in this call: not checked again
    for target in targets:
        item = {"provider": target, "installed": [], "already": [], "failed": [],
                "unknown": []}
        for tool in [str(d) for d in listed[target].get("dependencies") or []]:
            if tool in working:
                item["already"].append(tool)
                continue
            if tool in done:
                (item["installed"] if done[tool]["ok"] else item["failed"]).append(
                    done[tool] if not done[tool]["ok"] else tool)
                continue
            recipe = steps(tool)
            present = doctor._tool_available(tool)
            if present and recipe is None:
                item["already"].append(tool)
                continue
            if recipe is None:
                item["unknown"].append({"tool": tool, "how": providers.install_hint(
                    tool, str(listed[target]["file"]))})
                continue
            outcome = {"tool": tool, "ok": True, "size": recipe["size"], "detail": None}
            commands = [*recipe["package"], *recipe["browser"], recipe["check"]]
            if present:
                # The package imports; it counts only if its browser really starts.
                code, output = runner(recipe["check"])
                if code == 0:
                    working.add(tool)
                    item["already"].append(tool)
                    continue
                outcome["repaired"] = True
                outcome["was"] = _failure(recipe["check"], output)
                commands = [*recipe["browser"], recipe["check"]]
            for command in commands:
                code, output = runner(command)
                if code != 0:
                    outcome.update(ok=False, detail=_failure(command, output))
                    break
            done[tool] = outcome
            if outcome["ok"]:
                item["installed"].append(tool)
            else:
                item["failed"].append(outcome)
        item["ok"] = not item["failed"] and not item["unknown"]
        report.append(item)
    installed = sorted({tool for r in report for tool in r["installed"]})
    return {"providers": report, "installed": installed,
            "repaired": [tool for tool in installed if done[tool].get("repaired")],
            "sizes": {tool: done[tool]["size"] for tool in installed},
            "browsers": browsers.location(),
            "ok": all(r["ok"] for r in report)}
