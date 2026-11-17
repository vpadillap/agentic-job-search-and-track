"""Rules: system rules, user preferences, and learned lessons in one list."""
from __future__ import annotations

import json
import sqlite3

from .db import bump_changes, now_iso
from .errors import JobTrackerError

ORIGINS = ("system", "user", "learned")
STATUSES = ("proposed", "active", "ignored", "reverted")
AREAS = (
    "general", "search", "score", "resume", "cover_letter", "form",
    "salary", "statuses", "providers", "privacy",
)

# Shipped with the project, always active, never overridable by lessons.
SYSTEM_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "salary_evidence",
        "salary",
        "Suggest a salary only with 2 or more comparable, linked sources (same country and "
        "level, matching work mode, similar industry and company size). Never extrapolate; "
        "otherwise record that there is no reliable data.",
    ),
    (
        "truthful_documents",
        "resume",
        "Resumes, cover letters, and form answers never claim experience, skills, employers, "
        "dates, or results that are not in the user's base resume and profile.",
    ),
    (
        "resume_layout_consent",
        "resume",
        "Do not change a resume's layout or structure without the user's explicit consent; "
        "content edits only by default.",
    ),
    (
        "document_language",
        "general",
        "Resumes, cover letters, and form answers are written in the language of each job "
        "posting. The panel language does not affect them.",
    ),
    (
        "no_auto_apply",
        "general",
        "The agent never submits applications, sends messages, or changes anything in the "
        "user's accounts on job sites. It prepares; the user applies.",
    ),
    (
        "privacy_boundary",
        "privacy",
        "Personal data is written only inside the private home directory, using the paths "
        "reported by `jobtracker paths`.",
    ),
)


def seed_system_rules(conn: sqlite3.Connection) -> int:
    """Insert system rules that are not present yet; returns how many were added."""
    added = 0
    now = now_iso()
    for key, area, text in SYSTEM_RULES:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO rules (key, origin, status, area, text, created_at, updated_at)"
            " VALUES (?, 'system', 'active', ?, ?, ?, ?)",
            (key, area, text, now, now),
        )
        added += cursor.rowcount
    return added


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "key": row["key"],
        "origin": row["origin"],
        "status": row["status"],
        "area": row["area"],
        "text": row["text"],
        "evidence": row["evidence"],
        "effect": json.loads(row["effect"]) if row["effect"] else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_rules(conn: sqlite3.Connection, status: str | None = "active") -> list[dict]:
    if status is not None and status not in STATUSES:
        raise JobTrackerError("invalid_rule", f"unknown status '{status}'")
    query = "SELECT * FROM rules"
    params: tuple = ()
    if status is not None:
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY CASE origin WHEN 'system' THEN 0 WHEN 'user' THEN 1 ELSE 2 END, id"
    return [_row_to_dict(row) for row in conn.execute(query, params)]


def _validate(record: object, index: int) -> dict:
    where = f"record {index}"
    if not isinstance(record, dict):
        raise JobTrackerError("invalid_rule", f"{where}: must be an object", index=index)
    text = record.get("text")
    if not isinstance(text, str) or not text.strip():
        raise JobTrackerError("invalid_rule", f"{where}: 'text' is required", index=index)
    origin = record.get("origin", "user")
    if origin not in ("user", "learned"):
        raise JobTrackerError(
            "invalid_rule", f"{where}: origin must be 'user' or 'learned'", index=index
        )
    area = record.get("area", "general")
    if area not in AREAS:
        raise JobTrackerError(
            "invalid_rule", f"{where}: area must be one of {', '.join(AREAS)}", index=index
        )
    default_status = "active" if origin == "user" else "proposed"
    status = record.get("status", default_status)
    if status not in STATUSES:
        raise JobTrackerError("invalid_rule", f"{where}: unknown status '{status}'", index=index)
    if origin == "learned" and status == "active":
        raise JobTrackerError(
            "invalid_rule",
            f"{where}: a learned rule starts as 'proposed'; the user applies it",
            index=index,
        )
    effect = record.get("effect")
    if effect is not None and not isinstance(effect, dict):
        raise JobTrackerError("invalid_rule", f"{where}: 'effect' must be an object", index=index)
    evidence = record.get("evidence")
    if evidence is not None and not isinstance(evidence, str):
        raise JobTrackerError("invalid_rule", f"{where}: 'evidence' must be text", index=index)
    return {
        "origin": origin, "status": status, "area": area, "text": text.strip(),
        "evidence": evidence, "effect": json.dumps(effect) if effect is not None else None,
    }


def add_rules(conn: sqlite3.Connection, records: list) -> list[dict]:
    """Validate every record first, then store them all; nothing is stored on error."""
    if not isinstance(records, list) or not records:
        raise JobTrackerError("invalid_rule", "expected a non-empty list of rules")
    validated = [_validate(record, index) for index, record in enumerate(records)]
    now = now_iso()
    ids = []
    for rule in validated:
        cursor = conn.execute(
            "INSERT INTO rules (origin, status, area, text, evidence, effect, created_at,"
            " updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (rule["origin"], rule["status"], rule["area"], rule["text"], rule["evidence"],
             rule["effect"], now, now),
        )
        ids.append(cursor.lastrowid)
        conn.execute(
            "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
            " VALUES ('rule', ?, 'created', ?, ?)",
            (str(cursor.lastrowid), json.dumps({"origin": rule["origin"]}), now),
        )
    bump_changes(conn)
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(f"SELECT * FROM rules WHERE id IN ({placeholders}) ORDER BY id", ids)
    return [_row_to_dict(row) for row in rows]
