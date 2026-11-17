#!/usr/bin/env python3
"""Privacy guard: refuse to commit anything that looks like private user data.

Runs as the pre-commit hook (.githooks/pre-commit) and in CI. Standard library
only, so it works before any dependency is installed.

Usage:
    python scripts/check_private.py            # check staged files
    python scripts/check_private.py --all      # check every tracked file (CI)

A file is rejected when:
  1. it lives under a private directory (user-data/, user-data-*/);
  2. it has a document/database extension outside the allowlisted folders
     (resumes and databases are never source files);
  3. its content contains one of the user's private terms, listed one per line
     in user-data/.private-terms (written by /setup: name, email, phone...).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PRIVATE_DIR_PREFIXES = ("user-data/", "user-data-")
BLOCKED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".odt", ".rtf", ".pages",
    ".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3",
}
# Synthetic fixtures (fictional personas only) may use blocked extensions here.
EXTENSION_ALLOWLIST_PREFIXES = ("tests/fixtures/",)
MAX_SCAN_BYTES = 5 * 1024 * 1024


def git(*args: str) -> list[str]:
    out = subprocess.run(
        ["git", "-c", "core.quotepath=off", *args],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout.decode("utf-8", errors="replace")
    return [line for line in out.split("\0") if line]


def candidate_files(check_all: bool) -> list[str]:
    if check_all:
        return git("ls-files", "-z")
    return git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")


def private_home() -> Path:
    return Path(os.environ.get("JOBTRACKER_HOME") or ROOT / "user-data")


def load_private_terms() -> list[str]:
    path = private_home() / ".private-terms"
    if not path.is_file():
        return []
    terms = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        term = line.strip()
        if len(term) >= 4 and not term.startswith("#"):
            terms.append(term.lower())
    return terms


def staged_content(path: str, check_all: bool) -> bytes:
    if check_all:
        try:
            return (ROOT / path).read_bytes()[:MAX_SCAN_BYTES]
        except OSError:
            return b""
    result = subprocess.run(
        ["git", "show", f":{path}"], cwd=ROOT, capture_output=True
    )
    return result.stdout[:MAX_SCAN_BYTES]


def main() -> int:
    check_all = "--all" in sys.argv[1:]
    terms = load_private_terms()
    problems: list[str] = []

    for path in candidate_files(check_all):
        posix = path.replace("\\", "/")
        if posix.startswith(PRIVATE_DIR_PREFIXES):
            problems.append(f"{path}: inside a private user-data directory")
            continue
        suffix = Path(posix).suffix.lower()
        if suffix in BLOCKED_EXTENSIONS and not posix.startswith(
            EXTENSION_ALLOWLIST_PREFIXES
        ):
            problems.append(
                f"{path}: '{suffix}' files are not allowed outside "
                f"{', '.join(EXTENSION_ALLOWLIST_PREFIXES)}"
            )
            continue
        if terms:
            text = staged_content(path, check_all).decode("utf-8", errors="ignore").lower()
            hits = [t for t in terms if t in text]
            if hits:
                # Never echo the private term itself into logs.
                problems.append(f"{path}: contains {len(hits)} private term(s)")

    if problems:
        print("Privacy guard blocked this commit:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            "\nPrivate data belongs in user-data/ (see docs/workspace-layout.md).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
