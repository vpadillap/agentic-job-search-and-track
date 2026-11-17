"""What the user's own results show: outcomes, decisions, corrections, breakdowns.

Only applications the user applied to are outcomes (they have an applied
date; their facts at the time of applying come from
`applications.at_application`). An application is *resolved* when it reached
interview or beyond, was closed, or has waited longer than the no-response
threshold; unresolved
ones are left out of every rate, so recent applications do not look like
failures. Every rate carries its number of cases and an uncertainty range.

Each application also carries its full status name and the path of statuses
it went through, so the agent can see exactly at which step something worked
or failed. The only place that interprets statuses for the statistics is
`_progress`.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, datetime, timedelta

from . import applications, stats
from .errors import JobTrackerError

PERIODS = ("30", "90", "season", "all")
MIN_CASES = 5
NOT_STATED = "not_stated"
DIMENSIONS = ("score_band", "title", "channel", "provider", "resume_kind", "cover_letter",
              "salary_delta", "work_mode", "language", "posting_age")
STOPWORDS = set("""a al an and are as at be by con de del el en es for from has have in is it
la las los of on or para por que se the to un una we will with you your y o su sus nuestro
nuestra experience experiencia years años team equipo work trabajo role puesto""".split())
TERM = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9+#./-]{2,}")


def _today() -> date:
    return datetime.now().date()


def _day(value: str | None) -> date | None:
    return date.fromisoformat(value[:10]) if value else None


def terms(text: str | None) -> set[str]:
    """Distinct lowercase words of a text, without common words."""
    return {t.casefold().strip("./-") for t in TERM.findall(text or "")} - STOPWORDS


# ── statuses → outcome flags (the one place that interprets statuses) ─────

# Built-in statuses keep a fixed meaning through their key. A custom status is
# only its name and whether it ends an application: ending counts as closed with
# a response, otherwise it is pending.
INTERVIEW_KEYS = ("interview", "offer", "accepted")
OFFER_KEYS = ("offer", "accepted")
NO_RESPONSE_KEYS = ("ghosted", "withdrawn")


def _progress(status_key: str | None, ends: bool) -> dict:
    """What reaching a status means for the statistics."""
    return {
        "interview": status_key in INTERVIEW_KEYS,
        "offer": status_key in OFFER_KEYS,
        "response": status_key in INTERVIEW_KEYS
        or (ends and status_key not in NO_RESPONSE_KEYS),
        "closed": ends,
    }


def _event_status(conn: sqlite3.Connection, data: dict) -> tuple[str | None, bool]:
    """The key and "ends" of the status a `status_changed` event moved to: by status id
    in newer events, by key or stored name in older ones."""
    row = None
    if data.get("to_id") is not None:
        row = conn.execute("SELECT key, ends FROM statuses WHERE id = ?",
                           (data["to_id"],)).fetchone()
    if row is None and data.get("to") is not None:
        row = conn.execute(
            "SELECT key, ends FROM statuses WHERE key = ? OR (key IS NULL AND"
            " lower(name_en) = lower(?)) ORDER BY is_builtin DESC LIMIT 1",
            (data["to"], data["to"])).fetchone()
    if row is None:  # a custom status renamed since: fall back to what the event says
        return None, bool(data.get("to_ends")) or data.get("to_stage") in (
            "closed_positive", "closed_negative")
    return row["key"], bool(row["ends"])


# ── outcomes ──────────────────────────────────────────────────────────────

def outcomes(conn: sqlite3.Connection, today: date | None = None,
             language: str = "en") -> list[dict]:
    """One record per application the user applied to, with what happened. Statuses
    and the status path are given by their full names in `language`."""
    today = today or _today()
    ghost_days = applications.thresholds(conn)["ghost_after_days"]
    result = []
    for row in conn.execute(
        "SELECT a.id, a.job_id, a.applied_on, a.posting_id, s.key AS status_key, s.ends,"
        " s.name_en, s.name_es, p.title, p.company, p.language,"
        " p.work_mode, p.work_mode_source, p.provider, p.description"
        " FROM applications a JOIN statuses s ON s.id = a.status_id"
        " JOIN postings p ON p.id = a.posting_id WHERE a.applied_on IS NOT NULL"
        " ORDER BY a.applied_on, a.id"
    ):
        facts = applications.at_application(conn, row["job_id"])
        applied_on = _day(row["applied_on"])
        now = _progress(row["status_key"], bool(row["ends"]))
        reached = dict(now)
        reached["offer"] = reached["offer"] or facts["offered_salary"] is not None
        response_at: date | None = None
        path = []
        for event in conn.execute(
            "SELECT data, created_at FROM events WHERE entity_type = 'application'"
            " AND entity_id = ? AND kind = 'status_changed' ORDER BY created_at, id",
            (row["job_id"],),
        ):
            data = json.loads(event["data"])
            key, ends = _event_status(conn, data)
            step = _progress(key, ends)
            path.append({"status": applications.status_names(conn, data, language)[1],
                         "key": key, "on": event["created_at"][:10]})
            for flag in ("interview", "offer"):
                reached[flag] = reached[flag] or step[flag]
            if step["response"] and response_at is None:
                response_at = _day(event["created_at"])
        responded = response_at is not None or reached["interview"]
        waited = (today - applied_on).days if applied_on else 0
        resolved = reached["interview"] or now["closed"] or waited > ghost_days
        result.append({
            "job_id": row["job_id"], "posting_id": row["posting_id"],
            "applied_on": applied_on.isoformat() if applied_on else None,
            "status": row["name_es"] if language == "es" else row["name_en"],
            "status_key": row["status_key"],
            "status_path": path, "ended": bool(row["ends"]),
            "resolved": resolved, "interview": reached["interview"], "offer": reached["offer"],
            "responded": responded,
            "ghosted": resolved and not responded and row["status_key"] != "withdrawn",
            "days_to_response": (response_at - applied_on).days
            if response_at and applied_on else None,
            "at_application": facts, "offered_salary": facts["offered_salary"],
            "title": row["title"], "company": row["company"],
            "language": row["language"], "work_mode": row["work_mode"],
            "work_mode_source": row["work_mode_source"], "provider": row["provider"],
            "description": row["description"],
        })
    return result


def _in_period(conn: sqlite3.Connection, items: list[dict], period: str,
               today: date, key: str = "applied_on") -> list[dict]:
    if period not in PERIODS:
        raise JobTrackerError("invalid_period", f"period must be one of: {', '.join(PERIODS)}")
    if period == "all":
        return items
    if period == "season":
        season = conn.execute("SELECT started_at FROM seasons WHERE is_active = 1").fetchone()
        since = _day(season["started_at"]) if season else None
    else:
        since = today - timedelta(days=int(period))
    return [i for i in items if since is None or (i[key] and _day(i[key]) >= since)]


# ── decisions and corrections ─────────────────────────────────────────────

def decisions(conn: sqlite3.Connection) -> list[dict]:
    """Every posting the user decided on: tracked or dismissed (with the reason)."""
    result = []
    for row in conn.execute(
        "SELECT p.id, p.title, p.company, p.language, p.work_mode, p.contract_type,"
        " p.provider, p.location, p.posted_at, p.description, d.reason, d.note,"
        " d.created_at AS dismissed_at, a.job_id, a.created_at AS tracked_at"
        " FROM postings p LEFT JOIN dismissals d ON d.posting_id = p.id"
        " LEFT JOIN applications a ON a.posting_id = p.id"
        " WHERE d.id IS NOT NULL OR a.id IS NOT NULL ORDER BY p.id"
    ):
        tracked = row["job_id"] is not None
        result.append({
            "posting_id": row["id"], "decision": "tracked" if tracked else "dismissed",
            "reason": None if tracked else row["reason"], "note": None if tracked else row["note"],
            "on": (row["tracked_at"] if tracked else row["dismissed_at"] or "")[:10],
            "job_id": row["job_id"], "title": row["title"], "company": row["company"],
            "language": row["language"], "work_mode": row["work_mode"],
            "contract_type": row["contract_type"], "provider": row["provider"],
            "location": row["location"], "posted_at": row["posted_at"],
            "description": row["description"],
        })
    return result


def corrections(conn: sqlite3.Connection) -> list[dict]:
    """Agent readings the user corrected (today: work mode and its detail)."""
    result = []
    for row in conn.execute(
        "SELECT e.entity_id, e.data, e.created_at, p.provider, p.title, p.company"
        " FROM events e JOIN postings p ON CAST(p.id AS TEXT) = e.entity_id"
        " WHERE e.entity_type = 'posting' AND e.kind = 'work_mode' ORDER BY e.id"
    ):
        data = json.loads(row["data"])
        if data.get("source") != "user":
            continue
        before, after = data.get("from") or {}, data.get("to") or {}
        result.append({
            "posting_id": int(row["entity_id"]), "field": "work_mode",
            "provider": row["provider"], "title": row["title"], "company": row["company"],
            "agent_value": {"mode": before.get("mode"), "detail": before.get("detail")}
            if before.get("source", "agent") == "agent" else None,
            "from": {"mode": before.get("mode"), "detail": before.get("detail")},
            "to": {"mode": after.get("mode"), "detail": after.get("detail")},
            "on": row["created_at"][:10],
        })
    return result


# ── headline indicators ───────────────────────────────────────────────────

def _share(count: int, of: int) -> dict:
    return {"count": count, "of": of, "pct": round(count * 100 / of) if of else None}


def summary(conn: sqlite3.Connection, period: str = "season",
            today: date | None = None) -> dict:
    today = today or _today()
    items = _in_period(conn, outcomes(conn, today), period, today)
    resolved = [i for i in items if i["resolved"]]
    response_days = [i["days_to_response"] for i in resolved
                     if i["days_to_response"] is not None]
    made = decisions(conn)
    return {
        "period": period,
        "applied": len(items),
        "resolved": len(resolved),
        "unresolved": len(items) - len(resolved),
        "response": _share(sum(i["responded"] for i in resolved), len(resolved)),
        "interview": _share(sum(i["interview"] for i in resolved), len(resolved)),
        "offers": sum(i["offer"] for i in items),
        "ghosting": _share(sum(i["ghosted"] for i in resolved), len(resolved)),
        "median_days_to_response": stats.median(response_days),
        "response_days": sorted(response_days),
        "decisions": {"tracked": sum(d["decision"] == "tracked" for d in made),
                      "dismissed": sum(d["decision"] == "dismissed" for d in made)},
        "corrections": len(corrections(conn)),
        "offered_salary": _offered(items),
    }


def _offered(items: list[dict]) -> dict:
    """Offers with a recorded amount, and the median difference (%) between the
    offered salary and the asked and suggested ones, in the same currency."""
    with_amount = [i for i in items if i["offered_salary"]]

    def compare(key: str) -> dict:
        differences = []
        for item in with_amount:
            offered, other = item["offered_salary"], item["at_application"].get(key)
            if not other or not other.get("amount") or other["currency"] != offered["currency"]:
                continue
            if other.get("basis") and offered.get("basis") and other["basis"] != offered["basis"]:
                continue
            differences.append((offered["amount"] - other["amount"]) * 100 / other["amount"])
        middle = stats.median(differences)
        return {"median_pct": round(middle, 1) if middle is not None else None,
                "cases": len(differences)}

    return {"offers_with_amount": len(with_amount), "vs_asked": compare("asked_salary"),
            "vs_suggested": compare("suggested_salary")}


# ── breakdowns ────────────────────────────────────────────────────────────

def _score_band(score: int | None) -> str:
    if score is None:
        return "unscored"
    if score >= 85:
        return "85-100"
    if score >= 70:
        return "70-84"
    if score >= 55:
        return "55-69"
    return "0-54"


def _salary_delta(snap: dict) -> str:
    asked, suggested = snap.get("asked_salary"), snap.get("suggested_salary")
    if not asked or not suggested or asked.get("currency") != suggested.get("currency") \
            or not suggested.get("amount"):
        return "unknown"
    pct = (asked["amount"] - suggested["amount"]) * 100 / suggested["amount"]
    if pct <= 0:
        return "at_or_below"
    return "up_to_10" if pct <= 10 else "over_10"


def _posting_age(days: int | None) -> str:
    if days is None:
        return "unknown"
    return "0-3" if days <= 3 else "4-7" if days <= 7 else "8+"


def title_group(title: str, profile_titles: list[str]) -> str:
    """The profile's target title a posting title belongs to, or 'other'."""
    folded = (title or "").casefold()
    for target in sorted(profile_titles, key=len, reverse=True):
        if target.casefold() in folded:
            return target
    return "other"


def features_of(item: dict, profile_titles: list[str]) -> dict[str, str]:
    """The group of an application along every dimension. Work mode is the
    posting's current value, so the user's corrections count."""
    snap = item["at_application"]
    return {
        "score_band": _score_band(snap.get("score")),
        "title": title_group(item["title"], profile_titles),
        "channel": (snap.get("channel") or "unknown"),
        "provider": (item.get("provider") or snap.get("provider") or "unknown"),
        "resume_kind": snap.get("resume_kind") or "base",
        "cover_letter": "yes" if snap.get("cover_letter") else "no",
        "salary_delta": _salary_delta(snap),
        "work_mode": item.get("work_mode") or NOT_STATED,
        "language": item.get("language") or "unknown",
        "posting_age": _posting_age(snap.get("posting_age_days")),
    }


def profile_titles(conn: sqlite3.Connection) -> list[str]:
    from . import profile

    active = profile.get_active(conn)
    return [t["title"] for t in active["titles"]] if active else []


def breakdown(conn: sqlite3.Connection, dimension: str, period: str = "season",
              today: date | None = None) -> dict:
    if dimension not in DIMENSIONS:
        raise JobTrackerError("invalid_dimension",
                              f"dimension must be one of: {', '.join(DIMENSIONS)}")
    today = today or _today()
    resolved = [i for i in _in_period(conn, outcomes(conn, today), period, today)
                if i["resolved"]]
    titles = profile_titles(conn)
    overall = sum(i["interview"] for i in resolved) / len(resolved) if resolved else 0.0
    groups: dict[str, list[dict]] = {}
    for item in resolved:
        groups.setdefault(features_of(item, titles)[dimension], []).append(item)
    rows = []
    for label, members in groups.items():
        interviews = sum(m["interview"] for m in members)
        rate = stats.smoothed_rate(interviews, len(members), overall)
        rows.append({"group": label, "cases": len(members), "interviews": interviews,
                     **{k: round(v, 3) if v is not None else None for k, v in rate.items()},
                     "insufficient": len(members) < MIN_CASES})
    rows.sort(key=lambda r: (-r["cases"], r["group"]))
    return {"dimension": dimension, "period": period, "resolved": len(resolved),
            "overall_rate": round(overall, 3), "groups": rows}


def dismissal_patterns(conn: sqlite3.Connection) -> list[dict]:
    """The same reason given repeatedly for postings sharing a trait."""
    titles = profile_titles(conn)
    dismissed = [d for d in decisions(conn) if d["decision"] == "dismissed"]
    found = []
    by_reason: dict[str, list[dict]] = {}
    for item in dismissed:
        by_reason.setdefault(item["reason"] or "other", []).append(item)
    for reason, items in by_reason.items():
        for trait in ("work_mode", "provider", "language", "contract_type", "title"):
            counts: dict[str, int] = {}
            for item in items:
                value = title_group(item["title"], titles) if trait == "title" \
                    else (item.get(trait) or NOT_STATED if trait == "work_mode"
                          else item.get(trait) or "unknown")
                counts[value] = counts.get(value, 0) + 1
            for value, count in counts.items():
                if count >= MIN_CASES and value not in ("unknown", "other") \
                        and count >= 0.6 * len(items):
                    found.append({"reason": reason, "trait": trait, "value": value,
                                  "dismissals": count, "of_reason": len(items),
                                  "postings": [i["posting_id"] for i in items
                                               if (title_group(i["title"], titles)
                                                   if trait == "title"
                                                   else (i.get(trait) or (NOT_STATED if trait
                                                         == "work_mode" else "unknown")))
                                               == value]})
    return found


def correction_patterns(conn: sqlite3.Connection) -> list[dict]:
    """Agent readings corrected by the user, per site."""
    by_provider: dict[str, list[dict]] = {}
    for item in corrections(conn):
        if item["agent_value"] is not None:
            by_provider.setdefault(item["provider"] or "unknown", []).append(item)
    return [{"provider": provider, "field": "work_mode", "corrections": len(items),
             "examples": [{"posting_id": i["posting_id"], "agent": i["from"], "user": i["to"]}
                          for i in items[:10]]}
            for provider, items in by_provider.items() if len(items) >= MIN_CASES]
