"""Proposed answers to a posting's application-form questions.

One current answer per question. The agent's proposals replace earlier agent
proposals, but never an answer the user edited: those proposals are kept as
alternatives the user can pick. An answer the agent cannot support from the
user's data is stored as needing the user, with a note of what is missing.
"""
from __future__ import annotations

import json
import re
import sqlite3

from . import applications, search
from .db import bump_changes, now_iso
from .errors import JobTrackerError

MAX_ANSWER = 5000


def _questions(conn: sqlite3.Connection, posting_id: int) -> dict[int, dict]:
    return {q["position"]: q for q in search.questions(conn, posting_id)}


def _dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "position": row["position"], "text": row["text"],
        "origin": row["origin"], "state": row["state"], "needs_user": bool(row["needs_user"]),
        "basis": row["basis"], "note": row["note"], "language": row["language"],
        "applied_rules": json.loads(row["applied_rules"]) if row["applied_rules"] else [],
        "created_at": row["created_at"],
    }


def _event(conn: sqlite3.Connection, job_id: str, kind: str, data: dict, when: str) -> None:
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
        " VALUES ('application', ?, ?, ?, ?)",
        (job_id, kind, json.dumps(data, ensure_ascii=False), when),
    )


def _validate(conn: sqlite3.Connection, questions: dict[int, dict], proposals: object) -> list:
    if not isinstance(proposals, list) or not proposals:
        raise JobTrackerError("invalid_answer", "expected a non-empty list of answers")
    checked, seen = [], set()
    for index, item in enumerate(proposals):
        where = f"answer {index}"
        if not isinstance(item, dict):
            raise JobTrackerError("invalid_answer", f"{where}: must be an object", index=index)
        unknown = sorted(set(item) - {"position", "text", "needs_user", "note", "basis",
                                      "language", "applied_rules"})
        if unknown:
            raise JobTrackerError("invalid_answer", f"{where}: '{unknown[0]}' is not a field",
                                  index=index)
        position = item.get("position")
        if position not in questions:
            raise JobTrackerError(
                "invalid_answer",
                f"{where}: there is no question at position {position}", index=index,
            )
        if position in seen:
            raise JobTrackerError("invalid_answer",
                                  f"{where}: question {position} is answered twice", index=index)
        seen.add(position)
        needs_user = bool(item.get("needs_user", False))
        text = item.get("text", "")
        if not isinstance(text, str) or len(text) > MAX_ANSWER:
            raise JobTrackerError(
                "invalid_answer",
                f"{where}: 'text' must be text of at most {MAX_ANSWER} characters", index=index,
            )
        text = text.strip()
        note = item.get("note")
        note = note.strip() if isinstance(note, str) and note.strip() else None
        if needs_user and not note:
            raise JobTrackerError(
                "invalid_answer",
                f"{where}: an answer left for the user needs a 'note' saying what is missing",
                index=index,
            )
        if not needs_user and not text:
            raise JobTrackerError(
                "invalid_answer",
                f"{where}: an empty answer must be marked needs_user with a note", index=index,
            )
        language = item.get("language")
        if not isinstance(language, str) or not re.fullmatch(r"[a-z]{2}", language):
            raise JobTrackerError("invalid_answer",
                                  f"{where}: 'language' must be a 2-letter code", index=index)
        basis = item.get("basis")
        basis = basis.strip() if isinstance(basis, str) and basis.strip() else None
        rules = item.get("applied_rules") or []
        if not isinstance(rules, list) or any(isinstance(r, bool) or not isinstance(r, int)
                                              for r in rules):
            raise JobTrackerError("invalid_answer",
                                  f"{where}: 'applied_rules' must be a list of rule ids",
                                  index=index)
        for rule_id in rules:
            if conn.execute("SELECT 1 FROM rules WHERE id = ?", (rule_id,)).fetchone() is None:
                raise JobTrackerError("invalid_answer", f"{where}: there is no rule {rule_id}",
                                      index=index)
        checked.append({"position": position, "text": text, "needs_user": needs_user,
                        "note": note, "basis": basis, "language": language,
                        "applied_rules": json.dumps(rules)})
    return checked


def _insert(conn: sqlite3.Connection, application_id: int, item: dict, origin: str, state: str,
            when: str) -> None:
    conn.execute(
        "INSERT INTO form_answers (application_id, position, text, origin, state, needs_user,"
        " basis, note, language, applied_rules, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (application_id, item["position"], item["text"], origin, state, int(item["needs_user"]),
         item["basis"], item["note"], item["language"], item["applied_rules"], when),
    )


def propose(conn: sqlite3.Connection, job_id: str, proposals: object, *,
            as_alternative: bool = False) -> dict:
    """Store the agent's answers. Never overwrites an answer the user edited."""
    row = applications._editable_row(conn, job_id)
    questions = _questions(conn, row["posting_id"])
    if not questions:
        raise JobTrackerError("no_form", f"{job_id} has no captured form questions to answer")
    checked = _validate(conn, questions, proposals)
    now = now_iso()
    result = {"current": [], "alternatives": []}
    for item in checked:
        existing = conn.execute(
            "SELECT * FROM form_answers WHERE application_id = ? AND position = ?"
            " AND state = 'current'", (row["id"], item["position"]),
        ).fetchone()
        if existing is not None and (as_alternative or existing["origin"] == "user"):
            _insert(conn, row["id"], item, "agent", "alternative", now)
            result["alternatives"].append(item["position"])
            continue
        if existing is not None:
            conn.execute("UPDATE form_answers SET state = 'superseded' WHERE id = ?",
                         (existing["id"],))
        _insert(conn, row["id"], item, "agent", "current", now)
        result["current"].append(item["position"])
    _event(conn, job_id, "answers_proposed",
           {"current": result["current"], "alternatives": result["alternatives"]}, now)
    conn.execute("UPDATE applications SET updated_at = ? WHERE id = ?", (now, row["id"]))
    from . import learning

    rule_ids = sorted({r for item in checked for r in json.loads(item["applied_rules"])})
    learning.record_influence(conn, "answers", job_id, rule_ids=rule_ids,
                              areas=("form", "salary"))
    bump_changes(conn)
    return {**result, "answers": list_answers(conn, job_id)}


def edit(conn: sqlite3.Connection, job_id: str, position: int, text: str) -> dict:
    """The user's own wording. It becomes the current answer and is never overwritten."""
    row = applications._editable_row(conn, job_id)
    questions = _questions(conn, row["posting_id"])
    if position not in questions:
        raise JobTrackerError("not_found", f"{job_id} has no question at position {position}")
    if not isinstance(text, str) or len(text) > MAX_ANSWER:
        raise JobTrackerError("invalid_answer",
                              f"an answer must be text of at most {MAX_ANSWER} characters")
    existing = conn.execute(
        "SELECT * FROM form_answers WHERE application_id = ? AND position = ?"
        " AND state = 'current'", (row["id"], position),
    ).fetchone()
    clean = text.strip()
    if existing is not None and existing["origin"] == "user" and existing["text"] == clean:
        return answer(conn, job_id, position)
    now = now_iso()
    language = existing["language"] if existing is not None else None
    if existing is not None:
        conn.execute("UPDATE form_answers SET state = 'superseded' WHERE id = ?",
                     (existing["id"],))
    _insert(conn, row["id"], {"position": position, "text": clean, "needs_user": not clean,
                              "note": None,
                              "basis": None, "language": language, "applied_rules": "[]"},
            "user", "current", now)
    _event(conn, job_id, "answer_edited", {"position": position}, now)
    conn.execute("UPDATE applications SET updated_at = ? WHERE id = ?", (now, row["id"]))
    bump_changes(conn)
    return answer(conn, job_id, position)


def pick(conn: sqlite3.Connection, job_id: str, answer_id: int) -> dict:
    """Make an alternative the current answer. The replaced answer is kept."""
    row = applications._editable_row(conn, job_id)
    chosen = conn.execute(
        "SELECT * FROM form_answers WHERE id = ? AND application_id = ?", (answer_id, row["id"]),
    ).fetchone()
    if chosen is None or chosen["state"] != "alternative":
        raise JobTrackerError("not_found", f"{job_id} has no alternative answer {answer_id}")
    now = now_iso()
    conn.execute(
        "UPDATE form_answers SET state = 'alternative' WHERE application_id = ? AND position = ?"
        " AND state = 'current'", (row["id"], chosen["position"]),
    )
    conn.execute("UPDATE form_answers SET state = 'current' WHERE id = ?", (answer_id,))
    _event(conn, job_id, "answer_picked", {"position": chosen["position"]}, now)
    conn.execute("UPDATE applications SET updated_at = ? WHERE id = ?", (now, row["id"]))
    bump_changes(conn)
    return answer(conn, job_id, chosen["position"])


def answer(conn: sqlite3.Connection, job_id: str, position: int) -> dict:
    return next(item for item in list_answers(conn, job_id) if item["position"] == position)


def list_answers(conn: sqlite3.Connection, job_id: str) -> list[dict]:
    """Every captured question with its current answer and the alternatives."""
    row = applications._row(conn, job_id)
    result = []
    for question in search.questions(conn, row["posting_id"]):
        rows = conn.execute(
            "SELECT * FROM form_answers WHERE application_id = ? AND position = ?"
            " AND state IN ('current', 'alternative') ORDER BY id DESC",
            (row["id"], question["position"]),
        ).fetchall()
        current = next((_dict(r) for r in rows if r["state"] == "current"), None)
        result.append({**question, "answer": current,
                       "alternatives": [_dict(r) for r in rows if r["state"] == "alternative"]})
    return result


def answered_count(conn: sqlite3.Connection, application_id: int) -> int:
    """Questions whose current answer is usable as it is."""
    return conn.execute(
        "SELECT COUNT(*) FROM form_answers WHERE application_id = ? AND state = 'current'"
        " AND needs_user = 0 AND text != ''", (application_id,),
    ).fetchone()[0]


def proposed_count(conn: sqlite3.Connection, application_id: int) -> int:
    """Questions the agent has dealt with, including those it left for the user."""
    return conn.execute(
        "SELECT COUNT(*) FROM form_answers WHERE application_id = ? AND state = 'current'",
        (application_id,),
    ).fetchone()[0]
