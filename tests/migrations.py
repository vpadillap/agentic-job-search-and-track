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
    12: [
        "ALTER TABLE statuses ADD COLUMN stage TEXT NOT NULL DEFAULT 'applied'"
        " CHECK (stage IN ('to_apply', 'applied', 'interview', 'offer', 'closed_positive',"
        " 'closed_negative'))",
        "UPDATE statuses SET stage = CASE key WHEN 'new' THEN 'to_apply'"
        " WHEN 'interview' THEN 'interview' WHEN 'offer' THEN 'offer'"
        " WHEN 'accepted' THEN 'closed_positive' WHEN 'applied' THEN 'applied'"
        " ELSE CASE ends WHEN 1 THEN 'closed_negative' ELSE 'applied' END END",
        "ALTER TABLE statuses DROP COLUMN ends",
    ],
    13: [
        "CREATE TABLE application_snapshots (id INTEGER PRIMARY KEY, application_id TEXT NOT"
        " NULL UNIQUE, captured_at TEXT NOT NULL, data TEXT NOT NULL)",
        "DELETE FROM events WHERE kind = 'applied'",
        "ALTER TABLE applications DROP COLUMN offered_salary_basis",
        "ALTER TABLE applications DROP COLUMN offered_salary_currency",
        "ALTER TABLE applications DROP COLUMN offered_salary_amount",
    ],
    14: [
        "ALTER TABLE seasons DROP COLUMN closing",
        "DROP INDEX applications_season",
        "ALTER TABLE applications DROP COLUMN season_id",
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
