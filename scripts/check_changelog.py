#!/usr/bin/env python3
"""Changelog check for pull requests: a change that touches what users run (code,
provider files, skills, command aliases) must add an entry to CHANGELOG.md.

Usage: python scripts/check_changelog.py <base ref>   (for example origin/main)
Exit 0 when fine, 1 with a message when an entry is missing. Standard library only.
"""
from __future__ import annotations

import subprocess
import sys

USER_FACING = ("src/", "providers/", ".claude/skills/", "i18n/", "scripts/jt.py")
CHANGELOG = "CHANGELOG.md"


def needs_entry(changed: list[str]) -> bool:
    """True when the changed files touch what users run and the changelog is not among them."""
    touched = any(path.startswith(USER_FACING) for path in changed)
    return touched and CHANGELOG not in changed


def changed_files(base: str) -> list[str]:
    result = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"],
                            capture_output=True, text=True, check=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    changed = changed_files(argv[1])
    if needs_entry(changed):
        print("CHANGELOG.md has no entry for this change. Add one at the top, in plain words "
              "for the user (see the format at the top of CHANGELOG.md): what was added, "
              "changed, or fixed, and the Providers / Offers / Action lines.", file=sys.stderr)
        return 1
    print("changelog: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
