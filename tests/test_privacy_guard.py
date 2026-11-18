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
