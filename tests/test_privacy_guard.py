"""Privacy-guard scenarios of the `user-workspace` spec, in a throwaway git repo."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PRIVATE_TERM = "Marisol Quispe Tanaka"  # the fictional persona


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    shutil.copy(REPO / "scripts" / "check_private.py", root / "scripts" / "check_private.py")
    shutil.copy(REPO / ".gitignore", root / ".gitignore")
    for command in (["init", "-q"], ["config", "user.email", "t@example.test"],
                    ["config", "user.name", "Test"]):
        subprocess.run(["git", *command], cwd=root, check=True)
    (root / "user-data").mkdir()
    (root / "user-data" / ".private-terms").write_text(PRIVATE_TERM + "\n", encoding="utf-8")
    return root


def _stage(root: Path, name: str, content: str = "hello\n", force: bool = False) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", *(["-f"] if force else []), name], cwd=root, check=True)


def _guard(root: Path, *args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "JOBTRACKER_HOME"}
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "check_private.py"), *args],
        cwd=root, capture_output=True, text=True, env=env,
    )


def test_private_home_is_ignored_by_git(repo):
    (repo / "user-data" / "resume.txt").write_text("x", encoding="utf-8")
    status = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=repo,
                            capture_output=True, text=True).stdout
    assert "user-data" not in status


def test_staged_file_inside_the_private_home_is_rejected(repo):
    _stage(repo, "user-data/profile/notes.txt", force=True)
    result = _guard(repo)
    assert result.returncode == 1
    assert "user-data/profile/notes.txt" in result.stderr


def test_a_private_provider_is_never_committed(repo):
    _stage(repo, "user-data/providers/acme-jobs.study.md", force=True)
    result = _guard(repo)
    assert result.returncode == 1
    assert "user-data/providers/acme-jobs.study.md" in result.stderr


@pytest.mark.parametrize("name", ["resume.pdf", "docs/My CV.docx", "data/jobs.db"])
def test_resume_and_database_files_are_rejected(repo, name):
    _stage(repo, name, force=True)
    result = _guard(repo)
    assert result.returncode == 1
    assert name in result.stderr


def test_fixture_documents_are_allowed(repo):
    _stage(repo, "tests/fixtures/resume.pdf")
    assert _guard(repo).returncode == 0


def test_private_term_is_rejected_without_being_revealed(repo):
    _stage(repo, "src/example.py", f"AUTHOR = '{PRIVATE_TERM.upper()}'\n")
    result = _guard(repo)
    assert result.returncode == 1
    assert "src/example.py" in result.stderr
    assert PRIVATE_TERM.lower() not in (result.stderr + result.stdout).lower()


def test_clean_commit_is_allowed(repo):
    _stage(repo, "src/example.py", "print('hello')\n")
    result = _guard(repo)
    assert result.returncode == 0, result.stderr


def test_all_mode_checks_tracked_files(repo):
    _stage(repo, "src/example.py", f"# {PRIVATE_TERM}\n")
    subprocess.run(["git", "commit", "-q", "-m", "x"], cwd=repo, check=True)
    assert _guard(repo).returncode == 0  # nothing staged
    assert _guard(repo, "--all").returncode == 1


def test_this_repository_is_clean():
    result = subprocess.run([sys.executable, str(REPO / "scripts" / "check_private.py"), "--all"],
                            cwd=REPO, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


# ── the hook finds a working Python (fix-python-on-windows) ───────────────

HOOK = REPO / ".githooks" / "pre-commit"
SHELL = shutil.which("sh") or shutil.which("bash")
needs_shell = pytest.mark.skipif(SHELL is None, reason="needs a POSIX shell to run the hook")


def _bin(tmp_path: Path, name: str, body: str) -> Path:
    """A fake command on a private PATH (a shell script, also on Windows' Git Bash)."""
    folder = tmp_path / "bin"
    folder.mkdir(exist_ok=True)
    path = folder / name
    path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8", newline="\n")
    path.chmod(0o755)
    return folder


def _hook(root: Path, path_dirs: list[Path]) -> subprocess.CompletedProcess:
    shutil.copy(HOOK, root / "pre-commit")
    git_dir = Path(shutil.which("git")).parent
    sh_dir = Path(SHELL).parent
    env = {k: v for k, v in os.environ.items() if k not in ("JOBTRACKER_HOME", "PATH")}
    env["PATH"] = os.pathsep.join(str(p) for p in [*path_dirs, git_dir, sh_dir])
    return subprocess.run([SHELL, str(root / "pre-commit")], cwd=root, capture_output=True,
                          text=True, env=env)


def _real_python(tmp_path: Path, name: str) -> Path:
    """A command that runs the real interpreter (what a working `python` does)."""
    return _bin(tmp_path, name, f'exec "{Path(sys.executable).as_posix()}" "$@"')


@needs_shell
def test_hook_uses_the_project_environment_when_python_on_the_path_is_a_store_alias(
        repo, tmp_path):
    stub = _bin(tmp_path, "python3", 'echo "Python was not found; run without arguments to '
                                     'install from the Microsoft Store" >&2; exit 9009')
    _bin(tmp_path, "python", "exit 9009")
    venv = repo / ".venv" / "bin"
    venv.mkdir(parents=True)
    (venv / "python").write_text(f'#!/bin/sh\nexec "{Path(sys.executable).as_posix()}" "$@"\n',
                                 encoding="utf-8", newline="\n")
    (venv / "python").chmod(0o755)
    _stage(repo, "user-data/notes.txt", force=True)
    result = _hook(repo, [stub])
    assert result.returncode == 1 and "user-data/notes.txt" in result.stderr   # it ran the check


@needs_shell
def test_hook_skips_a_store_alias_and_uses_a_real_python(repo, tmp_path):
    folder = _bin(tmp_path, "python3", "exit 9009")
    _real_python(tmp_path, "python")
    _stage(repo, "src/app.py", "print('ok')\n")
    result = _hook(repo, [folder])
    assert result.returncode == 0, result.stderr


@needs_shell
def test_hook_without_any_python_blocks_with_a_clear_message(repo, tmp_path):
    folder = _bin(tmp_path, "python3", "exit 9009")
    _bin(tmp_path, "python", "exit 9009")
    _stage(repo, "src/app.py", "print('ok')\n")
    result = _hook(repo, [folder])
    assert result.returncode == 1
    assert "no working Python 3.11+ found" in result.stderr and "/setup" in result.stderr


def test_doctor_finds_the_hook_python_in_the_hooks_order(tmp_path, monkeypatch):
    from jobtracker.core import doctor

    venv = tmp_path / ".venv" / "Scripts"
    venv.mkdir(parents=True)
    (venv / "python.exe").write_text("", encoding="utf-8")
    real = {"python": "/usr/real/python"}
    monkeypatch.setattr(doctor.shutil, "which", lambda name: {"python3": "/store/python3",
                                                               **real}.get(name))
    monkeypatch.setattr(doctor, "_runs_python",
                        lambda command: "store" not in command[0])
    assert doctor.hook_python(tmp_path) == str(venv / "python.exe")      # the project first
    (venv / "python.exe").unlink()
    assert doctor.hook_python(tmp_path) == "/usr/real/python"            # the alias is skipped
    real.clear()
    assert doctor.hook_python(tmp_path) is None


def test_doctor_reports_a_guard_without_python(workspace, cli, monkeypatch):
    from jobtracker.core import doctor

    monkeypatch.setattr(doctor, "hook_python", lambda root=None: None)
    _, out, _ = cli("doctor")
    check = next(c for c in out["checks"] if c["id"] == "privacy_guard_python")
    assert check["status"] == "fail" and "Microsoft Store" in check["detail"]
    assert "/setup" in check["fix"]
