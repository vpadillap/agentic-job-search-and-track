"""The learning refresh, run before scoring and before tailoring.

Cheap and automatic: recomputes the numbers, refits a model only when enough
new outcomes or decisions arrived since its last fit, writes the full history
for the agent, and returns the active lessons and new lesson candidates. A
candidate changes nothing until the agent proposes it and the user applies it.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

from . import insights, learning, predict
from .db import bump_changes, now_iso
from .paths import Paths

REFIT_AFTER = 10
LAST_REFRESH = "learning.last_refresh"
LAST_LEVEL = "learning.level"


def history_path(paths: Paths) -> Path:
    return paths.home / "learning" / "history.jsonl"


# ── the full history ──────────────────────────────────────────────────────

def _similarity(target: dict | None, item: dict, titles: list[str]) -> float:
    if target is None:
        return 0.0
    score = 0.0
    if insights.title_group(item.get("title") or "", titles) == target["title_group"]:
        score += 3
    if item.get("language") and item.get("language") == target["language"]:
        score += 1
    if (item.get("work_mode") or insights.NOT_STATED) == target["work_mode"]:
        score += 1
    words = insights.terms(item.get("description"))
    if words and target["terms"]:
        score += 3 * len(words & target["terms"]) / len(words | target["terms"])
    return round(score, 3)


def write_history(conn: sqlite3.Connection, paths: Paths, posting_id: int | None = None,
                  today: date | None = None) -> dict:
    """Every outcome, decision, and correction, one JSON line each, nothing left out.
    With a posting, the most similar records come first."""
    titles = insights.profile_titles(conn)
    target = None
    if posting_id is not None:
        row = conn.execute("SELECT * FROM postings WHERE id = ?", (posting_id,)).fetchone()
        if row is not None:
            target = {"title_group": insights.title_group(row["title"], titles),
                      "language": row["language"],
                      "work_mode": row["work_mode"] or insights.NOT_STATED,
                      "terms": insights.terms(row["description"])}
    records: list[dict] = []
    applied = set()
    for item in insights.outcomes(conn, today):
        applied.add(item["posting_id"])
        snap = item["snapshot"]
        outcome = ("offer" if item["offer"] else "interview" if item["interview"]
                   else "response" if item["responded"] else "no_response" if item["resolved"]
                   else "pending")
        records.append({
            "type": "application", "job_id": item["job_id"], "posting_id": item["posting_id"],
            "title": item["title"], "company": item["company"], "language": item["language"],
            "work_mode": item["work_mode"],
            "work_mode_corrected": item["work_mode_source"] == "user",
            "provider": item["provider"], "status": item["status"],
            "status_path": item["status_path"], "outcome": outcome,
            "applied_on": item["applied_on"], "days_to_response": item["days_to_response"],
            "score": snap.get("score"), "score_components": snap.get("score_components"),
            "resume_kind": snap.get("resume_kind"), "cover_letter": snap.get("cover_letter"),
            "channel": snap.get("channel"), "asked_salary": snap.get("asked_salary"),
            "suggested_salary": snap.get("suggested_salary"),
            "similarity": _similarity(target, item, titles)})
    for item in insights.decisions(conn):
        if item["posting_id"] in applied:
            continue
        records.append({
            "type": "dismissal" if item["decision"] == "dismissed" else "tracked_not_applied",
            "posting_id": item["posting_id"], "job_id": item["job_id"], "title": item["title"],
            "company": item["company"], "language": item["language"],
            "work_mode": item["work_mode"], "provider": item["provider"],
            "reason": item["reason"], "note": item["note"], "on": item["on"],
            "similarity": _similarity(target, item, titles)})
    for item in insights.corrections(conn):
        records.append({"type": "correction", **item, "similarity": 0.0})
    order = {"application": 0, "tracked_not_applied": 1, "dismissal": 2, "correction": 3}
    records.sort(key=lambda r: (order[r["type"]], -r["similarity"],
                                -(int((r.get("applied_on") or r.get("on") or "0")
                                      .replace("-", "")) or 0)))
    path = history_path(paths)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    counts: dict[str, int] = {}
    for record in records:
        counts[record["type"]] = counts.get(record["type"], 0) + 1
    return {"path": str(path), "records": len(records), "counts": counts,
            "ordered_for_posting": posting_id if target else None}


# ── refresh ───────────────────────────────────────────────────────────────

def _due(conn: sqlite3.Connection, kind: str, count: int, ready: bool) -> bool:
    last = learning.analyses(conn, 1, kind)
    if not last:
        return ready
    return count - last[0]["resolved"] >= REFIT_AFTER


def refresh(conn: sqlite3.Connection, paths: Paths, posting_id: int | None = None,
            today: date | None = None) -> dict:
    today = today or datetime.now().date()
    summary = insights.summary(conn, "all", today)
    resolved, interviews = summary["resolved"], summary["interview"]["count"]
    refits = {}
    if _due(conn, "interview", resolved, resolved >= learning.PREDICTIVE_RESOLVED
            and interviews >= learning.PREDICTIVE_INTERVIEWS):
        refits["interview"] = predict.fit(conn, today)["validation"]
    made = summary["decisions"]["tracked"] + summary["decisions"]["dismissed"]
    if _due(conn, "fit", made, made >= predict.FIT_DECISIONS):
        refits["fit"] = predict.fit_preference(conn, today)["validation"]
    history = write_history(conn, paths, posting_id, today)
    from .rules import list_rules

    current = learning.level(conn, today)
    previous = conn.execute("SELECT value FROM settings WHERE key = ?",
                            (LAST_LEVEL,)).fetchone()
    changed = None
    if previous is None or previous["value"] != current["name"]:
        changed = {"from": previous["value"] if previous else None, "to": current["name"]}
        conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)"
                     " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                     (LAST_LEVEL, current["name"]))
        conn.execute("INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
                     " VALUES ('learning', 'level', 'level_changed', ?, ?)",
                     (json.dumps(changed), now_iso()))
    result = {
        "level": current,
        "level_changed": changed,
        "summary": {k: v for k, v in summary.items() if k != "response_days"},
        "refitted": refits,
        "fit_estimate_available": learning.latest_model(conn, "fit") is not None,
        "effects": learning.effects(conn),
        "active_lessons": [r for r in list_rules(conn, "active") if r["origin"] == "learned"],
        "history": history,
        "candidates": learning.candidates(conn, "all", today)["candidates"],
    }
    if posting_id is not None:
        result["posting"] = {"posting_id": posting_id,
                             "interview_estimate": predict.estimate(conn, posting_id, today),
                             "fit": predict.fit_estimate(conn, posting_id, today)}
    conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)"
                 " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                 (LAST_REFRESH, now_iso()))
    bump_changes(conn)
    result["refreshed_at"] = last_refresh(conn)
    return result


def last_refresh(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (LAST_REFRESH,)).fetchone()
    return row["value"] if row else None
