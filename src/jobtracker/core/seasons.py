"""Seasons: search campaigns.

There is exactly one active season. Searches, tracked applications, pending
work, and insights refer to it by default. Starting a new season closes the
current one, carries over the open applications the user chose, copies the
profile as the new season's first version (the previous answers become the
defaults), and either keeps or resets learning. Nothing is ever deleted: an
earlier season stays viewable and its applications still accept a status
change (a late reply).
"""
from __future__ import annotations

import json
import sqlite3

from .db import bump_changes, now_iso
from .errors import JobTrackerError

LEARNING_CHOICES = ("keep", "reset")


def active_id(conn: sqlite3.Connection) -> int | None:
    row = conn.execute("SELECT id FROM seasons WHERE is_active = 1").fetchone()
    return row["id"] if row else None


def _row(conn: sqlite3.Connection, number: int | None) -> sqlite3.Row:
    if number is None:
        row = conn.execute("SELECT * FROM seasons WHERE is_active = 1").fetchone()
        if row is None:
            raise JobTrackerError("no_active_season", "There is no active season")
        return row
    row = conn.execute("SELECT * FROM seasons WHERE number = ?", (number,)).fetchone()
    if row is None:
        raise JobTrackerError("not_found", f"There is no season {number}")
    return row


def season_id(conn: sqlite3.Connection, number: int | None = None) -> int:
    """The id of season `number`, or of the active season."""
    return _row(conn, number)["id"]


def _counts(conn: sqlite3.Connection, sid: int) -> dict:
    row = conn.execute(
        "SELECT COUNT(*) AS total, COALESCE(SUM(s.ends = 0), 0) AS open,"
        " COALESCE(SUM(a.applied_on IS NOT NULL), 0) AS applied"
        " FROM applications a JOIN statuses s ON s.id = a.status_id WHERE a.season_id = ?",
        (sid,)).fetchone()
    runs = conn.execute("SELECT COUNT(*) FROM search_runs WHERE season_id = ?",
                        (sid,)).fetchone()[0]
    return {"applications": row["total"], "open": row["open"], "applied": row["applied"],
            "searches": runs}


def _dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    closing = json.loads(row["closing"]) if row["closing"] else None
    version = conn.execute(
        "SELECT MAX(version) FROM profile_versions WHERE season_id = ?", (row["id"],)
    ).fetchone()[0]
    return {
        "number": row["number"], "label": row["label"],
        "started_at": row["started_at"], "ended_at": row["ended_at"],
        "active": bool(row["is_active"]),
        "profile_version": version,
        "base_resume_ids": closing["base_resume_ids"] if closing else None,
        "learning": closing.get("learning") if closing else None,
        "counts": _counts(conn, row["id"]),
    }


def list_seasons(conn: sqlite3.Connection) -> list[dict]:
    return [_dict(conn, r) for r in conn.execute("SELECT * FROM seasons ORDER BY number")]


def show(conn: sqlite3.Connection, paths, number: int | None = None) -> dict:
    """A season with its profile and base resumes (an earlier season keeps its own)."""
    from . import resume

    row = _row(conn, number)
    result = _dict(conn, row)
    profile_row = conn.execute(
        "SELECT * FROM profile_versions WHERE season_id = ? ORDER BY version DESC LIMIT 1",
        (row["id"],)).fetchone()
    result["profile"] = ({"version": profile_row["version"], **json.loads(profile_row["data"])}
                         if profile_row else None)
    if row["is_active"]:
        result["base_resumes"] = resume.list_current(conn, paths)
    else:
        result["base_resumes"] = [resume.by_id(conn, paths, rid)
                                  for rid in result["base_resume_ids"] or []]
    return result


def open_applications(conn: sqlite3.Connection, number: int | None = None) -> list[dict]:
    """Applications of a season that have not ended: the ones to decide on at a change."""
    sid = season_id(conn, number)
    return [{
        "job_id": r["job_id"], "title": r["title"], "company": r["company"],
        "status": r["key"] or r["name_en"], "applied_on": r["applied_on"],
    } for r in conn.execute(
        "SELECT a.job_id, a.applied_on, p.title, p.company, s.key, s.name_en"
        " FROM applications a JOIN statuses s ON s.id = a.status_id"
        " JOIN postings p ON p.id = a.posting_id"
        " WHERE a.season_id = ? AND s.ends = 0 ORDER BY a.id", (sid,))]


def is_earlier(conn: sqlite3.Connection, application_season_id: int | None) -> bool:
    """True when an application belongs to a season that is no longer active."""
    current = active_id(conn)
    return application_season_id is not None and current is not None \
        and application_season_id != current


def require_current(conn: sqlite3.Connection, job_id: str, application_season_id) -> None:
    """Applications of an earlier season are read-only except for their status."""
    if is_earlier(conn, application_season_id):
        raise JobTrackerError(
            "earlier_season",
            f"{job_id} belongs to an earlier season: only its status and the offered salary "
            "can still change. "
            "Carry it into the current season when starting one to keep working on it.")


def start(conn: sqlite3.Connection, *, learning: str, carry: list[str] | None = None,
          leave_open: bool = False, label: str | None = None) -> dict:
    """Close the active season and open the next one.

    `carry` lists the open applications that continue in the new season. When
    open applications exist, the user must decide: name them in `carry`, or
    say `leave_open` to leave the rest in the earlier season.
    """
    from . import learning as learning_service

    if learning not in LEARNING_CHOICES:
        raise JobTrackerError("invalid_season",
                              "say whether learned lessons are kept or reset (keep|reset)")
    current = _row(conn, None)
    open_items = open_applications(conn)
    open_ids = {i["job_id"] for i in open_items}
    carry = list(dict.fromkeys(carry or []))
    unknown = [j for j in carry if j not in open_ids]
    if unknown:
        raise JobTrackerError(
            "invalid_season",
            f"{', '.join(unknown)} is not an open application of the current season",
            open=sorted(open_ids))
    undecided = sorted(open_ids - set(carry))
    if undecided and not leave_open:
        raise JobTrackerError(
            "open_applications",
            f"{len(undecided)} application(s) are still open: decide for each whether it "
            "continues in the new season (carry) or stays in the earlier one (leave-open). "
            "Nothing was changed.", open=open_items)

    now = now_iso()
    base_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM base_resumes WHERE is_current = 1 ORDER BY id")]
    profile_row = conn.execute("SELECT * FROM profile_versions WHERE is_active = 1").fetchone()
    closing = {"base_resume_ids": base_ids,
               "profile_version": profile_row["version"] if profile_row else None,
               "learning": learning, "carried": carry, "left": undecided}
    conn.execute("UPDATE seasons SET is_active = 0, ended_at = ?, closing = ? WHERE id = ?",
                 (now, json.dumps(closing), current["id"]))
    cursor = conn.execute(
        "INSERT INTO seasons (number, label, started_at, is_active) VALUES (?, ?, ?, 1)",
        (current["number"] + 1, (label or "").strip() or None, now))
    new_id = cursor.lastrowid
    if profile_row is not None:
        # The previous answers are the new season's defaults: its first version.
        conn.execute("UPDATE profile_versions SET is_active = 0 WHERE is_active = 1")
        conn.execute(
            "INSERT INTO profile_versions (season_id, version, data, created_at, is_active)"
            " VALUES (?, 1, ?, ?, 1)", (new_id, profile_row["data"], now))
    for job_id in carry:
        conn.execute("UPDATE applications SET season_id = ?, updated_at = ? WHERE job_id = ?",
                     (new_id, now, job_id))
        conn.execute(
            "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
            " VALUES ('application', ?, 'carried_over', ?, ?)",
            (job_id, json.dumps({"from_season": current["number"],
                                 "to_season": current["number"] + 1}), now))

    retired: list[int] = []
    if learning == "reset":
        for rule in conn.execute(
                "SELECT id FROM rules WHERE origin = 'learned' AND status = 'active'"
                " ORDER BY id").fetchall():
            learning_service.revert(conn, rule["id"])
            retired.append(rule["id"])
        learning_service.reset(conn)
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
        " VALUES ('season', ?, 'started', ?, ?)",
        (str(current["number"] + 1),
         json.dumps({"previous": current["number"], "learning": learning,
                     "carried": carry, "retired_lessons": retired}), now))
    bump_changes(conn)
    return {"season": _dict(conn, _row(conn, None)),
            "previous": _dict(conn, _row(conn, current["number"])),
            "carried": carry, "left_in_previous": undecided,
            "learning": learning, "retired_lessons": retired}


def earlier_season_rules(conn: sqlite3.Connection) -> set[int]:
    """Applied lessons that come from an earlier season: the next analysis re-examines
    them against new data."""
    row = conn.execute("SELECT started_at FROM seasons WHERE is_active = 1").fetchone()
    if row is None:
        return set()
    return {r["id"] for r in conn.execute(
        "SELECT id FROM rules WHERE origin = 'learned' AND status = 'active'"
        " AND COALESCE(applied_at, updated_at) <= ?", (row["started_at"],))}
