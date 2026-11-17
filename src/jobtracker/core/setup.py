"""Progress of the first-run setup, so it can be resumed and revised."""
from __future__ import annotations

import sqlite3

from .db import bump_changes, now_iso
from .errors import JobTrackerError

STEPS: tuple[tuple[str, str], ...] = (
    ("environment", "Requirements checked and installed"),
    ("language", "Panel language chosen"),
    ("workspace", "Private workspace created"),
    ("privacy", "Private terms registered for the privacy guard"),
    ("resume", "Base resume imported and confirmed by the user"),
    ("questionnaire", "Job needs collected"),
    ("titles", "Target titles researched and confirmed"),
    ("providers", "Job sites selected"),
    ("preferences", "Standing preferences recorded as rules"),
    ("tour", "Guided tour given"),
)
STEP_IDS = tuple(step for step, _ in STEPS)
_PREFIX = "setup.step."


def _check(step: str) -> None:
    if step not in STEP_IDS:
        raise JobTrackerError(
            "invalid_step", f"'{step}' is not a setup step. Steps: {', '.join(STEP_IDS)}"
        )


def status(conn: sqlite3.Connection) -> dict:
    done = {
        row["key"][len(_PREFIX):]: row["value"]
        for row in conn.execute("SELECT key, value FROM settings WHERE key LIKE ?",
                                (_PREFIX + "%",))
    }
    steps = [
        {"step": step, "description": description, "done": step in done,
         "done_at": done.get(step)}
        for step, description in STEPS
    ]
    pending = [item["step"] for item in steps if not item["done"]]
    return {"steps": steps, "next_step": pending[0] if pending else None,
            "complete": not pending}


def mark_done(conn: sqlite3.Connection, steps: list[str]) -> dict:
    for step in steps:
        _check(step)
    for step in steps:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (_PREFIX + step, now_iso()),
        )
    bump_changes(conn)
    return summary(conn)


def summary(conn: sqlite3.Connection) -> dict:
    """The short form of `status`: what is done and what comes next."""
    full = status(conn)
    return {
        "done": [item["step"] for item in full["steps"] if item["done"]],
        "next_step": full["next_step"],
        "complete": full["complete"],
    }


def redo(conn: sqlite3.Connection, step: str) -> dict:
    """Mark a step as not done so /setup asks it again. Stored data is kept."""
    _check(step)
    conn.execute("DELETE FROM settings WHERE key = ?", (_PREFIX + step,))
    bump_changes(conn)
    return summary(conn)
