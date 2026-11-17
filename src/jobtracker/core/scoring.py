"""Alignment scores: the agent judges four components inside a fixed, versioned rubric.

The fifth component, history, comes from the user's own outcomes. Until the
learning loop supplies it, it is neutral: half of its maximum.
"""
from __future__ import annotations

import json
import sqlite3

from .db import bump_changes, now_iso
from .errors import JobTrackerError

COMPONENTS = ("title", "skills", "seniority", "conditions", "history")
JUDGED = ("title", "skills", "seniority", "conditions")
RESUME_KINDS = ("base", "tailored", "sent")
NEUTRAL_HISTORY_NOTE = {
    "en": "Neutral until there are enough outcomes to learn from.",
    "es": "Neutral hasta tener suficientes resultados de los que aprender.",
}


def _fail(message: str, **details: object):
    raise JobTrackerError("invalid_score", message, **details)


# ── weights ───────────────────────────────────────────────────────────────

def active_weights(conn: sqlite3.Connection) -> dict:
    row = conn.execute("SELECT * FROM score_weights WHERE is_active = 1").fetchone()
    return {"version": row["version"], "weights": json.loads(row["weights"]),
            "note": row["note"], "created_at": row["created_at"]}


def weights_history(conn: sqlite3.Connection) -> list[dict]:
    return [
        {"version": r["version"], "weights": json.loads(r["weights"]), "note": r["note"],
         "created_at": r["created_at"], "active": bool(r["is_active"])}
        for r in conn.execute("SELECT * FROM score_weights ORDER BY version")
    ]


def set_weights(conn: sqlite3.Connection, weights: object, note: str | None = None) -> dict:
    """Store new component maximums as a new version. Earlier scores keep their version."""
    if not isinstance(weights, dict) or set(weights) != set(COMPONENTS):
        _fail(f"weights need exactly these components: {', '.join(COMPONENTS)}")
    for component, value in weights.items():  # type: ignore[union-attr]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _fail(f"the maximum of '{component}' must be a whole number of 0 or more")
    if sum(weights.values()) != 100:  # type: ignore[union-attr]
        _fail("the maximums must add up to 100")
    latest = conn.execute("SELECT MAX(version) FROM score_weights").fetchone()[0]
    now = now_iso()
    conn.execute("UPDATE score_weights SET is_active = 0 WHERE is_active = 1")
    conn.execute(
        "INSERT INTO score_weights (version, weights, note, created_at, is_active)"
        " VALUES (?, ?, ?, ?, 1)",
        (latest + 1, json.dumps({c: weights[c] for c in COMPONENTS}), note, now),  # type: ignore[index]
    )
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
        " VALUES ('score_weights', ?, 'created', ?, ?)",
        (str(latest + 1), json.dumps({"note": note}), now),
    )
    bump_changes(conn)
    return active_weights(conn)


# ── scores ────────────────────────────────────────────────────────────────

def _component(name: str, value: object, maximum: int) -> dict:
    if not isinstance(value, dict):
        _fail(f"'{name}' must be an object with 'points' and 'note'", component=name)
    points = value.get("points")  # type: ignore[union-attr]
    if isinstance(points, bool) or not isinstance(points, int):
        _fail(f"'{name}.points' must be a whole number", component=name)
    if not 0 <= points <= maximum:  # type: ignore[operator]
        _fail(f"'{name}' has {points} points but its maximum is {maximum}", component=name)
    note = value.get("note")  # type: ignore[union-attr]
    if not isinstance(note, str) or not note.strip():
        _fail(f"'{name}.note' is required: explain the points in one or two sentences",
              component=name)
    result = {"component": name, "points": points, "max": maximum, "note": note.strip()}
    if name == "skills":
        for key in ("matched", "missing"):
            items = value.get(key)  # type: ignore[union-attr]
            if not isinstance(items, list) or any(
                    not isinstance(i, str) or not i.strip() for i in items):
                _fail(f"'skills.{key}' must be a list of skill names (it may be empty)",
                      component=name)
            result[key] = [i.strip() for i in items]
        unnamed = [s for s in result["missing"] if s.casefold() not in result["note"].casefold()]
        if unnamed:
            _fail("the skills note must name each missing skill: " + ", ".join(unnamed),
                  component=name)
    return result


def validate(submission: object, weights: dict, language: str = "en") -> dict:
    """Check a submitted score against the active weights; returns the full breakdown."""
    if not isinstance(submission, dict):
        _fail("a score must be an object with 'components'")
    components = submission.get("components")  # type: ignore[union-attr]
    if isinstance(components, list):
        components = {c.get("component"): c for c in components if isinstance(c, dict)}
    if not isinstance(components, dict):
        _fail("'components' must be an object keyed by component")
    if "history" in components:  # type: ignore[operator]
        _fail("'history' is supplied by the system from your own outcomes; leave it out")
    unknown = sorted(set(components) - set(JUDGED))  # type: ignore[arg-type]
    if unknown:
        _fail(f"unknown component '{unknown[0]}'; components are {', '.join(JUDGED)}")
    missing = [c for c in JUDGED if c not in components]  # type: ignore[operator]
    if missing:
        _fail(f"missing component '{missing[0]}'")
    breakdown = [_component(c, components[c], weights[c]) for c in JUDGED]  # type: ignore[index]
    history_max = weights["history"]
    breakdown.append({
        "component": "history", "points": history_max // 2, "max": history_max,
        "note": NEUTRAL_HISTORY_NOTE.get(language, NEUTRAL_HISTORY_NOTE["en"]),
        "neutral": True,
    })
    total = sum(item["points"] for item in breakdown)
    submitted = submission.get("total")  # type: ignore[union-attr]
    if submitted is not None and submitted != total:
        _fail(f"the total {submitted} does not match the sum of the components ({total}, "
              f"including {history_max // 2} neutral points for history)")
    resume = submission.get("resume") or {}  # type: ignore[union-attr]
    if not isinstance(resume, dict) or resume.get("kind", "base") not in RESUME_KINDS:
        _fail(f"'resume.kind' must be one of: {', '.join(RESUME_KINDS)}")
    return {"total": total, "components": breakdown,
            "resume_kind": resume.get("kind", "base"), "resume_ref": resume.get("ref")}


def _to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "posting_id": row["posting_id"], "total": row["total"],
        "components": json.loads(row["components"]), "weights_version": row["weights_version"],
        "resume_kind": row["resume_kind"], "resume_ref": row["resume_ref"],
        "run_id": row["run_id"], "created_at": row["created_at"],
        "current": bool(row["is_current"]),
    }


def set_score(
    conn: sqlite3.Connection, posting_id: int, submission: object, *,
    run_id: int | None = None, language: str = "en",
) -> dict:
    """Store a new current score; the previous one stays in history."""
    if conn.execute("SELECT 1 FROM postings WHERE id = ?", (posting_id,)).fetchone() is None:
        raise JobTrackerError("not_found", f"There is no posting {posting_id}")
    weights = active_weights(conn)
    checked = validate(submission, weights["weights"], language)
    if checked["resume_ref"] is None and checked["resume_kind"] == "base":
        base = conn.execute("SELECT version FROM base_resumes WHERE is_current = 1"
                            " AND is_main = 1").fetchone()
        checked["resume_ref"] = str(base["version"]) if base else None
    previous = current(conn, posting_id)
    now = now_iso()
    conn.execute("UPDATE scores SET is_current = 0 WHERE posting_id = ? AND is_current = 1",
                 (posting_id,))
    cursor = conn.execute(
        "INSERT INTO scores (posting_id, weights_version, total, components, resume_kind,"
        " resume_ref, run_id, created_at, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (posting_id, weights["version"], checked["total"],
         json.dumps(checked["components"], ensure_ascii=False), checked["resume_kind"],
         None if checked["resume_ref"] is None else str(checked["resume_ref"]), run_id, now),
    )
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
        " VALUES ('posting', ?, 'scored', ?, ?)",
        (str(posting_id), json.dumps({
            "score_id": cursor.lastrowid, "total": checked["total"],
            "previous_total": previous["total"] if previous else None,
            "resume_kind": checked["resume_kind"], "resume_ref": checked["resume_ref"],
        }), now),
    )
    bump_changes(conn)
    return current(conn, posting_id)  # type: ignore[return-value]


def current(conn: sqlite3.Connection, posting_id: int) -> dict | None:
    """The current score, with the total it replaced (so a change can be shown)."""
    rows = conn.execute(
        "SELECT * FROM scores WHERE posting_id = ? ORDER BY is_current DESC, id DESC LIMIT 2",
        (posting_id,),
    ).fetchall()
    if not rows or not rows[0]["is_current"]:
        return None
    result = _to_dict(rows[0])
    result["previous_total"] = rows[1]["total"] if len(rows) > 1 else None
    result["previous_resume_ref"] = rows[1]["resume_ref"] if len(rows) > 1 else None
    return result


def history(conn: sqlite3.Connection, posting_id: int) -> list[dict]:
    return [_to_dict(r) for r in conn.execute(
        "SELECT * FROM scores WHERE posting_id = ? ORDER BY id DESC", (posting_id,))]


def at_application(conn: sqlite3.Connection, posting_id: int) -> dict | None:
    """The score that was current when the user marked the posting as applied."""
    found = conn.execute(
        "SELECT s.data FROM application_snapshots s JOIN applications a"
        " ON a.job_id = s.application_id WHERE a.posting_id = ?", (posting_id,),
    ).fetchone()
    if found is None:
        return None
    score_id = json.loads(found["data"]).get("score_id")
    if score_id is None:
        return None
    row = conn.execute("SELECT * FROM scores WHERE id = ?", (score_id,)).fetchone()
    return _to_dict(row) if row else None
