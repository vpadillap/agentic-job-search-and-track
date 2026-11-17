"""Evidence-gated salary suggestions.

A suggestion exists only with two or more comparable, linked pieces of
evidence: same country, same seniority level, same currency and basis, and no
older than 18 months. Nothing is converted across currencies; yearly figures
become monthly by dividing by 12. Otherwise the posting has "no reliable data".
"""
from __future__ import annotations

import json
import re
import sqlite3
import statistics
from datetime import date, datetime, timedelta

from . import normalize
from .db import bump_changes, now_iso
from .errors import JobTrackerError

MIN_SOURCES = 2
MAX_EVIDENCE_AGE_DAYS = 548          # 18 months
CACHE_DAYS = 60
PERIODS = ("month", "year")
BASES = ("gross", "net")
CONTEXT_FIELDS = ("work_mode", "industry", "company_size")


def _fail(message: str, **details: object):
    raise JobTrackerError("invalid_salary", message, **details)


def _today() -> date:
    return datetime.now().date()


def _posting(conn: sqlite3.Connection, posting_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM postings WHERE id = ?", (posting_id,)).fetchone()
    if row is None:
        raise JobTrackerError("not_found", f"There is no posting {posting_id}")
    return row


def research_key(company: str, role: str, location: str | None) -> tuple[str, str, str]:
    return (normalize.company_key(company), normalize.title_key(role),
            normalize.location_key(location))


def _posting_key(row: sqlite3.Row) -> tuple[str, str, str]:
    return research_key(row["company"], row["title"], row["location"])


# ── evidence ──────────────────────────────────────────────────────────────

def _positive(value: object, field: str, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        _fail(f"{where}: '{field}' must be a positive whole number")
    return value  # type: ignore[return-value]


def _validate_evidence(conn: sqlite3.Connection, record: object, index: int, today: date) -> dict:
    where = f"evidence {index + 1}"
    if not isinstance(record, dict):
        _fail(f"{where}: must be an object")
    source = record.get("source")  # type: ignore[union-attr]
    if not isinstance(source, str) or not source.strip():
        _fail(f"{where}: 'source' is required")
    url = normalize.safe_url(record.get("url"), f"{where}: url")  # type: ignore[union-attr]
    if "amount" in record:  # type: ignore[operator]
        low = high = _positive(record["amount"], "amount", where)  # type: ignore[index]
    else:
        low = _positive(record.get("amount_min"), "amount_min", where)  # type: ignore[union-attr]
        high = _positive(record.get("amount_max"), "amount_max", where)  # type: ignore[union-attr]
    if low > high:
        _fail(f"{where}: 'amount_min' is larger than 'amount_max'")
    currency = record.get("currency")  # type: ignore[union-attr]
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        _fail(f"{where}: 'currency' must be a 3-letter ISO code such as PEN")
    basis = record.get("basis")  # type: ignore[union-attr]
    if basis not in BASES:
        _fail(f"{where}: 'basis' must be gross or net")
    period = record.get("period", "month")  # type: ignore[union-attr]
    if period not in PERIODS:
        _fail(f"{where}: 'period' must be month or year; other periods are not converted")
    if period == "year":
        low, high = round(low / 12), round(high / 12)
    observed = normalize.parse_date(str(record.get("observed_on") or ""))  # type: ignore[union-attr]
    if observed > today:
        _fail(f"{where}: 'observed_on' is in the future")
    country = record.get("country")  # type: ignore[union-attr]
    if not isinstance(country, str) or not re.fullmatch(r"[A-Za-z]{2}", country):
        _fail(f"{where}: 'country' must be a 2-letter ISO code such as PE")
    level = record.get("level")  # type: ignore[union-attr]
    if not isinstance(level, str) or not level.strip():
        _fail(f"{where}: 'level' (seniority) is required")
    sample = record.get("sample_size")  # type: ignore[union-attr]
    if sample is not None:
        _positive(sample, "sample_size", where)
    context = {}
    for field in CONTEXT_FIELDS:
        value = record.get(field)  # type: ignore[union-attr]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            _fail(f"{where}: '{field}' must be text or omitted")
        context[field] = value.strip() if isinstance(value, str) else None
    posting_id = record.get("posting_id")  # type: ignore[union-attr]
    if posting_id is not None:
        key = _posting_key(_posting(conn, posting_id))
    else:
        research = record.get("research")  # type: ignore[union-attr]
        if not isinstance(research, dict) or not isinstance(research.get("company"), str) \
                or not isinstance(research.get("role"), str):
            _fail(f"{where}: give 'posting_id', or 'research' with company, role, and location")
        key = research_key(research["company"], research["role"], research.get("location"))
    summary = record.get("summary")  # type: ignore[union-attr]
    return {
        "source": source.strip(), "url": url,  # type: ignore[union-attr]
        "summary": summary.strip() if isinstance(summary, str) and summary.strip() else None,
        "amount_min": low, "amount_max": high, "currency": currency, "basis": basis,
        "original_period": period, "sample_size": sample, "observed_on": observed.isoformat(),
        "country": country.upper(), "level": level.strip(), **context,  # type: ignore[union-attr]
        "from_posting": bool(record.get("from_posting", False)),  # type: ignore[union-attr]
        "key": key, "posting_id": posting_id,
    }


def add_evidence(conn: sqlite3.Connection, records: object, today: date | None = None) -> list:
    """Store salary reports. Every record is validated before anything is stored."""
    today = today or _today()
    if not isinstance(records, list) or not records:
        _fail("expected a non-empty list of evidence")
    validated = [_validate_evidence(conn, r, i, today) for i, r in enumerate(records)]  # type: ignore[arg-type]
    now = now_iso()
    ids = []
    for item in validated:
        cursor = conn.execute(
            "INSERT INTO salary_evidence (source, url, summary, amount_min, amount_max, currency,"
            " basis, original_period, sample_size, observed_on, country, level, work_mode,"
            " industry, company_size, from_posting, research_company, research_role,"
            " research_location, posting_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (item["source"], item["url"], item["summary"], item["amount_min"], item["amount_max"],
             item["currency"], item["basis"], item["original_period"], item["sample_size"],
             item["observed_on"], item["country"], item["level"], item["work_mode"],
             item["industry"], item["company_size"], int(item["from_posting"]), *item["key"],
             item["posting_id"], now),
        )
        ids.append(cursor.lastrowid)
    bump_changes(conn)
    return [evidence(conn, i) for i in ids]


def _evidence_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "source": row["source"], "url": row["url"], "summary": row["summary"],
        "amount_min": row["amount_min"], "amount_max": row["amount_max"],
        "currency": row["currency"], "basis": row["basis"], "period": "month",
        "original_period": row["original_period"], "sample_size": row["sample_size"],
        "observed_on": row["observed_on"], "country": row["country"], "level": row["level"],
        "work_mode": row["work_mode"], "industry": row["industry"],
        "company_size": row["company_size"], "from_posting": bool(row["from_posting"]),
        "created_at": row["created_at"],
    }


def evidence(conn: sqlite3.Connection, evidence_id: int) -> dict:
    row = conn.execute("SELECT * FROM salary_evidence WHERE id = ?", (evidence_id,)).fetchone()
    if row is None:
        raise JobTrackerError("not_found", f"There is no salary evidence {evidence_id}")
    return _evidence_dict(row)


# ── suggestions ───────────────────────────────────────────────────────────

def comparability(item: dict, criteria: dict, today: date) -> list[str]:
    """Why a piece of evidence does not count (empty when it is comparable)."""
    problems = []
    if item["country"] != criteria["country"]:
        problems.append(f"different country ({item['country']})")
    if item["level"].casefold() != criteria["level"].casefold():
        problems.append(f"different level ({item['level']})")
    if item["currency"] != criteria["currency"]:
        problems.append(f"different currency ({item['currency']})")
    if item["basis"] != criteria["basis"]:
        problems.append(f"{item['basis']} instead of {criteria['basis']}")
    if date.fromisoformat(item["observed_on"]) < today - timedelta(days=MAX_EVIDENCE_AGE_DAYS):
        problems.append(f"older than 18 months ({item['observed_on']})")
    return problems


def _confidence(items: list[dict], criteria: dict) -> str:
    """More sources and closer matches on work mode, industry, and size mean more confidence."""
    checks = [
        item[field].casefold() == criteria[field].casefold()
        for item in items for field in CONTEXT_FIELDS
        if criteria.get(field) and item.get(field)
    ]
    closeness = sum(checks) / len(checks) if checks else 0.0
    if len(items) >= 3 and closeness >= 2 / 3:
        return "high"
    if len(items) >= 3 or closeness >= 2 / 3:
        return "medium"
    return "low"


def _criteria(row: sqlite3.Row, given: object) -> dict:
    if given is not None and not isinstance(given, dict):
        _fail("'criteria' must be an object")
    given = given or {}
    country = (given.get("country") or row["country"] or "")  # type: ignore[union-attr]
    level = given.get("level") or row["seniority"]  # type: ignore[union-attr]
    if not country:
        _fail("the posting has no country; give criteria.country")
    if not level:
        _fail("the posting has no seniority level; give criteria.level")
    if row["country"] and country.upper() != row["country"]:
        _fail(f"criteria.country must be the posting's country ({row['country']})")
    if row["seniority"] and level.casefold() != row["seniority"].casefold():
        _fail(f"criteria.level must be the posting's level ({row['seniority']})")
    currency = given.get("currency")  # type: ignore[union-attr]
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        _fail("criteria.currency must be a 3-letter ISO code such as PEN")
    basis = given.get("basis", "gross")  # type: ignore[union-attr]
    if basis not in BASES:
        _fail("criteria.basis must be gross or net")
    result = {"country": country.upper(), "level": level, "currency": currency, "basis": basis}
    for field in CONTEXT_FIELDS:
        value = given.get(field)  # type: ignore[union-attr]
        if value is None and field == "work_mode":
            value = row["work_mode"]
        result[field] = value
    return result


def set_suggestion(
    conn: sqlite3.Connection, posting_id: int, submission: object, today: date | None = None,
) -> dict:
    """Store a suggestion from stored evidence, or reject it when fewer than two count."""
    today = today or _today()
    row = _posting(conn, posting_id)
    if not isinstance(submission, dict):
        _fail("expected an object with 'evidence_ids' and 'criteria'")
    ids = submission.get("evidence_ids")  # type: ignore[union-attr]
    if not isinstance(ids, list) or any(isinstance(i, bool) or not isinstance(i, int)
                                        for i in ids):
        _fail("'evidence_ids' must be a list of evidence ids")
    criteria = _criteria(row, submission.get("criteria"))  # type: ignore[union-attr]
    items = [evidence(conn, i) for i in dict.fromkeys(ids)]  # type: ignore[union-attr]
    counted, excluded = [], []
    for item in items:
        problems = comparability(item, criteria, today)
        if problems:
            excluded.append({"evidence_id": item["id"], "source": item["source"],
                             "problems": problems})
        else:
            counted.append(item)
    if len(counted) < MIN_SOURCES:
        raise JobTrackerError(
            "insufficient_evidence",
            f"Only {len(counted)} comparable source(s); at least {MIN_SOURCES} are required. "
            "Nothing was stored. Record `salary none` with what was checked if research is over.",
            comparable=len(counted), excluded=excluded,
        )
    midpoints = [(i["amount_min"] + i["amount_max"]) / 2 for i in counted]
    amount = round(statistics.median(midpoints))
    confidence = _confidence(counted, criteria)
    reused = submission.get("reused") is True  # type: ignore[union-attr]
    suggestion_id = _store(conn, posting_id, {
        "status": "suggested", "amount": amount,
        "range_min": min(i["amount_min"] for i in counted),
        "range_max": max(i["amount_max"] for i in counted),
        "currency": criteria["currency"], "basis": criteria["basis"],
        "confidence": confidence, "criteria": criteria, "checked": None,
    }, [i["id"] for i in counted], "reused" if reused else "suggested")
    from . import learning

    learning.record_influence(conn, "salary", posting_id, areas=("salary",))
    result = current(conn, posting_id)
    assert result is not None and result["id"] == suggestion_id
    result["excluded"] = excluded
    return result


def mark_no_data(conn: sqlite3.Connection, posting_id: int, checked: object) -> dict:
    """Record that research found no reliable data, and what was checked."""
    _posting(conn, posting_id)
    if not isinstance(checked, list) or not checked or any(
            not isinstance(c, str) or not c.strip() for c in checked):
        _fail("list what was checked (sources and searches), at least one item")
    _store(conn, posting_id, {
        "status": "no_data", "amount": None, "range_min": None, "range_max": None,
        "currency": None, "basis": None, "confidence": None, "criteria": None,
        "checked": [c.strip() for c in checked],  # type: ignore[union-attr]
    }, [], "no_data")
    return current(conn, posting_id)  # type: ignore[return-value]


def _store(conn: sqlite3.Connection, posting_id: int, data: dict, evidence_ids: list[int],
           outcome: str) -> int:
    now = now_iso()
    conn.execute("UPDATE salary_suggestions SET is_current = 0"
                 " WHERE posting_id = ? AND is_current = 1", (posting_id,))
    cursor = conn.execute(
        "INSERT INTO salary_suggestions (posting_id, status, amount, range_min, range_max,"
        " currency, basis, confidence, criteria, checked, created_at, is_current)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (posting_id, data["status"], data["amount"], data["range_min"], data["range_max"],
         data["currency"], data["basis"], data["confidence"],
         json.dumps(data["criteria"], ensure_ascii=False) if data["criteria"] else None,
         json.dumps(data["checked"], ensure_ascii=False) if data["checked"] else None, now),
    )
    suggestion_id = int(cursor.lastrowid)  # type: ignore[arg-type]
    for evidence_id in evidence_ids:
        conn.execute("INSERT INTO salary_suggestion_evidence (suggestion_id, evidence_id)"
                     " VALUES (?, ?)", (suggestion_id, evidence_id))
    key = _posting_key(_posting(conn, posting_id))
    conn.execute(
        "INSERT INTO salary_research_log (posting_id, research_company, research_role,"
        " research_location, outcome, checked, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (posting_id, *key, outcome,
         json.dumps(data["checked"], ensure_ascii=False) if data["checked"] else None, now),
    )
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
        " VALUES ('posting', ?, 'salary', ?, ?)",
        (str(posting_id), json.dumps({"suggestion_id": suggestion_id, "status": data["status"],
                                      "amount": data["amount"]}), now),
    )
    bump_changes(conn)
    return suggestion_id


def current(conn: sqlite3.Connection, posting_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM salary_suggestions WHERE posting_id = ? AND is_current = 1", (posting_id,)
    ).fetchone()
    if row is None:
        return None
    items = [
        _evidence_dict(e) for e in conn.execute(
            "SELECT e.* FROM salary_evidence e JOIN salary_suggestion_evidence s"
            " ON s.evidence_id = e.id WHERE s.suggestion_id = ? ORDER BY e.id", (row["id"],))
    ]
    return {
        "id": row["id"], "status": row["status"], "amount": row["amount"],
        "range_min": row["range_min"], "range_max": row["range_max"],
        "currency": row["currency"], "basis": row["basis"], "period": "month",
        "confidence": row["confidence"],
        "criteria": json.loads(row["criteria"]) if row["criteria"] else None,
        "checked": json.loads(row["checked"]) if row["checked"] else None,
        "evidence": items, "source_count": len(items), "created_at": row["created_at"],
    }


def lookup(conn: sqlite3.Connection, posting_id: int, today: date | None = None) -> dict:
    """Recent evidence and research for the same company, role, and location (60 days)."""
    today = today or _today()
    row = _posting(conn, posting_id)
    key = _posting_key(row)
    since = (today - timedelta(days=CACHE_DAYS)).isoformat()
    items = [
        _evidence_dict(e) for e in conn.execute(
            "SELECT * FROM salary_evidence WHERE research_company = ? AND research_role = ?"
            " AND research_location = ? AND substr(created_at, 1, 10) >= ? ORDER BY id",
            (*key, since))
    ]
    research = [
        {"posting_id": r["posting_id"], "outcome": r["outcome"],
         "checked": json.loads(r["checked"]) if r["checked"] else None,
         "created_at": r["created_at"]}
        for r in conn.execute(
            "SELECT * FROM salary_research_log WHERE research_company = ? AND research_role = ?"
            " AND research_location = ? AND substr(created_at, 1, 10) >= ? ORDER BY id DESC",
            (*key, since))
    ]
    comparable = []
    if row["country"] and row["seniority"]:
        for item in items:
            criteria = {"country": row["country"], "level": row["seniority"],
                        "currency": item["currency"], "basis": item["basis"]}
            if not comparability(item, criteria, today):
                comparable.append(item["id"])
    return {
        "posting_id": posting_id,
        "key": {"company": key[0], "role": key[1], "location": key[2]},
        "evidence": items, "research": research,
        "comparable_evidence_ids": comparable,
        "reusable": len(comparable) >= MIN_SOURCES,
        "recently_without_data": any(r["outcome"] == "no_data" for r in research),
    }
