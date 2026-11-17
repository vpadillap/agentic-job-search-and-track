"""Advice from the user's own results, offered only at the prescriptive level.

Every recommendation carries the counts it rests on and says it reflects
patterns in the user's own data. None of them requires any action.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

from . import insights, learning, predict, salary, stats
from .db import bump_changes, now_iso
from .errors import JobTrackerError

EXPERIMENT_SIZE = 10
EXPERIMENT_DIMENSIONS = {"cover_letter": ("yes", "no"), "resume_kind": ("tailored", "base")}


def _today() -> date:
    return datetime.now().date()


def available(conn: sqlite3.Connection, today: date | None = None) -> bool:
    return learning.level(conn, today)["level"] >= 3


# ── apply next ────────────────────────────────────────────────────────────

def apply_next(conn: sqlite3.Connection, today: date | None = None) -> list[dict] | None:
    """Tracked postings not applied to yet, most promising first."""
    if not available(conn, today):
        return None
    model = learning.latest_model(conn)
    ranked = []
    for row in conn.execute(
        "SELECT a.job_id, a.posting_id, p.title, p.company FROM applications a"
        " JOIN statuses s ON s.id = a.status_id JOIN postings p ON p.id = a.posting_id"
        " WHERE a.applied_on IS NULL AND s.ends = 0"
    ):
        estimate = predict.estimate(conn, row["posting_id"], today, model=model)
        ranked.append({"job_id": row["job_id"], "posting_id": row["posting_id"],
                       "title": row["title"], "company": row["company"],
                       "estimate": estimate})
    ranked.sort(key=lambda r: -(r["estimate"]["probability"] if r["estimate"] else 0))
    return ranked


# ── salary ask ────────────────────────────────────────────────────────────

def salary_guidance(conn: sqlite3.Connection, posting_id: int,
                    today: date | None = None) -> dict | None:
    """How much to ask: within the evidence range, at the highest band whose results
    are not clearly worse. None without reliable salary data."""
    if not available(conn, today):
        return None
    suggestion = salary.current(conn, posting_id)
    if not suggestion or suggestion["status"] != "suggested":
        return None
    bands = {g["group"]: g for g in insights.breakdown(conn, "salary_delta", "all",
                                                         today)["groups"]}
    overall = insights.breakdown(conn, "salary_delta", "all", today)["overall_rate"]
    median, top = suggestion["amount"], suggestion["range_max"] or suggestion["amount"]
    choice, basis = "at_or_below", bands.get("at_or_below")
    for band in ("over_10", "up_to_10"):
        group = bands.get(band)
        if group and not group["insufficient"] and group["high"] >= overall:
            choice, basis = band, group
            break
    amount = {"at_or_below": median, "up_to_10": min(top, round(median * 1.10)),
              "over_10": top}[choice]
    effects = learning.effects(conn)
    if "salary_cap_pct" in effects:
        amount = min(amount, round(median * (1 + effects["salary_cap_pct"] / 100)))
    return {"amount": amount, "currency": suggestion["currency"], "basis": suggestion["basis"],
            "suggested": median, "range": [suggestion["range_min"], suggestion["range_max"]],
            "band": choice,
            "evidence": {"cases": basis["cases"], "interviews": basis["interviews"]}
            if basis else None,
            "cited": {b: {"cases": g["cases"], "interviews": g["interviews"]}
                      for b, g in bands.items() if b != "unknown"}}


# ── resume emphasis ───────────────────────────────────────────────────────

def resume_emphasis(conn: sqlite3.Connection, paths, today: date | None = None) -> dict | None:
    """Terms common in postings that led to interviews: those in the user's resumes
    are emphasis; the rest are gaps, never recommended as emphasis."""
    from . import resume

    if not available(conn, today):
        return None
    resolved = [i for i in insights.outcomes(conn, today) if i["resolved"]]
    good = [insights.terms(i["description"]) for i in resolved if i["interview"]]
    rest = [insights.terms(i["description"]) for i in resolved if not i["interview"]]
    if len(good) < insights.MIN_CASES:
        return {"emphasis": [], "gaps": [], "interview_postings": len(good)}
    resume_terms: set[str] = set()
    for base in resume.list_current(conn, paths):
        resume_terms |= insights.terms(Path(base["text_path"]).read_text(encoding="utf-8"))
    counts: dict[str, tuple[int, int]] = {}
    for term in set().union(*good):
        in_good = sum(term in g for g in good)
        in_rest = sum(term in r for r in rest)
        counts[term] = (in_good, in_rest)
    emphasis, gaps = [], []
    for term, (in_good, in_rest) in sorted(counts.items(), key=lambda kv: -kv[1][0]):
        good_share = in_good / len(good)
        rest_share = in_rest / len(rest) if rest else 0.0
        if good_share >= 0.5 and good_share >= 1.5 * rest_share:
            entry = {"term": term, "in_interview_postings": in_good, "of": len(good),
                     "in_other_postings": in_rest, "of_other": len(rest)}
            (emphasis if term in resume_terms else gaps).append(entry)
    return {"emphasis": emphasis[:10], "gaps": gaps[:10], "interview_postings": len(good)}


# ── timing ────────────────────────────────────────────────────────────────

def timing(conn: sqlite3.Connection, today: date | None = None) -> dict | None:
    if not available(conn, today):
        return None
    days = insights.summary(conn, "all", today)["response_days"]
    if len(days) < insights.MIN_CASES:
        return None
    return {"follow_up_after_days": max(1, round(stats.median(days) or 1)),
            "ghost_after_days": max(days) + 2, "responses": len(days),
            "median_days": stats.median(days), "latest_day": max(days)}


# ── experiments ───────────────────────────────────────────────────────────

def experiment_proposals(conn: sqlite3.Connection, today: date | None = None) -> list[dict]:
    """Questions the data cannot settle: both options tried, intervals overlap."""
    if not available(conn, today):
        return []
    open_dims = {r["dimension"] for r in conn.execute(
        "SELECT dimension FROM experiments WHERE status IN ('proposed', 'active')")}
    result = []
    for dim, (a, b) in EXPERIMENT_DIMENSIONS.items():
        if dim in open_dims:
            continue
        groups = {g["group"]: g for g in insights.breakdown(conn, dim, "all", today)["groups"]}
        ga, gb = groups.get(a), groups.get(b)
        if not ga or not gb or ga["insufficient"] or gb["insufficient"]:
            continue
        if ga["low"] <= gb["high"] and gb["low"] <= ga["high"]:
            result.append({"dimension": dim, "option_a": a, "option_b": b,
                           "planned": EXPERIMENT_SIZE,
                           "evidence": {a: {"cases": ga["cases"], "interviews": ga["interviews"]},
                                        b: {"cases": gb["cases"], "interviews": gb["interviews"]}}})
    return result


def _experiment(conn: sqlite3.Connection, experiment_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,)).fetchone()
    if row is None:
        raise JobTrackerError("not_found", f"There is no experiment {experiment_id}")
    return row


def propose_experiment(conn: sqlite3.Connection, dimension: str, question: str,
                       planned: int = EXPERIMENT_SIZE) -> dict:
    if dimension not in EXPERIMENT_DIMENSIONS:
        raise JobTrackerError("invalid_experiment",
                              f"dimension must be one of: {', '.join(EXPERIMENT_DIMENSIONS)}")
    if not question.strip():
        raise JobTrackerError("invalid_experiment", "a question is required")
    a, b = EXPERIMENT_DIMENSIONS[dimension]
    cursor = conn.execute(
        "INSERT INTO experiments (dimension, option_a, option_b, planned, status, question,"
        " proposed_at) VALUES (?, ?, ?, ?, 'proposed', ?, ?)",
        (dimension, a, b, planned, question.strip(), now_iso()))
    bump_changes(conn)
    return experiment(conn, cursor.lastrowid)


def decide_experiment(conn: sqlite3.Connection, experiment_id: int, accept: bool) -> dict:
    row = _experiment(conn, experiment_id)
    if row["status"] != "proposed":
        raise JobTrackerError("invalid_state", f"Experiment {experiment_id} is {row['status']}")
    if accept:
        conn.execute("UPDATE experiments SET status = 'active', accepted_at = ? WHERE id = ?",
                     (now_iso(), experiment_id))
    else:
        conn.execute("UPDATE experiments SET status = 'declined' WHERE id = ?", (experiment_id,))
    bump_changes(conn)
    return experiment(conn, experiment_id)


def experiment(conn: sqlite3.Connection, experiment_id: int,
               today: date | None = None) -> dict:
    """An experiment with its progress; an active one concludes at its planned size."""
    row = _experiment(conn, experiment_id)
    result = json.loads(row["result"]) if row["result"] else None
    progress = None
    if row["status"] in ("active", "concluded"):
        since = row["accepted_at"][:10]
        titles = insights.profile_titles(conn)
        members = [i for i in insights.outcomes(conn, today)
                   if i["applied_on"] and i["applied_on"] >= since]
        by_option: dict[str, list[dict]] = {row["option_a"]: [], row["option_b"]: []}
        for item in members:
            value = insights.features_of(item, titles)[row["dimension"]]
            if value in by_option:
                by_option[value].append(item)
        progress = {option: {"applied": len(items),
                             "resolved": sum(i["resolved"] for i in items),
                             "interviews": sum(i["interview"] for i in items if i["resolved"])}
                    for option, items in by_option.items()}
        done = sum(p["resolved"] for p in progress.values())
        if row["status"] == "active" and done >= row["planned"]:
            overall_cases = sum(p["resolved"] for p in progress.values())
            overall = sum(p["interviews"] for p in progress.values()) / overall_cases
            rates = {o: stats.smoothed_rate(p["interviews"], p["resolved"], overall)
                     for o, p in progress.items() if p["resolved"]}
            a, b = rates.get(row["option_a"]), rates.get(row["option_b"])
            clear = bool(a and b and (a["low"] > b["high"] or b["low"] > a["high"]))
            result = {"counts": progress, "clear_difference": clear,
                      "better": (row["option_a"] if a["rate"] > b["rate"] else row["option_b"])
                      if clear else None}
            conn.execute("UPDATE experiments SET status = 'concluded', concluded_at = ?,"
                         " result = ? WHERE id = ?",
                         (now_iso(), json.dumps(result), experiment_id))
            row = _experiment(conn, experiment_id)
    return {"id": row["id"], "dimension": row["dimension"], "option_a": row["option_a"],
            "option_b": row["option_b"], "planned": row["planned"], "status": row["status"],
            "question": row["question"], "proposed_at": row["proposed_at"],
            "accepted_at": row["accepted_at"], "concluded_at": row["concluded_at"],
            "progress": progress, "result": result}


def experiments(conn: sqlite3.Connection, today: date | None = None) -> list[dict]:
    return [experiment(conn, r["id"], today) for r in conn.execute(
        "SELECT id FROM experiments ORDER BY id DESC")]


def all_recommendations(conn: sqlite3.Connection, paths, today: date | None = None) -> dict | None:
    if not available(conn, today):
        return None
    return {"apply_next": apply_next(conn, today), "timing": timing(conn, today),
            "resume_emphasis": resume_emphasis(conn, paths, today),
            "experiments": experiment_proposals(conn, today),
            "note": "Based on patterns in your own results (correlation, not proof). "
                    "None of this requires action."}
