"""Documents the agent proposes for an application: tailored resumes and cover letters.

The agent writes the file at the path this module hands out, then registers it
with what it is based on: a change summary, the base-resume line behind every
emphasized term, the gaps it did not paper over, and the rules it followed.
Earlier versions and the base resume are never modified.
"""
from __future__ import annotations

import difflib
import json
import re
import sqlite3
from pathlib import Path

from . import applications
from .db import bump_changes, now_iso
from .errors import JobTrackerError
from .paths import Paths, next_version_path

STEMS = {"resume_proposed": "resume-proposed", "cover_letter": "cover-letter"}
EXTENSIONS = {"resume_proposed": ("docx", "md"), "cover_letter": ("md",)}
LEVELS = ("light", "medium", "heavy")
COVER_LETTER_NEEDS = ("required", "not_required")
MAX_SUMMARY = 2000


def _kind(kind: str) -> str:
    normalized = kind.replace("-", "_")
    if normalized == "resume":
        normalized = "resume_proposed"
    if normalized not in STEMS:
        raise JobTrackerError("invalid_document",
                              "kind must be resume-proposed or cover-letter")
    return normalized


def _extension(kind: str, extension: str) -> str:
    clean = extension.lower().lstrip(".")
    if clean not in EXTENSIONS[kind]:
        raise JobTrackerError(
            "invalid_document",
            f"a {kind.replace('_', ' ')} is stored as {', '.join(EXTENSIONS[kind])}",
        )
    return clean


def next_path(conn: sqlite3.Connection, paths: Paths, job_id: str, kind: str,
              extension: str) -> Path:
    """Where to write the next version of a document. Never an existing file."""
    kind = _kind(kind)
    extension = _extension(kind, extension)
    base = applications.folder(conn, paths, job_id)
    base.mkdir(parents=True, exist_ok=True)
    return next_version_path(base, STEMS[kind], extension)


# ── registration ──────────────────────────────────────────────────────────

def _text_list(field: str, value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip()
                                          for v in value):
        raise JobTrackerError("invalid_document", f"'{field}' must be a list of texts",
                              field=field)
    return [v.strip() for v in value]


def _rule_ids(conn: sqlite3.Connection, value: object) -> list[int]:
    if value is None:
        return []
    if not isinstance(value, list) or any(isinstance(v, bool) or not isinstance(v, int)
                                          for v in value):
        raise JobTrackerError("invalid_document", "'applied_rules' must be a list of rule ids",
                              field="applied_rules")
    for rule_id in value:
        if conn.execute("SELECT 1 FROM rules WHERE id = ?", (rule_id,)).fetchone() is None:
            raise JobTrackerError("invalid_document", f"there is no rule {rule_id}",
                                  field="applied_rules")
    return list(dict.fromkeys(value))


def _language(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z]{2}", value):
        raise JobTrackerError("invalid_document",
                              "'language' must be a 2-letter code such as en or es",
                              field="language")
    return value


def validate_meta(conn: sqlite3.Connection, kind: str, meta: object) -> dict:
    """What a registered document must say about itself."""
    if not isinstance(meta, dict):
        raise JobTrackerError("invalid_document", "expected an object describing the document")
    unknown = sorted(set(meta) - {"language", "summary", "level", "support", "gaps",
                                  "applied_rules", "base"})
    if unknown:
        raise JobTrackerError("invalid_document", f"'{unknown[0]}' is not a document field",
                              field=unknown[0])
    summary = meta.get("summary")
    if summary is not None and (not isinstance(summary, str) or len(summary) > MAX_SUMMARY):
        raise JobTrackerError("invalid_document",
                              f"'summary' must be text of at most {MAX_SUMMARY} characters",
                              field="summary")
    summary = summary.strip() if isinstance(summary, str) else None
    if kind == "resume_proposed" and not summary:
        raise JobTrackerError("invalid_document",
                              "a proposed resume needs a 'summary' of what changed and why",
                              field="summary")
    level = meta.get("level", "light")
    if level not in LEVELS:
        raise JobTrackerError("invalid_document", f"'level' must be one of: {', '.join(LEVELS)}",
                              field="level")
    support = meta.get("support") or []
    if not isinstance(support, list):
        raise JobTrackerError("invalid_document", "'support' must be a list", field="support")
    checked_support = []
    for item in support:
        term = item.get("term") if isinstance(item, dict) else None
        source = item.get("source") if isinstance(item, dict) else None
        if not isinstance(term, str) or not term.strip() or not isinstance(source, str) \
                or not source.strip():
            raise JobTrackerError(
                "invalid_document",
                "each 'support' entry needs a 'term' and the 'source' line of the base resume "
                "or profile that backs it", field="support",
            )
        checked_support.append({"term": term.strip(), "source": source.strip()})
    return {
        "language": _language(meta.get("language")),
        "summary": summary,
        "level": level,
        "support": checked_support,
        "gaps": _text_list("gaps", meta.get("gaps")),
        "applied_rules": _rule_ids(conn, meta.get("applied_rules")),
        "base": meta.get("base"),
    }


def _name_pattern(kind: str) -> re.Pattern:
    extensions = "|".join(EXTENSIONS[kind])
    return re.compile(rf"^{STEMS[kind]}-v\d+\.({extensions})$")


def register(conn: sqlite3.Connection, paths: Paths, job_id: str, kind: str, file_name: str,
             meta: object) -> dict:
    """Register a document the agent wrote in the application folder."""
    kind = _kind(kind)
    name = Path(file_name).name
    if not _name_pattern(kind).match(name):
        raise JobTrackerError(
            "invalid_document",
            f"'{name}' does not follow the naming rule; get the path from `documents path`",
        )
    checked = validate_meta(conn, kind, meta)
    app_row = applications._row(conn, job_id)
    if conn.execute("SELECT 1 FROM documents WHERE application_id = ? AND file_name = ?",
                    (app_row["id"], name)).fetchone():
        raise JobTrackerError("already_registered",
                              f"'{name}' is already registered; write a new version instead")
    base_id = None
    if kind == "resume_proposed":
        from . import resume

        posting = applications.application(conn, job_id)["posting"]
        if checked["base"] is not None and not isinstance(checked["base"], str):
            raise JobTrackerError("invalid_document",
                                  "'base' is the language code of the base resume used",
                                  field="base")
        base_id = resume.choose_base(conn, paths, posting["language"], checked["base"])["id"]
    elif checked["base"] is not None:
        raise JobTrackerError("invalid_document", "only a resume has a base resume",
                              field="base")
    document = applications.register_document(conn, paths, job_id, kind, name, "agent")
    conn.execute(
        "UPDATE documents SET language = ?, change_summary = ?, level = ?, support = ?,"
        " gaps = ?, applied_rules = ?, base_resume_id = ? WHERE id = ?",
        (checked["language"], checked["summary"], checked["level"],
         json.dumps(checked["support"], ensure_ascii=False),
         json.dumps(checked["gaps"], ensure_ascii=False),
         json.dumps(checked["applied_rules"]), base_id, document["id"]),
    )
    if kind == "cover_letter" and app_row["cover_letter_need"] != "required":
        conn.execute("UPDATE applications SET cover_letter_need = 'required' WHERE id = ?",
                     (app_row["id"],))
    bump_changes(conn)
    return get(conn, document["id"])


def set_cover_letter_need(conn: sqlite3.Connection, job_id: str, need: str,
                          reason: str | None = None) -> dict:
    """Record whether this application needs a cover letter, and why."""
    if need not in COVER_LETTER_NEEDS:
        raise JobTrackerError("invalid_document",
                              f"need must be one of: {', '.join(COVER_LETTER_NEEDS)}")
    row = applications._row(conn, job_id)
    clean = " ".join((reason or "").split()) or None
    if clean and len(clean) > 300:
        raise JobTrackerError("invalid_document", "the reason is longer than 300 characters")
    now = now_iso()
    conn.execute(
        "UPDATE applications SET cover_letter_need = ?, cover_letter_reason = ?, updated_at = ?"
        " WHERE id = ?", (need, clean, now, row["id"]),
    )
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
        " VALUES ('application', ?, 'cover_letter_need', ?, ?)",
        (job_id, json.dumps({"need": need, "reason": clean}, ensure_ascii=False), now),
    )
    bump_changes(conn)
    return cover_letter(conn, row["id"])


def cover_letter(conn: sqlite3.Connection, application_id: int) -> dict:
    row = conn.execute("SELECT cover_letter_need, cover_letter_reason FROM applications"
                       " WHERE id = ?", (application_id,)).fetchone()
    has = conn.execute("SELECT 1 FROM documents WHERE application_id = ? AND kind ="
                       " 'cover_letter' AND is_current = 1", (application_id,)).fetchone()
    return {"need": row["cover_letter_need"], "reason": row["cover_letter_reason"],
            "written": has is not None}


# ── reading ───────────────────────────────────────────────────────────────

def _loads(value: str | None, default):
    return json.loads(value) if value else default


def _dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "kind": row["kind"], "file_name": row["file_name"],
        "version": row["version"], "origin": row["origin"],
        "original_name": row["original_name"], "size_bytes": row["size_bytes"],
        "created_at": row["created_at"], "current": bool(row["is_current"]),
        "language": row["language"], "summary": row["change_summary"], "level": row["level"],
        "support": _loads(row["support"], []), "gaps": _loads(row["gaps"], []),
        "applied_rules": _loads(row["applied_rules"], []),
        "base_resume": _base_ref(conn, row),
    }


def _base_ref(conn: sqlite3.Connection, row: sqlite3.Row) -> dict | None:
    """Which base resume a tailored resume came from (language and version)."""
    if row["base_resume_id"] is None:
        return None
    base = conn.execute(
        "SELECT id, language, version FROM base_resumes WHERE id = ?", (row["base_resume_id"],)
    ).fetchone()
    return {"id": base["id"], "language": base["language"], "version": base["version"]} \
        if base else None


def get(conn: sqlite3.Connection, document_id: int) -> dict:
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    if row is None:
        raise JobTrackerError("not_found", f"There is no document {document_id}")
    return _dict(conn, row)


def list_for(conn: sqlite3.Connection, job_id: str) -> list[dict]:
    row = applications._row(conn, job_id)
    return [_dict(conn, r) for r in conn.execute(
        "SELECT * FROM documents WHERE application_id = ? ORDER BY kind, version DESC",
        (row["id"],))]


def current(conn: sqlite3.Connection, application_id: int, kind: str) -> dict | None:
    row = conn.execute("SELECT * FROM documents WHERE application_id = ? AND kind = ?"
                       " AND is_current = 1", (application_id, kind)).fetchone()
    return _dict(conn, row) if row else None


# ── comparison with the base resume ───────────────────────────────────────

def _lines(text: str) -> list[str]:
    return [" ".join(line.split()) for line in text.splitlines() if line.strip()]


def diff(conn: sqlite3.Connection, paths: Paths, job_id: str,
         document_id: int | None = None) -> dict:
    """The passages of a proposed resume that differ from the base resume it came from."""
    from . import resume

    app_row = applications._row(conn, job_id)
    if document_id is None:
        doc = current(conn, app_row["id"], "resume_proposed")
        if doc is None:
            raise JobTrackerError("not_found", f"{job_id} has no proposed resume")
    else:
        doc = get(conn, document_id)
        found = conn.execute("SELECT 1 FROM documents WHERE id = ? AND application_id = ?",
                             (document_id, app_row["id"])).fetchone()
        if found is None or doc["kind"] != "resume_proposed":
            raise JobTrackerError("not_found",
                                  f"{job_id} has no proposed resume {document_id}")
    if doc["base_resume"] is not None:
        base = resume.by_id(conn, paths, doc["base_resume"]["id"])
    else:  # registered before languages were recorded
        base = resume.current(conn, paths)
    if base is None:
        raise JobTrackerError("no_base_resume", "There is no base resume to compare with")
    base_text = Path(base["text_path"]).read_text(encoding="utf-8")
    path = applications.document_path(conn, paths, job_id, doc["id"])
    proposed_text = resume.extract_text(path)

    old, new = _lines(base_text), _lines(proposed_text)
    hunks = []
    added = removed = 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        hunks.append({"op": op, "base": old[i1:i2], "proposed": new[j1:j2],
                      "context": old[i1 - 1] if i1 > 0 else None})
        removed += i2 - i1
        added += j2 - j1
    return {
        "document": doc,
        "base_resume": {"version": base["version"], "language": base["language"],
                        "original_name": base["original_name"]},
        "hunks": hunks,
        "stats": {"base_lines": len(old), "proposed_lines": len(new),
                  "added": added, "removed": removed},
    }
