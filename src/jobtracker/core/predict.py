"""Estimated chance that a posting leads to an interview, from the user's own history.

The model is fitted and validated only in an analysis (`fit`). It is used only
while the latest analysis passed validation: walk-forward (train on earlier
applications, predict later ones), it must beat the user's overall rate and
rank interviews higher. Otherwise no estimate is shown anywhere.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime

from . import insights, learning, stats
from .db import bump_changes, now_iso

HALF_LIFE_DAYS = 180
BRIER_MARGIN = 0.05          # the model must beat the base rate by at least 5%
FIRST_TEST = 20              # fewest applications to train on before testing
BLOCK = 5


def _component_band(points: int | None, maximum: int | None) -> str:
    if points is None or not maximum:
        return "na"
    share = points / maximum
    return "high" if share >= 0.8 else "mid" if share >= 0.5 else "low"


def feature_row(groups: dict[str, str], components: dict | None) -> dict[str, float]:
    row = {f"{dim}={value}": 1.0 for dim, value in groups.items() if value not in
           ("unknown", "unscored")}
    for name, (points, maximum) in (components or {}).items():
        if name != "history":
            row[f"{name}={_component_band(points, maximum)}"] = 1.0
    return row


def _components_at(conn: sqlite3.Connection, facts: dict) -> dict:
    """The components of the score the application had when it was applied to."""
    if not facts.get("score_id"):
        return {}
    row = conn.execute("SELECT components FROM scores WHERE id = ?",
                       (facts["score_id"],)).fetchone()
    if row is None:
        return {}
    return {c["component"]: (c["points"], c["max"]) for c in json.loads(row["components"])}


def _training(conn: sqlite3.Connection, today: date) -> tuple[list, list, list, list]:
    titles = insights.profile_titles(conn)
    items = [i for i in learning.since_reset(conn, insights.outcomes(conn, today),
                                             "applied_on") if i["resolved"]]
    items.sort(key=lambda i: (i["applied_on"] or "", i["job_id"]))
    rows, labels, weights = [], [], []
    for item in items:
        groups = insights.features_of(item, titles)
        groups.pop("salary_delta")  # mostly unknown before applying; would leak
        rows.append(feature_row(groups, _components_at(conn, item["at_application"])))
        labels.append(1 if item["interview"] else 0)
        age = (today - date.fromisoformat(item["applied_on"])).days if item["applied_on"] else 0
        weights.append(0.5 ** (max(age, 0) / HALF_LIFE_DAYS))
    return items, rows, labels, weights


def validate(rows: list, labels: list, weights: list) -> dict:
    """Walk-forward: train on the first k, predict the next block, repeat."""
    predictions, base_predictions, actual = [], [], []
    k = max(FIRST_TEST, len(rows) // 2)
    while k < len(rows):
        model = stats.fit_logistic(rows[:k], labels[:k], weights[:k])
        base = sum(labels[:k]) / k
        for i in range(k, min(k + BLOCK, len(rows))):
            predictions.append(stats.predict(model, rows[i]))
            base_predictions.append(base)
            actual.append(labels[i])
        k += BLOCK
    if not actual:
        return {"tested": 0, "passed": False, "reason": "not enough applications to test"}
    model_brier = stats.brier(predictions, actual)
    base_brier = stats.brier(base_predictions, actual)
    order = sorted(range(len(actual)), key=lambda i: predictions[i])
    third = max(1, len(order) // 3)
    bottom = sum(actual[i] for i in order[:third])
    top = sum(actual[i] for i in order[-third:])
    calibration = []
    for low in (0.0, 0.2, 0.4, 0.6, 0.8):
        members = [i for i in range(len(actual)) if low <= predictions[i] < low + 0.2
                   or (low == 0.8 and predictions[i] == 1.0)]
        if members:
            calibration.append({
                "range": [low, round(low + 0.2, 1)], "cases": len(members),
                "predicted": round(sum(predictions[i] for i in members) / len(members), 3),
                "actual": round(sum(actual[i] for i in members) / len(members), 3)})
    passed = model_brier < base_brier * (1 - BRIER_MARGIN) and top > bottom
    reason = None if passed else (
        "the estimates do not beat your overall rate on applications they were not "
        "trained on" if model_brier >= base_brier * (1 - BRIER_MARGIN)
        else "the estimates do not rank the applications that led to interviews higher")
    return {"tested": len(actual), "model_brier": round(model_brier, 4),
            "base_brier": round(base_brier, 4), "top_third_interviews": top,
            "bottom_third_interviews": bottom, "calibration": calibration,
            "passed": passed, "reason": reason}


def fit(conn: sqlite3.Connection, today: date | None = None) -> dict:
    """Run an analysis: fit and validate the model, and record the result."""
    today = today or datetime.now().date()
    items, rows, labels, weights = _training(conn, today)
    interviews = sum(labels)
    if len(rows) < learning.PREDICTIVE_RESOLVED or interviews < learning.PREDICTIVE_INTERVIEWS:
        validation = {"passed": False, "reason": (
            f"{len(rows)} resolved applications and {interviews} interviews; estimates need "
            f"{learning.PREDICTIVE_RESOLVED} and {learning.PREDICTIVE_INTERVIEWS}")}
        model = None
    else:
        validation = validate(rows, labels, weights)
        model = None
        if validation["passed"]:
            fitted = stats.fit_logistic(rows, labels, weights)
            model = {**fitted, "base_rate": sum(labels) / len(labels),
                     "bootstrap": stats.bootstrap_models(rows, labels, weights),
                     "fitted_on": len(rows)}
    conn.execute(
        "INSERT INTO analyses (kind, created_at, resolved, interviews, passed, reason,"
        " validation, model) VALUES ('interview', ?, ?, ?, ?, ?, ?, ?)",
        (now_iso(), len(rows), interviews, int(validation["passed"]), validation["reason"],
         json.dumps(validation), json.dumps(model) if model else None))
    bump_changes(conn)
    return {"validation": validation, "level": learning.level(conn, today)}


# ── estimates ─────────────────────────────────────────────────────────────

def _posting_groups(conn: sqlite3.Connection, posting_id: int, titles: list[str],
                    today: date) -> tuple[dict, dict]:
    from . import applications, scoring

    posting = conn.execute("SELECT * FROM postings WHERE id = ?", (posting_id,)).fetchone()
    app = conn.execute("SELECT * FROM applications WHERE posting_id = ?",
                       (posting_id,)).fetchone()
    score = scoring.current(conn, posting_id)
    facts = applications.at_application(conn, app["job_id"]) if app else None
    if facts:
        item = {"at_application": facts, "title": posting["title"],
                "provider": posting["provider"], "work_mode": posting["work_mode"],
                "language": posting["language"]}
        groups = insights.features_of(item, titles)
        components = _components_at(conn, facts)
    else:
        docs = {r["kind"] for r in conn.execute(
            "SELECT kind FROM documents WHERE application_id = ? AND is_current = 1",
            (app["id"] if app else -1,))}
        posted = posting["posted_at"]
        age = (today - date.fromisoformat(posted)).days if posted else None
        item = {"title": posting["title"], "provider": posting["provider"],
                "work_mode": posting["work_mode"], "language": posting["language"],
                "at_application": {
            "score": score["total"] if score else None,
            "channel": app["channel"] if app else None, "provider": posting["provider"],
            "resume_kind": "sent" if "resume_sent" in docs else
            "tailored" if "resume_proposed" in docs else "base",
            "cover_letter": "cover_letter" in docs, "work_mode": posting["work_mode"],
            "posting_age_days": age}}
        groups = insights.features_of(item, titles)
        components = {c["component"]: (c["points"], c["max"])
                      for c in score["components"]} if score else {}
    groups.pop("salary_delta")
    return groups, components


def _label(p: float, base: float) -> str:
    if p < base * 0.75:
        return "low"
    if p > base * 1.25:
        return "high"
    return "medium"


def estimate(conn: sqlite3.Connection, posting_id: int, today: date | None = None,
             model: dict | None = None) -> dict | None:
    """The estimated interview chance of a posting, or None when estimates are off."""
    today = today or datetime.now().date()
    model = model or latest_active_model(conn, today)
    if model is None:
        return None
    titles = insights.profile_titles(conn)
    groups, components = _posting_groups(conn, posting_id, titles, today)
    row = feature_row(groups, components)
    p = stats.predict(model, row)
    samples = sorted(stats.predict(m, row) for m in model["bootstrap"])
    low = samples[int(len(samples) * 0.1)]
    high = samples[min(len(samples) - 1, int(len(samples) * 0.9))]
    factors = [{"feature": f, "effect": "up" if c > 0 else "down"}
               for f, c in stats.contributions(model, row)[:2] if abs(c) > 0.05]
    return {"probability": round(p, 3), "low": round(min(low, p), 3),
            "high": round(max(high, p), 3), "label": _label(p, model["base_rate"]),
            "base_rate": round(model["base_rate"], 3), "factors": factors}


def latest_active_model(conn: sqlite3.Connection, today: date | None = None) -> dict | None:
    """The model in force: only while the level is predictive or above."""
    if learning.level(conn, today)["level"] < 2:
        return None
    return learning.latest_model(conn)


def history_points(probability: float, base_rate: float, maximum: int) -> int:
    """The score's history component: half points at the user's usual rate."""
    base = min(max(base_rate, 0.01), 0.99)
    share = probability / (2 * base)
    return round(maximum * min(max(share, 0.0), 1.0))


def track_record(conn: sqlite3.Connection) -> dict | None:
    """How past estimates compared with what happened (from the latest analysis)."""
    recent = learning.analyses(conn, 1)
    if not recent or not recent[0]["validation"]:
        return None
    validation = recent[0]["validation"]
    return {"analysis": recent[0]["created_at"], "passed": recent[0]["passed"],
            "tested": validation.get("tested", 0),
            "calibration": validation.get("calibration", []),
            "model_brier": validation.get("model_brier"),
            "base_brier": validation.get("base_brier")}


# ── fit to the user's choices ─────────────────────────────────────────────

FIT_DECISIONS = 30
FIT_EACH = 8
REFIT_AFTER = 10


def _decision_row(conn: sqlite3.Connection, decision: dict, titles: list[str],
                  decided: date | None) -> dict[str, float]:
    """What was known about a posting when the user decided on it."""
    from . import scoring

    posted = date.fromisoformat(decision["posted_at"]) if decision.get("posted_at") else None
    age = (decided - posted).days if decided and posted else None
    score = scoring.current(conn, decision["posting_id"])
    groups = {
        "title": insights.title_group(decision["title"], titles),
        "provider": decision.get("provider") or "unknown",
        "work_mode": decision.get("work_mode") or insights.NOT_STATED,
        "contract": decision.get("contract_type") or "unknown",
        "language": decision.get("language") or "unknown",
        "score_band": insights._score_band(score["total"] if score else None),
        "posting_age": insights._posting_age(age),
    }
    components = {c["component"]: (c["points"], c["max"])
                  for c in score["components"]} if score else {}
    return feature_row(groups, components)


def _decision_training(conn: sqlite3.Connection, today: date) -> tuple[list, list, list]:
    titles = insights.profile_titles(conn)
    made = sorted(learning.since_reset(conn, insights.decisions(conn), "on"),
                  key=lambda d: (d["on"] or "", d["posting_id"]))
    rows, labels, weights = [], [], []
    for item in made:
        decided = date.fromisoformat(item["on"]) if item["on"] else None
        rows.append(_decision_row(conn, item, titles, decided))
        labels.append(1 if item["decision"] == "tracked" else 0)
        age = (today - decided).days if decided else 0
        weights.append(0.5 ** (max(age, 0) / HALF_LIFE_DAYS))
    return rows, labels, weights


def fit_preference(conn: sqlite3.Connection, today: date | None = None) -> dict:
    """Fit and validate the fit-to-you model from track and dismiss decisions."""
    today = today or datetime.now().date()
    rows, labels, weights = _decision_training(conn, today)
    tracked, dismissed = sum(labels), len(labels) - sum(labels)
    model = None
    if len(rows) < FIT_DECISIONS or tracked < FIT_EACH or dismissed < FIT_EACH:
        validation = {"passed": False, "reason": (
            f"{len(rows)} decisions ({tracked} tracked, {dismissed} dismissed); the fit "
            f"estimate needs {FIT_DECISIONS} with at least {FIT_EACH} of each")}
    else:
        validation = validate(rows, labels, weights)
        if validation["passed"]:
            fitted = stats.fit_logistic(rows, labels, weights)
            model = {**fitted, "base_rate": tracked / len(labels),
                     "bootstrap": stats.bootstrap_models(rows, labels, weights),
                     "fitted_on": len(rows)}
        elif validation.get("reason"):
            validation["reason"] = validation["reason"].replace(
                "led to interviews", "you tracked")
    conn.execute(
        "INSERT INTO analyses (kind, created_at, resolved, interviews, passed, reason,"
        " validation, model) VALUES ('fit', ?, ?, ?, ?, ?, ?, ?)",
        (now_iso(), len(rows), tracked, int(validation["passed"]), validation["reason"],
         json.dumps(validation), json.dumps(model) if model else None))
    bump_changes(conn)
    return {"validation": validation, "decisions": len(rows), "tracked": tracked,
            "dismissed": dismissed}


def fit_estimate(conn: sqlite3.Connection, posting_id: int, today: date | None = None,
                 model: dict | None = None) -> dict | None:
    """How well a posting matches what the user usually tracks. Never a success claim."""
    today = today or datetime.now().date()
    model = model or learning.latest_model(conn, "fit")
    if model is None:
        return None
    posting = conn.execute("SELECT * FROM postings WHERE id = ?", (posting_id,)).fetchone()
    item = {"posting_id": posting_id, "title": posting["title"], "provider": posting["provider"],
            "work_mode": posting["work_mode"], "contract_type": posting["contract_type"],
            "language": posting["language"], "posted_at": posting["posted_at"]}
    row = _decision_row(conn, item, insights.profile_titles(conn), today)
    p = stats.predict(model, row)
    factors = [{"feature": f, "effect": "up" if c > 0 else "down"}
               for f, c in stats.contributions(model, row)[:2] if abs(c) > 0.05]
    return {"label": _label(p, model["base_rate"]), "factors": factors,
            "meaning": "matches what you usually track; not a chance of success"}


# ── retraining the scoring rubric ─────────────────────────────────────────

JUDGED = ("title", "skills", "seniority", "conditions")
JUDGED_TOTAL = 90
WEIGHT_MIN, WEIGHT_MAX, WEIGHT_STEP = 5, 45, 5


def weights_candidate(conn: sqlite3.Connection) -> dict | None:
    """New component maximums proportional to how strongly each component predicts
    interviews in the validated model; None when nothing would change by 5+ points."""
    from . import scoring

    model = learning.latest_model(conn, "interview")
    if model is None:
        return None
    current = scoring.active_weights(conn)["weights"]
    strength = {}
    for name in JUDGED:
        high = model["coef"].get(f"{name}=high", 0.0)
        low = model["coef"].get(f"{name}=low", 0.0)
        strength[name] = max(high - low, 0.0) + 0.05
    total = sum(strength.values())
    proposed = {n: min(max(round(JUDGED_TOTAL * s / total), WEIGHT_MIN), WEIGHT_MAX)
                for n, s in strength.items()}
    drift = JUDGED_TOTAL - sum(proposed.values())
    order = sorted(proposed, key=lambda n: -strength[n])
    while drift:
        step = 1 if drift > 0 else -1
        movable = [n for n in order if WEIGHT_MIN <= proposed[n] + step <= WEIGHT_MAX]
        if not movable:
            break
        for name in movable:
            if drift == 0:
                break
            proposed[name] += step
            drift -= step
    if max(abs(proposed[n] - current.get(n, 0)) for n in JUDGED) < WEIGHT_STEP:
        return None
    return {"weights": {**proposed, "history": current.get("history", 10)},
            "current": {n: current.get(n) for n in (*JUDGED, "history")},
            "strength": {n: round(s - 0.05, 3) for n, s in strength.items()},
            "fitted_on": model.get("fitted_on")}
