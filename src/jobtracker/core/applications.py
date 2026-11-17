"""Tracked applications: statuses, tags, details, documents, history.

Every application has exactly one status. Statuses are a flat list; each one
says whether an application ended with it. Built-in statuses keep a fixed
meaning through their key, read only where the system must act on a status
(the applied date, the next step); a custom status is its name and whether it
ends an application. An application counts as applied when it has an applied
date. Every change writes an event. The facts known when the application first
got an applied date are kept in a snapshot.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from . import salary, scoring
from .db import bump_changes, now_iso
from .errors import JobTrackerError
from .paths import Paths

# Built-in statuses that imply the user applied: they fill in an empty applied date.
APPLIED_KEYS = ("applied", "interview", "offer", "accepted", "rejected", "ghosted",
                "offer_declined", "no_economic_alignment")
# Built-in statuses whose next step is a date the user sets (the interview, the answer).
DATED_KEYS = ("interview", "offer")
FOLLOW_UP_DAYS = 7
GHOST_DAYS = 21
DETAIL_FIELDS = ("applied_on", "asked_salary", "channel", "contact", "notes", "next_step_on",
                 "next_step_note")
SENT_RESUME_TYPES = {".pdf": b"%PDF", ".docx": b"PK"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DOCUMENT_KINDS = ("posting", "resume_proposed", "resume_sent", "cover_letter")


def _today() -> date:
    return datetime.now().date()


def _event(conn: sqlite3.Connection, job_id: str, kind: str, data: dict, when: str) -> None:
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
        " VALUES ('application', ?, ?, ?, ?)",
        (job_id, kind, json.dumps(data, ensure_ascii=False), when),
    )


# ── statuses ──────────────────────────────────────────────────────────────

def _status_dict(row: sqlite3.Row, language: str = "en") -> dict:
    return {
        "id": row["id"], "key": row["key"],
        "name": row["name_es"] if language == "es" else row["name_en"],
        "name_en": row["name_en"], "name_es": row["name_es"],
        "ends": bool(row["ends"]), "builtin": bool(row["is_builtin"]),
        "retired": bool(row["is_retired"]),
    }


def list_statuses(conn: sqlite3.Connection, language: str = "en",
                  include_retired: bool = False) -> list[dict]:
    """Built-in statuses in their fixed order, then custom ones in creation order."""
    query = "SELECT * FROM statuses"
    if not include_retired:
        query += " WHERE is_retired = 0"
    query += " ORDER BY position, id"
    return [_status_dict(r, language) for r in conn.execute(query)]


def _ends(value: object) -> bool:
    if not isinstance(value, bool):
        raise JobTrackerError("invalid_status",
                              "say whether the application ended with this status (ends)",
                              field="ends")
    return value


def _status_row(conn: sqlite3.Connection, ref: object) -> sqlite3.Row | None:
    if isinstance(ref, int) and not isinstance(ref, bool):
        return conn.execute("SELECT * FROM statuses WHERE id = ?", (ref,)).fetchone()
    if isinstance(ref, str) and ref.strip():
        name = " ".join(ref.split())
        return conn.execute(
            "SELECT * FROM statuses WHERE key = ? OR lower(name_en) = lower(?)"
            " OR lower(name_es) = lower(?) ORDER BY is_builtin DESC, id LIMIT 1",
            (name, name, name),
        ).fetchone()
    return None


def create_status(conn: sqlite3.Connection, name: str, ends: object) -> dict:
    """A custom status, available for every application from now on. Only its name
    and whether an application ends with it are asked."""
    clean = " ".join((name or "").split())
    if not clean or len(clean) > 40:
        raise JobTrackerError("invalid_status", "a status needs a name of 1 to 40 characters")
    ends = _ends(ends)
    if _status_row(conn, clean) is not None:
        raise JobTrackerError("status_exists", f"There is already a status named '{clean}'")
    now = now_iso()
    cursor = conn.execute(
        "INSERT INTO statuses (name_en, name_es, ends, is_builtin, created_at)"
        " VALUES (?, ?, ?, 0, ?)", (clean, clean, int(ends), now),
    )
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
        " VALUES ('status', ?, 'created', ?, ?)",
        (str(cursor.lastrowid), json.dumps({"name": clean, "ends": ends}), now),
    )
    bump_changes(conn)
    return _status_dict(conn.execute("SELECT * FROM statuses WHERE id = ?",
                                     (cursor.lastrowid,)).fetchone())


def _custom(conn: sqlite3.Connection, status_id: int) -> sqlite3.Row:
    row = _status_row(conn, status_id)
    if row is None:
        raise JobTrackerError("not_found", f"There is no status {status_id}")
    if row["is_builtin"]:
        raise JobTrackerError("builtin_status", "Built-in statuses cannot be renamed or retired")
    return row


def rename_status(conn: sqlite3.Connection, status_id: int, name: str) -> dict:
    _custom(conn, status_id)
    clean = " ".join((name or "").split())
    if not clean or len(clean) > 40:
        raise JobTrackerError("invalid_status", "a status needs a name of 1 to 40 characters")
    other = _status_row(conn, clean)
    if other is not None and other["id"] != status_id:
        raise JobTrackerError("status_exists", f"There is already a status named '{clean}'")
    conn.execute("UPDATE statuses SET name_en = ?, name_es = ? WHERE id = ?",
                 (clean, clean, status_id))
    bump_changes(conn)
    return _status_dict(_status_row(conn, status_id))  # type: ignore[arg-type]


def retire_status(conn: sqlite3.Connection, status_id: int, retired: bool = True) -> dict:
    """Stop offering a custom status. Applications that have it keep it."""
    _custom(conn, status_id)
    conn.execute("UPDATE statuses SET is_retired = ? WHERE id = ?", (int(retired), status_id))
    bump_changes(conn)
    return _status_dict(_status_row(conn, status_id))  # type: ignore[arg-type]


# ── applications ──────────────────────────────────────────────────────────

def _row(conn: sqlite3.Connection, job_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT a.*, s.key AS status_key, s.ends, s.name_en, s.name_es, s.is_builtin,"
        " s.is_retired FROM applications a JOIN statuses s ON s.id = a.status_id"
        " WHERE a.job_id = ?", (job_id,),
    ).fetchone()
    if row is None:
        raise JobTrackerError("not_found", f"There is no tracked application {job_id}")
    return row


def thresholds(conn: sqlite3.Connection) -> dict:
    """Follow-up and ghost thresholds in days; active rules can change them."""
    result = {"follow_up_after_days": FOLLOW_UP_DAYS, "ghost_after_days": GHOST_DAYS}
    for row in conn.execute(
        "SELECT effect FROM rules WHERE status = 'active' AND effect IS NOT NULL"
        " ORDER BY updated_at, id"
    ):
        effect = json.loads(row["effect"])
        for key in result:
            value = effect.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 365:
                result[key] = value
    return result


def _snapshot(conn: sqlite3.Connection, row: sqlite3.Row, when: str) -> None:
    """The facts known when the application first got an applied date (training data
    for prediction). Taken once; later changes do not replace it."""
    if not row["applied_on"] or conn.execute(
        "SELECT 1 FROM application_snapshots WHERE application_id = ?", (row["job_id"],)
    ).fetchone():
        return
    posting = conn.execute("SELECT * FROM postings WHERE id = ?", (row["posting_id"],)
                           ).fetchone()
    score = scoring.current(conn, row["posting_id"])
    suggestion = salary.current(conn, row["posting_id"])
    sent = _current_document(conn, row["id"], "resume_sent")
    proposed = _current_document(conn, row["id"], "resume_proposed")
    cover = _current_document(conn, row["id"], "cover_letter")
    applied_on = row["applied_on"]
    age = None
    if applied_on and posting["posted_at"]:
        age = (date.fromisoformat(applied_on) - date.fromisoformat(posting["posted_at"])).days
    data = {
        "score": score["total"] if score else None,
        "score_id": score["id"] if score else None,
        "score_components": {c["component"]: c["points"] for c in score["components"]}
        if score else None,
        "target_title": posting["title"],
        "provider": posting["provider"],
        "channel": row["channel"],
        "work_mode": posting["work_mode"],
        "contract_type": posting["contract_type"],
        "resume_kind": "sent" if sent else ("tailored" if proposed else "base"),
        "cover_letter": cover is not None,
        "posting_age_days": age,
        "applied_on": applied_on,
        "suggested_salary": {k: suggestion[k] for k in ("amount", "currency", "basis",
                                                         "confidence")}
        if suggestion and suggestion["status"] == "suggested" else None,
        "asked_salary": _asked(row),
    }
    conn.execute(
        "INSERT INTO application_snapshots (application_id, captured_at, data) VALUES (?, ?, ?)",
        (row["job_id"], when, json.dumps(data, ensure_ascii=False)),
    )


def snapshot(conn: sqlite3.Connection, job_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM application_snapshots WHERE application_id = ?",
                       (job_id,)).fetchone()
    if row is None:
        return None
    return {"captured_at": row["captured_at"], **json.loads(row["data"])}


def _update_snapshot(conn: sqlite3.Connection, job_id: str, fields: dict) -> None:
    """Applied date and asked salary stay editable in the snapshot; score does not."""
    current = snapshot(conn, job_id)
    if current is None:
        return
    current.pop("captured_at")
    current.update(fields)
    conn.execute("UPDATE application_snapshots SET data = ? WHERE application_id = ?",
                 (json.dumps(current, ensure_ascii=False), job_id))


def set_status(
    conn: sqlite3.Connection, job_ids: list[str], status: object, *, ends: bool | None = None,
    today: date | None = None,
) -> list[str]:
    """Give applications a status (by id, key, or name). With `ends`, an unknown name
    becomes a new custom status (inline creation) that ends applications or not."""
    if not job_ids:
        raise JobTrackerError("invalid_action", "no application given")
    target = _status_row(conn, status)
    if target is None:
        if ends is None or not isinstance(status, str):
            raise JobTrackerError(
                "not_found",
                f"There is no status '{status}'. To create it, say whether the application"
                " ended with it (ends).",
            )
        target = _status_row(conn, create_status(conn, status, ends)["id"])
    if target["is_retired"]:
        raise JobTrackerError("retired_status",
                              f"'{target['name_en']}' is retired; it is no longer offered")
    rows = [_row(conn, job_id) for job_id in dict.fromkeys(job_ids)]
    today = today or _today()
    now = now_iso()
    for row in rows:
        if row["status_id"] == target["id"]:
            continue
        applied_on = row["applied_on"]
        if target["key"] in APPLIED_KEYS and not applied_on:
            applied_on = today.isoformat()
        conn.execute(
            "UPDATE applications SET status_id = ?, applied_on = ?, status_changed_at = ?,"
            " updated_at = ? WHERE id = ?",
            (target["id"], applied_on, now, now, row["id"]),
        )
        _event(conn, row["job_id"], "status_changed", {
            "from": row["status_key"] or row["name_en"], "to": target["key"] or target["name_en"],
            "from_id": row["status_id"], "to_id": target["id"],
            "from_name": {"en": row["name_en"], "es": row["name_es"]},
            "to_name": {"en": target["name_en"], "es": target["name_es"]},
            "to_ends": bool(target["ends"]),
        }, now)
        _snapshot(conn, _row(conn, row["job_id"]), now)
    bump_changes(conn)
    return [row["job_id"] for row in rows]


def set_tags(conn: sqlite3.Connection, job_id: str, add: list | None = None,
             remove: list | None = None) -> list[str]:
    row = _row(conn, job_id)
    now = now_iso()
    for tag in add or []:
        clean = " ".join(str(tag).split())
        if not clean or len(clean) > 40:
            raise JobTrackerError("invalid_tag", "a tag needs 1 to 40 characters")
        cursor = conn.execute(
            "INSERT OR IGNORE INTO application_tags (application_id, tag, created_at)"
            " VALUES (?, ?, ?)", (row["id"], clean, now),
        )
        if cursor.rowcount:
            _event(conn, job_id, "tag_added", {"tag": clean}, now)
    for tag in remove or []:
        cursor = conn.execute(
            "DELETE FROM application_tags WHERE application_id = ? AND tag = ? COLLATE NOCASE",
            (row["id"], " ".join(str(tag).split())),
        )
        if cursor.rowcount:
            _event(conn, job_id, "tag_removed", {"tag": str(tag)}, now)
    conn.execute("UPDATE applications SET updated_at = ? WHERE id = ?", (now, row["id"]))
    bump_changes(conn)
    return tags(conn, row["id"])


def tags(conn: sqlite3.Connection, application_id: int) -> list[str]:
    return [r["tag"] for r in conn.execute(
        "SELECT tag FROM application_tags WHERE application_id = ? ORDER BY created_at, tag",
        (application_id,))]


def _asked(row: sqlite3.Row) -> dict | None:
    if row["asked_salary_amount"] is None:
        return None
    return {"amount": row["asked_salary_amount"], "currency": row["asked_salary_currency"],
            "basis": row["asked_salary_basis"] or "gross", "period": "month"}


def _optional_date(field: str, value: object) -> str | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as error:
        raise JobTrackerError("invalid_details", f"{field} must be a date like 2026-11-15",
                              field=field) from error


def _optional_text(field: str, value: object, limit: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise JobTrackerError("invalid_details", f"{field} must be text", field=field)
    clean = value.strip()
    if len(clean) > limit:
        raise JobTrackerError("invalid_details", f"{field} is longer than {limit} characters",
                              field=field)
    return clean or None


def update_details(conn: sqlite3.Connection, job_id: str, changes: object) -> dict:
    """Save the user's application details. Each changed field is an event."""
    if not isinstance(changes, dict) or not changes:
        raise JobTrackerError("invalid_details", "expected an object with the fields to change")
    unknown = sorted(set(changes) - set(DETAIL_FIELDS))
    if unknown:
        raise JobTrackerError("invalid_details", f"'{unknown[0]}' is not an application detail",
                              field=unknown[0])
    row = _row(conn, job_id)
    columns: dict[str, object] = {}
    if "applied_on" in changes:
        columns["applied_on"] = _optional_date("applied_on", changes["applied_on"])
    if "next_step_on" in changes:
        columns["next_step_on"] = _optional_date("next_step_on", changes["next_step_on"])
    for field, limit in (("channel", 80), ("contact", 200), ("notes", 5000),
                         ("next_step_note", 200)):
        if field in changes:
            columns[field] = _optional_text(field, changes[field], limit)
    if "asked_salary" in changes:
        asked = changes["asked_salary"]
        if asked is None:
            columns.update(asked_salary_amount=None, asked_salary_currency=None,
                           asked_salary_basis=None)
        else:
            amount = asked.get("amount") if isinstance(asked, dict) else None
            currency = asked.get("currency") if isinstance(asked, dict) else None
            basis = asked.get("basis", "gross") if isinstance(asked, dict) else None
            if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
                raise JobTrackerError("invalid_details",
                                      "asked_salary.amount must be a positive whole number",
                                      field="asked_salary")
            if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
                raise JobTrackerError("invalid_details",
                                      "asked_salary.currency must be a code such as PEN",
                                      field="asked_salary")
            if basis not in ("gross", "net"):
                raise JobTrackerError("invalid_details", "asked_salary.basis must be gross or net",
                                      field="asked_salary")
            columns.update(asked_salary_amount=amount, asked_salary_currency=currency,
                           asked_salary_basis=basis)
    changed = {key: value for key, value in columns.items() if row[key] != value}
    if not changed:
        return application(conn, job_id)
    now = now_iso()
    assignments = ", ".join(f"{key} = ?" for key in changed)
    conn.execute(f"UPDATE applications SET {assignments}, updated_at = ? WHERE id = ?",
                 (*changed.values(), now, row["id"]))
    for key, value in changed.items():
        if key.startswith("asked_salary_") and key != "asked_salary_amount":
            continue
        field = "asked_salary" if key == "asked_salary_amount" else key
        _event(conn, job_id, "field_changed", {
            "field": field,
            "from": _asked(row) if field == "asked_salary" else row[key],
            "to": _asked(_row(conn, job_id)) if field == "asked_salary" else value,
        }, now)
    fresh = _row(conn, job_id)
    _update_snapshot(conn, job_id, {"applied_on": fresh["applied_on"],
                                    "asked_salary": _asked(fresh)})
    _snapshot(conn, fresh, now)  # a date entered by hand makes the application applied
    bump_changes(conn)
    return application(conn, job_id)


# ── documents ─────────────────────────────────────────────────────────────

def _document_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "kind": row["kind"], "file_name": row["file_name"],
        "version": row["version"], "origin": row["origin"],
        "original_name": row["original_name"], "size_bytes": row["size_bytes"],
        "created_at": row["created_at"], "current": bool(row["is_current"]),
    }


def _current_document(conn: sqlite3.Connection, application_id: int, kind: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM documents WHERE application_id = ? AND kind = ? AND is_current = 1",
        (application_id, kind),
    ).fetchone()
    return _document_dict(row) if row else None


def documents(conn: sqlite3.Connection, application_id: int) -> list[dict]:
    return [_document_dict(r) for r in conn.execute(
        "SELECT * FROM documents WHERE application_id = ? ORDER BY kind, version DESC",
        (application_id,))]


def folder(conn: sqlite3.Connection, paths: Paths, job_id: str) -> Path:
    row = _row(conn, job_id)
    company = conn.execute("SELECT company FROM postings WHERE id = ?",
                           (row["posting_id"],)).fetchone()["company"]
    return paths.job_folder(job_id, company)


def register_document(conn: sqlite3.Connection, paths: Paths, job_id: str, kind: str,
                      file_name: str, origin: str, original_name: str | None = None) -> dict:
    """Register a file already inside the application folder as the current one of its kind."""
    if kind not in DOCUMENT_KINDS:
        raise JobTrackerError("invalid_document",
                              f"kind must be one of: {', '.join(DOCUMENT_KINDS)}")
    row = _row(conn, job_id)
    base = folder(conn, paths, job_id).resolve()
    path = (base / file_name).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise JobTrackerError("invalid_document",
                              f"'{file_name}' is not a file in the folder of {job_id}")
    version = conn.execute(
        "SELECT COALESCE(MAX(version), 0) FROM documents WHERE application_id = ? AND kind = ?",
        (row["id"], kind),
    ).fetchone()[0] + 1
    now = now_iso()
    conn.execute("UPDATE documents SET is_current = 0 WHERE application_id = ? AND kind = ?",
                 (row["id"], kind))
    cursor = conn.execute(
        "INSERT INTO documents (application_id, kind, file_name, version, origin, original_name,"
        " size_bytes, created_at, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (row["id"], kind, path.relative_to(base).as_posix(), version, origin, original_name,
         path.stat().st_size, now),
    )
    _event(conn, job_id, "document_registered",
           {"kind": kind, "file": path.name, "version": version, "origin": origin}, now)
    conn.execute("UPDATE applications SET updated_at = ? WHERE id = ?", (now, row["id"]))
    bump_changes(conn)
    return _document_dict(conn.execute("SELECT * FROM documents WHERE id = ?",
                                       (cursor.lastrowid,)).fetchone())


def upload_sent_resume(conn: sqlite3.Connection, paths: Paths, job_id: str, original_name: str,
                       data: bytes) -> dict:
    """Store the resume the user actually sent. The previous upload is kept as -v<N>."""
    extension = Path(original_name or "").suffix.lower()
    if extension not in SENT_RESUME_TYPES:
        raise JobTrackerError("unsupported_file",
                              "Upload the resume you sent as a PDF or DOCX file.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise JobTrackerError("file_too_large", "The file is larger than 10 MB.")
    if not data.startswith(SENT_RESUME_TYPES[extension]):
        raise JobTrackerError("unsupported_file",
                              f"The file is not a real {extension[1:].upper()} document.")
    row = _row(conn, job_id)
    base = folder(conn, paths, job_id)
    base.mkdir(parents=True, exist_ok=True)
    previous = conn.execute(
        "SELECT * FROM documents WHERE application_id = ? AND kind = 'resume_sent'"
        " AND is_current = 1", (row["id"],),
    ).fetchone()
    if previous is not None:
        old = base / previous["file_name"]
        kept = f"resume-sent-v{previous['version']}{Path(previous['file_name']).suffix}"
        if old.exists() and old.name != kept:
            old.rename(base / kept)
        conn.execute("UPDATE documents SET file_name = ? WHERE id = ?", (kept, previous["id"]))
    for stale in base.glob("resume-sent.*"):
        stale.rename(base / f"resume-sent-orphan-{now_iso().replace(':', '')}{stale.suffix}")
    target = base / f"resume-sent{extension}"
    target.write_bytes(data)
    return register_document(conn, paths, job_id, "resume_sent", target.name, "user",
                             Path(original_name).name)


def document_path(conn: sqlite3.Connection, paths: Paths, job_id: str, document_id: int) -> Path:
    """The file of a document, confined to the application's private folder."""
    row = _row(conn, job_id)
    doc = conn.execute("SELECT * FROM documents WHERE id = ? AND application_id = ?",
                       (document_id, row["id"])).fetchone()
    if doc is None:
        raise JobTrackerError("not_found", f"There is no document {document_id} for {job_id}")
    base = folder(conn, paths, job_id).resolve()
    path = (base / doc["file_name"]).resolve()
    if not path.is_relative_to(base) or not path.is_relative_to(paths.home.resolve()):
        raise JobTrackerError("forbidden_path", "That file is outside the private folder")
    if not path.is_file():
        raise JobTrackerError("not_found", f"The file of document {document_id} is missing")
    return path


# ── read models ───────────────────────────────────────────────────────────

def _next_step(row: sqlite3.Row, docs: dict, limits: dict, today: date) -> dict:
    """What the user should do next: derived, unless the user set their own."""
    ended = bool(row["ends"])
    if row["next_step_note"] or (row["next_step_on"] and not ended):
        return {"kind": "user", "note": row["next_step_note"], "date": row["next_step_on"]}
    if ended:
        return {"kind": "none"}
    if not row["applied_on"]:
        has_resume = docs.get("resume_proposed") or docs.get("resume_sent")
        return {"kind": "apply" if has_resume else "prepare_documents"}
    if row["status_key"] in DATED_KEYS:
        return {"kind": "set_date"}
    since = max(date.fromisoformat(row["status_changed_at"][:10]),
                date.fromisoformat(row["applied_on"]))
    waited = (today - since).days
    if waited >= limits["ghost_after_days"]:
        return {"kind": "ghost", "days": waited}
    follow_up = since + timedelta(days=limits["follow_up_after_days"])
    if today >= follow_up:
        return {"kind": "follow_up", "date": follow_up.isoformat(), "due": True}
    return {"kind": "follow_up", "date": follow_up.isoformat(), "due": False}


def application(conn: sqlite3.Connection, job_id: str, language: str = "en",
                today: date | None = None, limits: dict | None = None) -> dict:
    row = _row(conn, job_id)
    today = today or _today()
    limits = limits or thresholds(conn)
    docs = {kind: _current_document(conn, row["id"], kind) for kind in DOCUMENT_KINDS}
    from . import answers as answers_service
    from . import documents as documents_service
    from . import search  # local import: search imports this module's tables only

    posting = search.posting(conn, row["posting_id"], detail=False)
    next_step = _next_step(row, docs, limits, today)
    for kind in ("resume_proposed", "cover_letter"):
        if docs[kind]:
            docs[kind] = documents_service.current(conn, row["id"], kind)
    return {
        "job_id": row["job_id"], "posting_id": row["posting_id"],
        "status": {"id": row["status_id"], "key": row["status_key"],
                   "name": row["name_es"] if language == "es" else row["name_en"],
                   "name_en": row["name_en"], "name_es": row["name_es"],
                   "ends": bool(row["ends"]), "builtin": bool(row["is_builtin"])},
        "ended": bool(row["ends"]),
        "tags": tags(conn, row["id"]),
        "applied_on": row["applied_on"], "channel": row["channel"], "contact": row["contact"],
        "notes": row["notes"], "next_step_on": row["next_step_on"],
        "next_step_note": row["next_step_note"], "asked_salary": _asked(row),
        "created_at": row["created_at"], "updated_at": row["updated_at"],
        "status_changed_at": row["status_changed_at"],
        "posting": posting,
        "score": scoring.current(conn, row["posting_id"]),
        "salary": salary.current(conn, row["posting_id"]),
        "snapshot": snapshot(conn, row["job_id"]),
        "documents": {kind: docs[kind] for kind in ("resume_proposed", "resume_sent",
                                                    "cover_letter")},
        "cover_letter": documents_service.cover_letter(conn, row["id"]),
        "form_question_count": posting["form_question_count"],
        "form_answered_count": answers_service.answered_count(conn, row["id"]),
        "form_proposed_count": answers_service.proposed_count(conn, row["id"]),
        "next_step": next_step,
        "flags": {"ghost": next_step["kind"] == "ghost",
                  "follow_up_due": next_step["kind"] == "follow_up" and next_step["due"]},
    }


def list_applications(conn: sqlite3.Connection, language: str = "en",
                      status: object = None, include_ended: bool = True,
                      today: date | None = None) -> list[dict]:
    limits = thresholds(conn)
    today = today or _today()
    query = ("SELECT a.job_id FROM applications a JOIN statuses s ON s.id = a.status_id")
    params: list = []
    clauses = []
    if status is not None:
        target = _status_row(conn, status)
        if target is None:
            raise JobTrackerError("not_found", f"There is no status '{status}'")
        clauses.append("s.id = ?")
        params.append(target["id"])
    if not include_ended:
        clauses.append("s.ends = 0")
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY a.id"
    return [application(conn, r["job_id"], language, today, limits)
            for r in conn.execute(query, params)]


def status_names(conn: sqlite3.Connection, data: dict, language: str = "en") -> tuple:
    """The full names of the two statuses of a `status_changed` event. Newer events
    carry both names; older ones are resolved by status key or by the stored name."""
    def name(side: str) -> str | None:
        stored = data.get(f"{side}_name")
        if isinstance(stored, dict):
            return stored.get(language) or stored.get("en")
        ref = data.get(side)
        if ref is None:
            return None
        found = conn.execute("SELECT name_en, name_es FROM statuses WHERE key = ?",
                             (ref,)).fetchone()
        if found is None:
            return ref
        return found["name_es"] if language == "es" else found["name_en"]

    return name("from"), name("to")


def history(conn: sqlite3.Connection, job_id: str, language: str = "en") -> list[dict]:
    """Everything that happened: when it was found, scored, documents, status changes
    (each with the full names of both statuses)."""
    row = _row(conn, job_id)
    posting = conn.execute("SELECT * FROM postings WHERE id = ?", (row["posting_id"],)
                           ).fetchone()
    items = [{"at": posting["captured_at"], "kind": "found",
              "data": {"provider": posting["provider"]}}]
    for event in conn.execute(
        "SELECT * FROM events WHERE (entity_type = 'application' AND entity_id = ?)"
        " OR (entity_type = 'posting' AND entity_id = ? AND kind IN ('scored', 'salary',"
        " 'tracked', 'work_mode')) ORDER BY created_at, id", (job_id, str(row["posting_id"])),
    ):
        data = json.loads(event["data"]) if event["data"] else {}
        if event["kind"] == "status_changed":
            data["from_name"], data["to_name"] = status_names(conn, data, language)
        items.append({"at": event["created_at"], "kind": event["kind"], "data": data})
    items.sort(key=lambda item: item["at"])
    return items


def detail(conn: sqlite3.Connection, job_id: str, language: str = "en") -> dict:
    from . import answers as answers_service
    from . import documents as documents_service
    from . import search

    item = application(conn, job_id, language)
    item["all_documents"] = documents_service.list_for(conn, job_id)
    item["form_questions"] = answers_service.list_answers(conn, job_id)
    item["history"] = history(conn, job_id, language)
    item["description"] = search.posting(conn, item["posting_id"])["description"]
    return item


def funnel(conn: sqlite3.Connection, items: list[dict], language: str = "en") -> list[dict]:
    """One count per status that at least one of the applications has, in the order
    of the status list."""
    counts: dict[int, int] = {}
    for item in items:
        counts[item["status"]["id"]] = counts.get(item["status"]["id"], 0) + 1
    return [{"status_id": s["id"], "key": s["key"], "name": s["name"], "ends": s["ends"],
             "count": counts[s["id"]]}
            for s in list_statuses(conn, language, include_retired=True) if s["id"] in counts]


def attention(items: list[dict]) -> dict:
    """Applications that have not ended and need something, by reason."""
    open_items = [i for i in items if not i["ended"]]
    return {
        "missing_resume": [i["job_id"] for i in open_items
                           if not i["documents"]["resume_proposed"]
                           and not i["documents"]["resume_sent"]
                           and not i["applied_on"]],
        "unanswered_form": [i["job_id"] for i in open_items
                            if i["form_question_count"] > i["form_answered_count"]
                            and not i["applied_on"]],
        "no_response": [i["job_id"] for i in open_items if i["flags"]["ghost"]],
        "follow_up_due": [i["job_id"] for i in open_items if i["flags"]["follow_up_due"]],
    }
