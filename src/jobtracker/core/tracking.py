"""What the user decides about a posting: track it, mark it applied, or dismiss it.

Tracking creates the minimal application record (statuses, tags, and details
arrive with application tracking). Every action can be undone right after it.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta

from .db import bump_changes, now_iso
from .errors import JobTrackerError

DISMISS_REASONS = ("industry", "low_salary", "location", "stack", "other")
UNDO_WINDOW = timedelta(minutes=10)
_JOB_COUNTER = "applications.last_job_number"


def _ids(posting_ids: object) -> list[int]:
    if not isinstance(posting_ids, list) or not posting_ids or any(
            isinstance(i, bool) or not isinstance(i, int) for i in posting_ids):
        raise JobTrackerError("invalid_action", "expected a non-empty list of posting ids")
    return list(dict.fromkeys(posting_ids))


def _check_postings(conn: sqlite3.Connection, ids: list[int]) -> None:
    for posting_id in ids:
        if conn.execute("SELECT 1 FROM postings WHERE id = ?", (posting_id,)).fetchone() is None:
            raise JobTrackerError("not_found", f"There is no posting {posting_id}")


def _event(conn: sqlite3.Connection, entity: str, entity_id: str, kind: str, data: dict,
           when: str) -> None:
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (entity, entity_id, kind, json.dumps(data, ensure_ascii=False), when),
    )


def _next_job_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (_JOB_COUNTER,)).fetchone()
    number = int(row["value"]) + 1 if row else 1
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value", (_JOB_COUNTER, str(number)),
    )
    return f"J{number:04d}"


def application(conn: sqlite3.Connection, posting_id: int) -> dict | None:
    row = conn.execute(
        "SELECT a.*, s.key AS status_key, s.name_en, s.ends FROM applications a"
        " JOIN statuses s ON s.id = a.status_id WHERE a.posting_id = ?", (posting_id,),
    ).fetchone()
    if row is None:
        return None
    return {"job_id": row["job_id"], "posting_id": row["posting_id"],
            "status": row["status_key"] or row["name_en"], "ended": bool(row["ends"]),
            "applied_on": row["applied_on"], "created_at": row["created_at"]}


def dismissal(conn: sqlite3.Connection, posting_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM dismissals WHERE posting_id = ?", (posting_id,)).fetchone()
    if row is None:
        return None
    return {"reason": row["reason"], "note": row["note"], "created_at": row["created_at"]}


def track(conn: sqlite3.Connection, posting_ids: object, applied: bool = False,
          today: date | None = None) -> list[dict]:
    """Track postings; with `applied`, also set status Applied and the applied date."""
    ids = _ids(posting_ids)
    _check_postings(conn, ids)
    for posting_id in ids:
        if dismissal(conn, posting_id):
            raise JobTrackerError(
                "dismissed", f"Posting {posting_id} is dismissed. Restore it before tracking it."
            )
    from . import applications  # local import: applications builds on this module's records

    today = today or datetime.now().date()
    now = now_iso()
    new_status = conn.execute("SELECT id FROM statuses WHERE key = 'new'").fetchone()["id"]
    for posting_id in ids:
        existing = application(conn, posting_id)
        if existing is None:
            job_id = _next_job_id(conn)
            conn.execute(
                "INSERT INTO applications (job_id, posting_id, status_id, status_changed_at,"
                " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, posting_id, new_status, now, now, now),
            )
            _event(conn, "posting", str(posting_id), "tracked", {"job_id": job_id}, now)
            _event(conn, "application", job_id, "created", {"status": "new"}, now)
        else:
            job_id = existing["job_id"]
        if applied and (existing is None or not existing["applied_on"]):
            applications.set_status(conn, [job_id], "applied", today=today)
    bump_changes(conn)
    return [application(conn, i) for i in ids]  # type: ignore[misc]


def untrack(conn: sqlite3.Connection, posting_ids: object) -> list[int]:
    """Undo a recent track. The job id is not reused."""
    ids = _ids(posting_ids)
    now = datetime.now().astimezone()
    for posting_id in ids:
        existing = application(conn, posting_id)
        if existing is None:
            raise JobTrackerError("not_tracked", f"Posting {posting_id} is not tracked")
        created = datetime.fromisoformat(existing["created_at"].replace("Z", "+00:00"))
        if now - created > UNDO_WINDOW:
            raise JobTrackerError(
                "undo_expired", f"{existing['job_id']} was tracked too long ago to undo here"
            )
    stamp = now_iso()
    for posting_id in ids:
        existing = application(conn, posting_id)
        conn.execute("DELETE FROM application_snapshots WHERE application_id = ?",
                     (existing["job_id"],))  # type: ignore[index]
        conn.execute("DELETE FROM applications WHERE posting_id = ?", (posting_id,))
        _event(conn, "posting", str(posting_id), "untracked",
               {"job_id": existing["job_id"]}, stamp)  # type: ignore[index]
    bump_changes(conn)
    return ids


def dismiss(conn: sqlite3.Connection, posting_ids: object, reason: str,
            note: str | None = None) -> list[int]:
    """Dismiss postings with a reason; they leave the default view and are not proposed again."""
    ids = _ids(posting_ids)
    _check_postings(conn, ids)
    if reason not in DISMISS_REASONS:
        raise JobTrackerError(
            "invalid_action", f"reason must be one of: {', '.join(DISMISS_REASONS)}"
        )
    note = (note or "").strip() or None
    if reason == "other" and not note:
        raise JobTrackerError("invalid_action", "the reason 'other' needs a short note")
    for posting_id in ids:
        if application(conn, posting_id):
            raise JobTrackerError("tracked", f"Posting {posting_id} is tracked; it cannot be "
                                  "dismissed from the search results")
    now = now_iso()
    for posting_id in ids:
        conn.execute(
            "INSERT INTO dismissals (posting_id, reason, note, created_at) VALUES (?, ?, ?, ?)"
            " ON CONFLICT(posting_id) DO UPDATE SET reason = excluded.reason,"
            " note = excluded.note, created_at = excluded.created_at",
            (posting_id, reason, note, now),
        )
        _event(conn, "posting", str(posting_id), "dismissed", {"reason": reason, "note": note},
               now)
    bump_changes(conn)
    return ids


def undismiss(conn: sqlite3.Connection, posting_ids: object) -> list[int]:
    ids = _ids(posting_ids)
    for posting_id in ids:
        if dismissal(conn, posting_id) is None:
            raise JobTrackerError("not_dismissed", f"Posting {posting_id} is not dismissed")
    now = now_iso()
    for posting_id in ids:
        conn.execute("DELETE FROM dismissals WHERE posting_id = ?", (posting_id,))
        _event(conn, "posting", str(posting_id), "undismissed", {}, now)
    bump_changes(conn)
    return ids
