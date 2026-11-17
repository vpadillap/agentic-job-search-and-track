"""Rewind a test database to an older schema version, to test a migration.

Each migration that a test rewinds past needs its undo here. When you add a
migration, add its undo (the reverse statements, newest first) so every test
that rewinds keeps working.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

UNDO: dict[int, list[str]] = {
    8: [
        "DROP INDEX base_resumes_one_current_per_language",
        "ALTER TABLE base_resumes DROP COLUMN language",
        "ALTER TABLE documents DROP COLUMN base_resume_id",
        "CREATE UNIQUE INDEX base_resumes_one_current ON base_resumes (is_current)"
        " WHERE is_current = 1",
    ],
    9: ["ALTER TABLE base_resumes DROP COLUMN translated_from"],
    10: [
        "ALTER TABLE postings DROP COLUMN work_mode_detail",
        "ALTER TABLE postings DROP COLUMN work_mode_source",
    ],
    11: [
        "DROP TABLE rule_influence",
        "DROP TABLE analyses",
        "DROP TABLE experiments",
        "ALTER TABLE rules DROP COLUMN candidate_key",
        "ALTER TABLE rules DROP COLUMN candidate_cases",
        "ALTER TABLE rules DROP COLUMN applied_at",
    ],
}
# 0008 adds `is_main` and 0009 drops it again, so undoing 9 then 8 leaves no
# `is_main` column: that matches a version-7 database.


def rewind(database: Path, version: int) -> None:
    """Undo every migration above `version` and set the schema version."""
    with closing(sqlite3.connect(database)) as conn:
        current = conn.execute("PRAGMA user_version").fetchone()[0]
        for number in range(current, version, -1):
            if number not in UNDO:
                raise AssertionError(f"tests/migrations.py has no undo for migration {number}")
            for statement in UNDO[number]:
                conn.execute(statement)
        conn.execute(f"PRAGMA user_version = {version}")
        conn.commit()
