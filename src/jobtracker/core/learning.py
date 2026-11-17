"""The learning loop: maturity levels, lessons and their effects, influence.

Lessons are rules with origin `learned`. The analysis proposes them with the
evidence attached; they change nothing until the user applies them, and every
applied lesson can be reverted. Structured effects are a fixed list the code
knows how to enforce; anything else is text the agent must follow.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime

from . import applications, insights, stats
from .db import bump_changes, now_iso
from .errors import JobTrackerError

# Maturity thresholds (design L2). Conservative on purpose; tunable later.
DESCRIPTIVE_RESOLVED = 15
PREDICTIVE_RESOLVED = 40
PREDICTIVE_INTERVIEWS = 8
PRESCRIPTIVE_GAP_DAYS = 14
RESHOW_AFTER_NEW_CASES = 5
SUGGEST_ANALYSIS_AFTER = 10
LEVELS = ("collecting", "descriptive", "predictive", "prescriptive")

EFFECTS = ("min_score_shown", "title_state", "ghost_after_days", "follow_up_after_days",
           "salary_cap_pct", "resume_emphasis", "weights")
TITLE_STATES = ("under_review", "excluded")
LEARNED_AREAS = ("search", "score", "resume", "cover_letter", "form", "salary", "statuses",
                 "providers", "general")


RESET_KEY = "learning.reset_at"


def reset_at(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (RESET_KEY,)).fetchone()
    return row["value"] if row else None


def reset(conn: sqlite3.Connection) -> dict:
    """Start learning over: models are withdrawn and only outcomes and decisions after
    today count toward estimates. Descriptive numbers still show all history."""
    now = now_iso()
    conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)"
                 " ON CONFLICT(key) DO UPDATE SET value = excluded.value", (RESET_KEY, now))
    conn.execute("UPDATE analyses SET passed = 0, reason = 'learning was reset' WHERE passed = 1")
    conn.execute("INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
                 " VALUES ('learning', 'all', 'reset', '{}', ?)", (now,))
    bump_changes(conn)
    return {"reset_at": now}


def since_reset(conn: sqlite3.Connection, items: list[dict], key: str) -> list[dict]:
    """Items dated after the last learning reset (all of them without a reset)."""
    since = reset_at(conn)
    if since is None:
        return items
    return [i for i in items if (i.get(key) or "") >= since[:10]]


# ── analyses and levels ───────────────────────────────────────────────────

def analyses(conn: sqlite3.Connection, limit: int = 10, kind: str = "interview") -> list[dict]:
    rows = conn.execute("SELECT * FROM analyses WHERE kind = ? ORDER BY id DESC LIMIT ?",
                        (kind, limit)).fetchall()
    return [{
        "id": r["id"], "created_at": r["created_at"], "resolved": r["resolved"],
        "interviews": r["interviews"], "passed": bool(r["passed"]), "reason": r["reason"],
        "validation": json.loads(r["validation"]) if r["validation"] else None,
    } for r in rows]


def latest_model(conn: sqlite3.Connection, kind: str = "interview") -> dict | None:
    row = conn.execute("SELECT model FROM analyses WHERE id = (SELECT MAX(id) FROM analyses"
                       " WHERE kind = ?) AND passed = 1", (kind,)).fetchone()
    return json.loads(row["model"]) if row and row["model"] else None


def level(conn: sqlite3.Connection, today: date | None = None) -> dict:
    """The current maturity level, what it enables, and what the next one needs."""
    summary = insights.summary(conn, "all", today)
    resolved = summary["resolved"]
    counted = [i for i in since_reset(conn, insights.outcomes(conn, today), "applied_on")
               if i["resolved"]]
    model_resolved = len(counted)
    interviews = sum(i["interview"] for i in counted)
    recent = analyses(conn, 50)
    passed_last = bool(recent) and recent[0]["passed"]
    # Prescriptive: the unbroken run of passing analyses up to the latest spans 14+ days,
    # so re-checking on the same day never demotes, and any failure starts over.
    streak = []
    for analysis in recent:
        if not analysis["passed"]:
            break
        streak.append(analysis)
    passed_twice = len(streak) >= 2 and (
        datetime.fromisoformat(streak[0]["created_at"].replace("Z", "+00:00"))
        - datetime.fromisoformat(streak[-1]["created_at"].replace("Z", "+00:00"))
    ).days >= PRESCRIPTIVE_GAP_DAYS
    enough = model_resolved >= PREDICTIVE_RESOLVED and interviews >= PREDICTIVE_INTERVIEWS
    if enough and passed_twice:
        number = 3
    elif enough and passed_last:
        number = 2
    elif resolved >= DESCRIPTIVE_RESOLVED:
        number = 1
    else:
        number = 0

    if number == 0:
        needs = {"resolved": DESCRIPTIVE_RESOLVED - resolved}
    elif number == 1:
        needs = {"resolved": max(0, PREDICTIVE_RESOLVED - model_resolved),
                 "interviews": max(0, PREDICTIVE_INTERVIEWS - interviews),
                 "validated_analysis": not passed_last}
    elif number == 2:
        needs = {"validated_analyses": 1, "days_between": PRESCRIPTIVE_GAP_DAYS}
    else:
        needs = {}
    reason = recent[0]["reason"] if recent and not recent[0]["passed"] else None
    since_last = None
    if recent:
        since_last = sum(1 for i in insights.outcomes(conn, today) if i["resolved"]) \
            - recent[0]["resolved"]
    return {
        "level": number, "name": LEVELS[number], "resolved": resolved,
        "interviews": interviews, "needs": needs, "model_reason": reason,
        "reset_at": reset_at(conn),
        "last_analysis": recent[0]["created_at"] if recent else None,
        "resolved_since_analysis": since_last,
        "suggest_analysis": since_last is None and resolved >= DESCRIPTIVE_RESOLVED
        or (since_last or 0) >= SUGGEST_ANALYSIS_AFTER,
    }


def estimates_for(conn: sqlite3.Connection, posting_ids: list[int],
                  today: date | None = None) -> dict[int, dict]:
    """Interview estimate and fit label per posting, where each is allowed."""
    from . import predict

    model = predict.latest_active_model(conn, today)
    fit_model = latest_model(conn, "fit")
    result = {}
    for posting_id in posting_ids:
        result[posting_id] = {
            "interview": predict.estimate(conn, posting_id, today, model=model) if model else None,
            "fit": predict.fit_estimate(conn, posting_id, today, model=fit_model)
            if fit_model else None}
    return result


def board(conn: sqlite3.Connection, paths, period: str = "season",
          today: date | None = None) -> dict:
    """Everything the Learning board shows, gated by level."""
    from . import predict, recommend, refresh
    from .rules import list_rules

    current = level(conn, today)
    summary = insights.summary(conn, period, today)
    summary.pop("response_days")
    shown = ("score_band", "resume_kind", "channel", "salary_delta", "language", "work_mode")
    breakdowns = {d: insights.breakdown(conn, d, period, today) for d in shown} \
        if current["level"] >= 1 else {}
    lessons = [r for r in list_rules(conn, None) if r["origin"] == "learned"
               and r["status"] in ("proposed", "active")]
    fit_last = analyses(conn, 1, "fit")
    return {
        "level": current, "summary": summary, "breakdowns": breakdowns, "lessons": lessons,
        "track_record": predict.track_record(conn) if current["level"] >= 2 else None,
        "recommendations": recommend.all_recommendations(conn, paths, today),
        "experiments": recommend.experiments(conn, today) if current["level"] >= 3 else [],
        "fit": {"available": latest_model(conn, "fit") is not None,
                "decisions": summary["decisions"],
                "needs": predict.FIT_DECISIONS, "each": predict.FIT_EACH,
                "reason": fit_last[0]["reason"] if fit_last and not fit_last[0]["passed"]
                else None},
        "last_refresh": refresh.last_refresh(conn),
        "ghost_after_days": applications.thresholds(conn)["ghost_after_days"],
        "commands": {"review": "analyze-results"},
    }


# ── effects ───────────────────────────────────────────────────────────────

def _check_effect(effect: object, where: str) -> dict | None:
    if effect is None:
        return None
    if not isinstance(effect, dict) or not effect:
        raise JobTrackerError("invalid_rule", f"{where}: 'effect' must be an object")
    unknown = sorted(set(effect) - set(EFFECTS))
    if unknown:
        raise JobTrackerError(
            "invalid_rule",
            f"{where}: '{unknown[0]}' is not an effect the system can apply; effects are "
            f"{', '.join(EFFECTS)}. Describe anything else in the text.")
    for key, value in effect.items():
        if key in ("min_score_shown",) and not (isinstance(value, int) and 0 <= value <= 100):
            raise JobTrackerError("invalid_rule", f"{where}: {key} must be 0 to 100")
        if key in ("ghost_after_days", "follow_up_after_days") and not (
                isinstance(value, int) and 1 <= value <= 365):
            raise JobTrackerError("invalid_rule", f"{where}: {key} must be 1 to 365 days")
        if key == "salary_cap_pct" and not (isinstance(value, (int, float))
                                            and 0 <= value <= 50):
            raise JobTrackerError("invalid_rule", f"{where}: salary_cap_pct must be 0 to 50")
        if key == "resume_emphasis" and not (isinstance(value, list) and value and all(
                isinstance(v, str) and v.strip() for v in value)):
            raise JobTrackerError("invalid_rule", f"{where}: resume_emphasis is a list of terms")
        if key == "title_state":
            if not (isinstance(value, dict) and isinstance(value.get("title"), str)
                    and value.get("state") in TITLE_STATES):
                raise JobTrackerError(
                    "invalid_rule",
                    f"{where}: title_state is {{\"title\": ..., \"state\": under_review|excluded}}")
        if key == "weights" and not isinstance(value, dict):
            raise JobTrackerError("invalid_rule", f"{where}: weights is {{component: points}}")
    return effect


def effects(conn: sqlite3.Connection) -> dict:
    """What the active rules change, the latest rule winning per setting. Nothing here
    affects searching; title states are applied to the profile when a lesson is applied."""
    result: dict = {"resume_emphasis": []}
    for row in conn.execute(
        "SELECT id, effect FROM rules WHERE status = 'active' AND effect IS NOT NULL"
        " ORDER BY COALESCE(applied_at, updated_at), id"
    ):
        effect = json.loads(row["effect"])
        for key, value in effect.items():
            if key == "resume_emphasis":
                for term in value:
                    if term not in result["resume_emphasis"]:
                        result["resume_emphasis"].append(term)
            elif key not in ("weights", "title_state"):
                result[key] = value
    return result


# ── lessons: propose, apply, ignore, revert ───────────────────────────────

def _rule(conn: sqlite3.Connection, rule_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
    if row is None:
        raise JobTrackerError("not_found", f"There is no rule {rule_id}")
    return row


def _event(conn: sqlite3.Connection, rule_id: int, kind: str, data: dict | None = None) -> None:
    conn.execute("INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
                 " VALUES ('rule', ?, ?, ?, ?)",
                 (str(rule_id), kind, json.dumps(data or {}, ensure_ascii=False), now_iso()))


def propose(conn: sqlite3.Connection, proposals: object) -> dict:
    """Store lessons as proposed. A lesson needs evidence from at least five cases and
    is not proposed again while its earlier proposal was ignored or reverted on the
    same evidence."""
    from .rules import list_rules

    if not isinstance(proposals, list) or not proposals:
        raise JobTrackerError("invalid_rule", "expected a non-empty list of lessons")
    checked = []
    for index, item in enumerate(proposals):
        where = f"lesson {index}"
        if not isinstance(item, dict):
            raise JobTrackerError("invalid_rule", f"{where}: must be an object", index=index)
        text, evidence = item.get("text"), item.get("evidence")
        key, cases = item.get("candidate_key"), item.get("cases")
        if not isinstance(text, str) or not text.strip():
            raise JobTrackerError("invalid_rule", f"{where}: 'text' is required", index=index)
        if not isinstance(evidence, str) or not evidence.strip():
            raise JobTrackerError("invalid_rule", f"{where}: 'evidence' with counts is required",
                                  index=index)
        if not isinstance(key, str) or not key:
            raise JobTrackerError("invalid_rule", f"{where}: 'candidate_key' is required",
                                  index=index)
        if isinstance(cases, bool) or not isinstance(cases, int) or cases < insights.MIN_CASES:
            raise JobTrackerError(
                "too_few_cases",
                f"{where}: a lesson needs at least {insights.MIN_CASES} cases", index=index)
        area = item.get("area", "general")
        if area not in LEARNED_AREAS:
            raise JobTrackerError("invalid_rule", f"{where}: unknown area '{area}'", index=index)
        checked.append({"text": text.strip(), "evidence": evidence.strip(), "key": key,
                        "cases": cases, "area": area,
                        "effect": _check_effect(item.get("effect"), where)})
    now = now_iso()
    proposed, skipped = [], []
    for item in checked:
        earlier = conn.execute(
            "SELECT status, candidate_cases FROM rules WHERE candidate_key = ?"
            " ORDER BY id DESC LIMIT 1", (item["key"],)).fetchone()
        if earlier is not None and earlier["status"] in ("proposed", "active"):
            skipped.append({"candidate_key": item["key"], "reason": f"already {earlier['status']}"})
            continue
        if earlier is not None and item["cases"] < (earlier["candidate_cases"] or 0) \
                + RESHOW_AFTER_NEW_CASES:
            skipped.append({"candidate_key": item["key"],
                            "reason": f"{earlier['status']} by the user on the same evidence"})
            continue
        cursor = conn.execute(
            "INSERT INTO rules (origin, status, area, text, evidence, effect, created_at,"
            " updated_at, candidate_key, candidate_cases)"
            " VALUES ('learned', 'proposed', ?, ?, ?, ?, ?, ?, ?, ?)",
            (item["area"], item["text"], item["evidence"],
             json.dumps(item["effect"]) if item["effect"] else None, now, now, item["key"],
             item["cases"]))
        _event(conn, cursor.lastrowid, "proposed", {"candidate_key": item["key"]})
        proposed.append(cursor.lastrowid)
    bump_changes(conn)
    rules = {r["id"]: r for r in list_rules(conn, None)}
    return {"proposed": [rules[i] for i in proposed], "skipped": skipped}


def _learned(conn: sqlite3.Connection, rule_id: int, status: str) -> sqlite3.Row:
    row = _rule(conn, rule_id)
    if row["origin"] != "learned":
        raise JobTrackerError("not_a_lesson", "Only learned lessons are applied, ignored, or "
                                              "reverted; edit or retire your own rules instead")
    if row["status"] != status:
        raise JobTrackerError("invalid_state",
                              f"Rule {rule_id} is {row['status']}, not {status}")
    return row


def _title_state(conn: sqlite3.Connection, title: str) -> str | None:
    from . import profile

    active = profile.get_active(conn)
    for item in active["titles"] if active else []:
        if item["title"].casefold() == title.casefold():
            return item["state"]
    return None


def _set_title_state(conn: sqlite3.Connection, title: str, state: str) -> None:
    from . import profile

    if _title_state(conn, title) is not None:
        profile.set_title_state(conn, title, state)


def apply(conn: sqlite3.Connection, rule_id: int) -> dict:
    """The user applies a proposed lesson: it takes effect from the next run."""
    from . import scoring
    from .rules import list_rules

    row = _learned(conn, rule_id, "proposed")
    effect = json.loads(row["effect"]) if row["effect"] else {}
    data: dict = {}
    if "weights" in effect:
        before = scoring.active_weights(conn)
        scoring.set_weights(conn, {**before["weights"], **effect["weights"]},
                            note=f"lesson {rule_id}")
        data["previous_weights"] = before["weights"]
    title = effect.get("title_state")
    if title:
        data["previous_title_state"] = _title_state(conn, title["title"])
        _set_title_state(conn, title["title"], title["state"])
    now = now_iso()
    conn.execute("UPDATE rules SET status = 'active', applied_at = ?, updated_at = ?"
                 " WHERE id = ?", (now, now, rule_id))
    _event(conn, rule_id, "applied", data)
    bump_changes(conn)
    return next(r for r in list_rules(conn, None) if r["id"] == rule_id)


def ignore(conn: sqlite3.Connection, rule_id: int) -> dict:
    from .rules import list_rules

    _learned(conn, rule_id, "proposed")
    conn.execute("UPDATE rules SET status = 'ignored', updated_at = ? WHERE id = ?",
                 (now_iso(), rule_id))
    _event(conn, rule_id, "ignored")
    bump_changes(conn)
    return next(r for r in list_rules(conn, None) if r["id"] == rule_id)


def revert(conn: sqlite3.Connection, rule_id: int) -> dict:
    """Stop an applied lesson from the next run. Past records are unchanged."""
    from . import scoring
    from .rules import list_rules

    row = _learned(conn, rule_id, "active")
    effect = json.loads(row["effect"]) if row["effect"] else {}
    if "weights" in effect:
        applied = conn.execute(
            "SELECT data FROM events WHERE entity_type = 'rule' AND entity_id = ?"
            " AND kind = 'applied' ORDER BY id DESC LIMIT 1", (str(rule_id),)).fetchone()
        previous = json.loads(applied["data"]).get("previous_weights") if applied else None
        if previous:
            scoring.set_weights(conn, previous, note=f"lesson {rule_id} reverted")
    title = effect.get("title_state")
    if title:
        applied = conn.execute(
            "SELECT data FROM events WHERE entity_type = 'rule' AND entity_id = ?"
            " AND kind = 'applied' ORDER BY id DESC LIMIT 1", (str(rule_id),)).fetchone()
        previous = json.loads(applied["data"]).get("previous_title_state") if applied else None
        _set_title_state(conn, title["title"], previous or "included")
    conn.execute("UPDATE rules SET status = 'reverted', updated_at = ? WHERE id = ?",
                 (now_iso(), rule_id))
    _event(conn, rule_id, "reverted")
    bump_changes(conn)
    return next(r for r in list_rules(conn, None) if r["id"] == rule_id)


# ── influence ─────────────────────────────────────────────────────────────

def record_influence(conn: sqlite3.Connection, entity_type: str, entity_id: object, *,
                     areas: tuple[str, ...] = (), rule_ids: list[int] | None = None) -> None:
    """Record which rules were in force when something was produced."""
    ids = set(rule_ids or [])
    if areas:
        marks = ",".join("?" * len(areas))
        ids |= {r["id"] for r in conn.execute(
            f"SELECT id FROM rules WHERE status = 'active' AND origin != 'system'"
            f" AND area IN ({marks})", areas)}
    now = now_iso()
    for rule_id in sorted(ids):
        conn.execute("INSERT INTO rule_influence (rule_id, entity_type, entity_id, created_at)"
                     " VALUES (?, ?, ?, ?)", (rule_id, entity_type, str(entity_id), now))


def rule_effect(conn: sqlite3.Connection, rule_id: int, today: date | None = None) -> dict:
    """Outcomes of applications produced with this rule in force versus without it."""
    _rule(conn, rule_id)
    touched_postings = {int(r["entity_id"]) for r in conn.execute(
        "SELECT entity_id FROM rule_influence WHERE rule_id = ? AND entity_type IN"
        " ('score', 'salary', 'search_result')", (rule_id,))}
    touched_jobs = {r["entity_id"] for r in conn.execute(
        "SELECT entity_id FROM rule_influence WHERE rule_id = ? AND entity_type IN"
        " ('document', 'answers', 'application')", (rule_id,))}
    resolved = [i for i in insights.outcomes(conn, today) if i["resolved"]]
    overall = sum(i["interview"] for i in resolved) / len(resolved) if resolved else 0.0
    groups = {"with": [], "without": []}
    for item in resolved:
        key = "with" if item["posting_id"] in touched_postings \
            or item["job_id"] in touched_jobs else "without"
        groups[key].append(item)
    result = {}
    for key, members in groups.items():
        interviews = sum(m["interview"] for m in members)
        rate = stats.smoothed_rate(interviews, len(members), overall) if members else None
        result[key] = {"cases": len(members), "interviews": interviews,
                       "rate": round(rate["rate"], 3) if rate else None,
                       "insufficient": len(members) < insights.MIN_CASES}
    return {"rule_id": rule_id, **result}


# ── lesson candidates ─────────────────────────────────────────────────────

def candidates(conn: sqlite3.Connection, period: str = "all",
               today: date | None = None) -> dict:
    """Patterns in the user's results that may deserve a lesson. Mechanical: the
    agent reviews them for confounding and words the ones worth proposing."""
    current = level(conn, today)
    found: list[dict] = _decision_candidates(conn)
    if current["level"] < 1:
        return {"level": current, "candidates": _mark_existing(conn, found),
                "note": f"Fewer than {DESCRIPTIVE_RESOLVED} resolved applications: no "
                        "conclusions from outcomes yet; dismissals and corrections still count."}
    by_dim = {d: insights.breakdown(conn, d, period, today) for d in insights.DIMENSIONS}
    overall = by_dim["title"]["overall_rate"]

    def evidence(group: dict) -> dict:
        return {"cases": group["cases"], "interviews": group["interviews"],
                "rate": group["rate"], "low": group["low"], "high": group["high"],
                "overall": overall}

    for dim in ("title", "provider", "channel", "resume_kind", "cover_letter", "work_mode",
                "posting_age"):
        for group in by_dim[dim]["groups"]:
            if group["insufficient"] or group["group"] in ("unknown", "other"):
                continue
            direction = "worse" if group["high"] < overall else \
                "better" if group["low"] > overall else None
            if direction is None:
                continue
            item = {"key": f"{dim}:{group['group']}:{direction}", "dimension": dim,
                    "group": group["group"], "direction": direction,
                    "cases": group["cases"], "evidence": evidence(group), "effect": None,
                    "area": {"title": "general", "provider": "providers",
                             "resume_kind": "resume", "cover_letter": "cover_letter"}.get(
                                 dim, "general")}
            if dim == "title" and direction == "worse":
                item["effect"] = {"title_state": {"title": group["group"],
                                                  "state": "under_review"}}
            found.append(item)

    # Score bands: if every sufficiently known band below some score has no
    # interviews while higher bands do, propose hiding postings below it.
    bands = {g["group"]: g for g in by_dim["score_band"]["groups"]}
    order = [("0-54", 0), ("55-69", 55), ("70-84", 70), ("85-100", 85)]
    floor = None
    for name, lower in order:
        group = bands.get(name)
        if group is None:
            continue
        if group["interviews"] == 0 and not group["insufficient"]:
            floor = None
            continue
        if group["interviews"] > 0:
            floor = lower
            break
    if floor:
        dead = [bands[n] for n, lo in order if lo < floor and n in bands]
        cases = sum(g["cases"] for g in dead)
        if dead and all(g["interviews"] == 0 for g in dead) and cases >= insights.MIN_CASES:
            found.append({"key": f"min_score:{floor}", "dimension": "score_band",
                          "group": f"below {floor}", "direction": "worse", "cases": cases,
                          "evidence": {"cases": cases, "interviews": 0, "overall": overall},
                          "effect": {"min_score_shown": floor}, "area": "search"})

    over = next((g for g in by_dim["salary_delta"]["groups"] if g["group"] == "over_10"), None)
    if over and not over["insufficient"] and over["high"] < overall:
        found.append({"key": "salary_cap:10", "dimension": "salary_delta", "group": "over_10",
                      "direction": "worse", "cases": over["cases"], "evidence": evidence(over),
                      "effect": {"salary_cap_pct": 10}, "area": "salary"})

    summary = insights.summary(conn, period, today)
    days = summary["response_days"]
    if len(days) >= insights.MIN_CASES:
        from . import applications

        limits = applications.thresholds(conn)
        ghost = max(days) + 2
        if abs(ghost - limits["ghost_after_days"]) >= 3:
            found.append({"key": f"ghost_days:{ghost}", "dimension": "response_time",
                          "group": f"responses within {max(days)} days", "direction": None,
                          "cases": len(days),
                          "evidence": {"responses": len(days), "latest_day": max(days),
                                       "median_day": stats.median(days)},
                          "effect": {"ghost_after_days": ghost}, "area": "statuses"})
    if current["level"] >= 2:
        from . import predict

        weights = predict.weights_candidate(conn)
        if weights:
            found.append({"key": "weights:" + json.dumps(weights["weights"], sort_keys=True),
                          "dimension": "score_components", "group": "weights",
                          "direction": None, "cases": weights["fitted_on"] or 0,
                          "evidence": {"strength": weights["strength"],
                                       "current": weights["current"],
                                       "resolved": weights["fitted_on"]},
                          "effect": {"weights": {k: v for k, v in weights["weights"].items()
                                                 if k != "history"}},
                          "area": "score"})
    return {"level": current, "candidates": _mark_existing(conn, found)}


def _decision_candidates(conn: sqlite3.Connection) -> list[dict]:
    """Lessons from what the user does with postings, available from the start."""
    found = []
    for item in insights.dismissal_patterns(conn):
        found.append({
            "key": f"dismissed:{item['reason']}:{item['trait']}:{item['value']}",
            "dimension": "dismissals", "group": f"{item['trait']}={item['value']}",
            "direction": "worse", "cases": item["dismissals"],
            "evidence": {"reason": item["reason"], "dismissals": item["dismissals"],
                         "of_reason": item["of_reason"], "postings": item["postings"]},
            "effect": None, "area": "search"})
    for item in insights.correction_patterns(conn):
        found.append({
            "key": f"corrected:{item['field']}:{item['provider']}",
            "dimension": "corrections", "group": item["provider"], "direction": None,
            "cases": item["corrections"],
            "evidence": {"field": item["field"], "corrections": item["corrections"],
                         "examples": item["examples"]},
            "effect": None, "area": "search"})
    return found


def _mark_existing(conn: sqlite3.Connection, found: list[dict]) -> list[dict]:
    """Say which candidates already have a lesson, so they are not proposed twice."""
    for item in found:
        row = conn.execute("SELECT id, status, candidate_cases FROM rules"
                           " WHERE candidate_key = ? ORDER BY id DESC LIMIT 1",
                           (item["key"],)).fetchone()
        item["existing"] = {"rule_id": row["id"], "status": row["status"],
                            "cases": row["candidate_cases"]} if row else None
    return found
