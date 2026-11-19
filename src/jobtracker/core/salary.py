"""Salary suggestions as the agent's analysis, gated by evidence.

`lookup` gathers everything available for a posting without searching: the offered
salary, the user's history (salaries offered to the user and published in stored
postings, each with its company's profile), fresh stored evidence for the posting's
company and market keys, and what was already checked. The agent searches only what
is missing, weighs the data (the same company more; otherwise similar companies), and
records a range with a short note through `set_suggestion`.

The evidence rule: every suggestion cites at least one source. One is enough when it
is a reference for the same company or the user's own history; a suggestion resting
only on the market needs two comparable sources (same country, level, currency, and
basis, no older than 18 months). Nothing is converted across currencies; yearly
figures become monthly by dividing by 12. Otherwise the posting has "no reliable data".
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

MIN_SOURCES = 2                      # for a suggestion resting only on the market
MAX_EVIDENCE_AGE_DAYS = 548          # 18 months
CACHE_DAYS = 60                      # company evidence (same company, family, country)
MARKET_DAYS = 30                     # market evidence (family, level, country)
NOTE_MAX = 300
SCOPES = ("company", "market")
WEIGHTS = ("main", "supporting")
HISTORY_LIMIT = 60
SENIORITY_WORDS = {"senior", "sr", "junior", "jr", "semi", "semisenior", "ssr", "mid", "lead",
                   "principal", "staff", "trainee", "intern", "i", "ii", "iii", "iv"}
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


def title_family(title: str) -> str:
    """The title without its seniority words: "Senior Data Engineer II" → "data engineer"."""
    words = [w for w in normalize.title_key(title).split() if w not in SENIORITY_WORDS]
    return " ".join(words) or normalize.title_key(title)


def _keys(row: sqlite3.Row) -> dict:
    """The posting's company key and market key, as stored in `salary_checks`."""
    family = title_family(row["title"])
    country = (row["country"] or "").upper()
    return {
        "company": {"company": normalize.company_key(row["company"]), "family": family,
                    "country": country},
        "market": {"family": family, "level": (row["seniority"] or "").casefold(),
                   "country": country},
    }


def _key_text(key: dict) -> str:
    return json.dumps(key, sort_keys=True, ensure_ascii=False)


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
    scope = record.get("scope", "market")  # type: ignore[union-attr]
    if scope not in SCOPES:
        _fail(f"{where}: 'scope' must be company (reports for this company) or market")
    return {
        "scope": scope, "role_family": title_family(key[1]),
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
            " research_location, posting_id, created_at, scope, role_family)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (item["source"], item["url"], item["summary"], item["amount_min"], item["amount_max"],
             item["currency"], item["basis"], item["original_period"], item["sample_size"],
             item["observed_on"], item["country"], item["level"], item["work_mode"],
             item["industry"], item["company_size"], int(item["from_posting"]), *item["key"],
             item["posting_id"], now, item["scope"], item["role_family"]),
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
        "scope": row["scope"], "company": row["research_company"],
        "role_family": row["role_family"], "created_at": row["created_at"],
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


def _monthly(published: dict | None) -> dict | None:
    """A published salary as monthly figures; None when its period is not converted."""
    if not published:
        return None
    divide = {"month": 1, "year": 12}.get(published.get("period", "month"))
    if divide is None:
        return None
    return {"min": round(published["min"] / divide), "max": round(published["max"] / divide),
            "currency": published["currency"], "basis": published.get("basis")}


def _history_input(conn: sqlite3.Connection, item: dict, where: str) -> dict:
    """An offer the user recorded (`application`) or a stored posting's published salary
    (`posting_id`), checked to exist and to carry a salary."""
    if item["kind"] == "offer":
        ref = item.get("application")
        row = conn.execute(
            "SELECT a.job_id, a.offered_salary_amount AS amount, a.offered_salary_currency"
            " AS currency, a.offered_salary_basis AS basis, p.company, p.title FROM applications a"
            " JOIN postings p ON p.id = a.posting_id WHERE a.job_id = ?", (ref,)).fetchone()
        if row is None or row["amount"] is None:
            _fail(f"{where}: application '{ref}' has no offered salary recorded")
        return {"kind": "offer", "application": row["job_id"], "company": row["company"],
                "title": row["title"], "amount_min": row["amount"], "amount_max": row["amount"],
                "currency": row["currency"], "basis": row["basis"] or "gross"}
    ref = item.get("posting_id")
    if isinstance(ref, bool) or not isinstance(ref, int):
        _fail(f"{where}: 'posting_id' must be a posting id")
    row = _posting(conn, ref)
    monthly = _monthly(json.loads(row["published_salary"]) if row["published_salary"] else None)
    if monthly is None:
        _fail(f"{where}: posting {ref} has no monthly or yearly published salary")
    return {"kind": "published", "posting_id": ref, "company": row["company"],
            "title": row["title"], "url": row["url"], "amount_min": monthly["min"],
            "amount_max": monthly["max"], "currency": monthly["currency"],
            "basis": monthly["basis"] or "gross"}


def _inputs(conn: sqlite3.Connection, raw: object, criteria: dict, today: date) -> tuple:
    """Validated inputs, the evidence ids among them, and what does not count and why."""
    if not isinstance(raw, list) or not raw:
        _fail("'inputs' must list the sources the suggestion rests on (at least one)")
    inputs, evidence_ids, excluded = [], [], []
    for index, item in enumerate(raw):
        where = f"input {index + 1}"
        if not isinstance(item, dict):
            _fail(f"{where}: must be an object")
        weight = item.get("weight", "main")
        if weight not in WEIGHTS:
            _fail(f"{where}: 'weight' must be main or supporting")
        kind = item.get("kind")
        if kind == "evidence" or "evidence_id" in item:
            found = evidence(conn, item.get("evidence_id"))  # type: ignore[arg-type]
            problems = comparability(found, criteria, today)
            if problems:
                excluded.append({"evidence_id": found["id"], "source": found["source"],
                                 "problems": problems})
                continue
            inputs.append({"kind": found["scope"], "evidence_id": found["id"],
                           "source": found["source"], "url": found["url"], "weight": weight,
                           "amount_min": found["amount_min"], "amount_max": found["amount_max"],
                           "currency": found["currency"]})
            evidence_ids.append(found["id"])
        elif kind in ("offer", "published"):
            found = _history_input(conn, item, where)
            problems = [p for p in (
                found["currency"] != criteria["currency"]
                and f"different currency ({found['currency']})",
                found["basis"] != criteria["basis"]
                and f"{found['basis']} instead of {criteria['basis']}") if p]
            if problems:
                excluded.append({**{k: found[k] for k in ("kind", "application", "posting_id")
                                    if k in found}, "problems": problems})
                continue
            inputs.append({**found, "weight": weight})
        else:
            _fail(f"{where}: 'kind' must be evidence (with evidence_id), offer (with "
                  "application), or published (with posting_id)")
    return inputs, evidence_ids, excluded


def _counts(inputs: list[dict]) -> dict:
    counts = {"company": 0, "history": 0, "market": 0}
    for item in inputs:
        counts["history" if item["kind"] in ("offer", "published") else item["kind"]] += 1
    return counts


def _set_aside(raw: object) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        _fail("'set_aside' must be a list")
    result = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict) or not str(item.get("reason") or "").strip() \
                or not str(item.get("value") or "").strip():
            _fail(f"set_aside {index + 1}: give the report's 'value' and the 'reason'")
        result.append({"value": str(item["value"]).strip(), "reason": str(item["reason"]).strip(),
                       "source": str(item.get("source") or "").strip() or None})
    return result


def set_suggestion(
    conn: sqlite3.Connection, posting_id: int, submission: object, today: date | None = None,
) -> dict:
    """Store the agent's suggestion: a range, the inputs it rests on with their weight,
    the reports it set aside, and a short note. Refused without a source, and refused
    when it rests only on the market with fewer than two comparable sources.

    `evidence_ids` may stand for `inputs` (each a piece of stored evidence)."""
    today = today or _today()
    row = _posting(conn, posting_id)
    if not isinstance(submission, dict):
        _fail("expected an object with 'inputs', 'note', and 'criteria'")
    criteria = _criteria(row, submission.get("criteria"))  # type: ignore[union-attr]
    raw = submission.get("inputs")  # type: ignore[union-attr]
    if raw is None and isinstance(submission.get("evidence_ids"), list):  # type: ignore[union-attr]
        raw = [{"evidence_id": i} for i in dict.fromkeys(submission["evidence_ids"])]  # type: ignore[index]
    note = submission.get("note")  # type: ignore[union-attr]
    if not isinstance(note, str) or not note.strip():
        _fail("'note' is required: one or two sentences that justify the suggestion")
    if len(note.strip()) > NOTE_MAX:
        _fail(f"'note' must be at most {NOTE_MAX} characters")
    inputs, evidence_ids, excluded = _inputs(conn, raw, criteria, today)
    counts = _counts(inputs)
    if not inputs or (counts["company"] == 0 and counts["history"] == 0
                      and counts["market"] < MIN_SOURCES):
        raise JobTrackerError(
            "insufficient_evidence",
            f"{len(inputs)} comparable source(s). A suggestion needs one reference for the "
            f"same company or from the user's history, or at least {MIN_SOURCES} market "
            "sources. Nothing was stored. Record `salary none` with what was checked if "
            "research is over.",
            comparable=len(inputs), excluded=excluded,
        )
    low, high = submission.get("range_min"), submission.get("range_max")  # type: ignore[union-attr]
    if low is None and high is None:
        low = min(i["amount_min"] for i in inputs)
        high = max(i["amount_max"] for i in inputs)
    low = _positive(low, "range_min", "suggestion")
    high = _positive(high, "range_max", "suggestion")
    if low > high:
        _fail("'range_min' is larger than 'range_max'")
    amount = submission.get("amount")  # type: ignore[union-attr]
    if amount is None:
        midpoints = [(i["amount_min"] + i["amount_max"]) / 2 for i in inputs
                     if i["weight"] == "main"] or [(low + high) / 2]
        amount = min(max(round(statistics.median(midpoints)), low), high)
    amount = _positive(amount, "amount", "suggestion")
    evidence_items = [evidence(conn, i) for i in evidence_ids]
    confidence = _confidence_of(counts, evidence_items, criteria)
    reused = submission.get("reused") is True  # type: ignore[union-attr]
    suggestion_id = _store(conn, posting_id, {
        "status": "suggested", "amount": amount, "range_min": low, "range_max": high,
        "currency": criteria["currency"], "basis": criteria["basis"],
        "confidence": confidence, "criteria": criteria, "checked": None,
        "note": note.strip(), "inputs": inputs, "counts": counts,
        "set_aside": _set_aside(submission.get("set_aside")),  # type: ignore[union-attr]
    }, evidence_ids, "reused" if reused else "suggested")
    record_checks(conn, posting_id, submission.get("checked"))  # type: ignore[union-attr]
    from . import learning

    learning.record_influence(conn, "salary", posting_id, areas=("salary",))
    result = current(conn, posting_id)
    assert result is not None and result["id"] == suggestion_id
    result["excluded"] = excluded
    return result


def _confidence_of(counts: dict, items: list[dict], criteria: dict) -> str:
    total = sum(counts.values())
    kinds = sum(1 for value in counts.values() if value)
    if total >= 3 and (counts["company"] or kinds >= 2):
        return "high"
    if total >= 2:
        return "medium" if not items else max(
            ("medium", _confidence(items, criteria)), key=("low", "medium", "high").index)
    return "low"


def record_checks(conn: sqlite3.Connection, posting_id: int, checks: object) -> list[dict]:
    """What the agent searched for this posting's keys, found or not, so that a source is
    not searched again for the same key within its reuse period."""
    if checks is None:
        return []
    if not isinstance(checks, list):
        _fail("'checked' must be a list")
    keys = _keys(_posting(conn, posting_id))
    now = now_iso()
    stored = []
    for index, item in enumerate(checks):
        if isinstance(item, str):
            continue  # a plain description, kept on a "no data" record
        where = f"checked {index + 1}"
        if not isinstance(item, dict) or not str(item.get("source") or "").strip():
            _fail(f"{where}: give the 'source' searched")
        scope = item.get("scope", "market")
        if scope not in SCOPES:
            _fail(f"{where}: 'scope' must be company or market")
        found = bool(item.get("found", False))
        detail = str(item.get("detail") or "").strip() or None
        conn.execute("INSERT INTO salary_checks (scope, key, source, found, detail, posting_id,"
                     " checked_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (scope, _key_text(keys[scope]), str(item["source"]).strip(), int(found),
                      detail, posting_id, now))
        stored.append({"scope": scope, "source": str(item["source"]).strip(), "found": found})
    return stored


def mark_no_data(conn: sqlite3.Connection, posting_id: int, checked: object) -> dict:
    """Record that research found no reliable data, and what was checked: plain
    descriptions, or {source, scope, found, detail} objects that also count as checks."""
    _posting(conn, posting_id)
    if not isinstance(checked, list) or not checked:
        _fail("list what was checked (sources and searches), at least one item")
    lines = []
    for item in checked:
        if isinstance(item, str) and item.strip():
            lines.append(item.strip())
        elif isinstance(item, dict) and str(item.get("source") or "").strip():
            lines.append(f"{str(item['source']).strip()}: "
                         f"{str(item.get('detail') or 'nothing comparable').strip()}")
        else:
            _fail("each checked item is a description or an object with 'source'")
    _store(conn, posting_id, {
        "status": "no_data", "amount": None, "range_min": None, "range_max": None,
        "currency": None, "basis": None, "confidence": None, "criteria": None,
        "checked": lines, "note": None, "inputs": None, "counts": None, "set_aside": None,
    }, [], "no_data")
    record_checks(conn, posting_id, checked)
    return current(conn, posting_id)  # type: ignore[return-value]


def _store(conn: sqlite3.Connection, posting_id: int, data: dict, evidence_ids: list[int],
           outcome: str) -> int:
    now = now_iso()
    conn.execute("UPDATE salary_suggestions SET is_current = 0"
                 " WHERE posting_id = ? AND is_current = 1", (posting_id,))
    cursor = conn.execute(
        "INSERT INTO salary_suggestions (posting_id, status, amount, range_min, range_max,"
        " currency, basis, confidence, criteria, checked, created_at, is_current, note, inputs,"
        " set_aside, counts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)",
        (posting_id, data["status"], data["amount"], data["range_min"], data["range_max"],
         data["currency"], data["basis"], data["confidence"],
         json.dumps(data["criteria"], ensure_ascii=False) if data["criteria"] else None,
         json.dumps(data["checked"], ensure_ascii=False) if data["checked"] else None, now,
         data.get("note"), *(json.dumps(data[k], ensure_ascii=False) if data.get(k) is not None
                             else None for k in ("inputs", "set_aside", "counts"))),
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
        "evidence": items, "created_at": row["created_at"],
        "note": row["note"],
        "inputs": json.loads(row["inputs"]) if row["inputs"] else [],
        "set_aside": json.loads(row["set_aside"]) if row["set_aside"] else [],
        "counts": json.loads(row["counts"]) if row["counts"] else (
            {"company": 0, "history": 0, "market": len(items)} if items else None),
        "source_count": len(json.loads(row["inputs"])) if row["inputs"] else len(items),
    }


def profile(conn: sqlite3.Connection, company: str) -> dict | None:
    row = conn.execute("SELECT * FROM company_profiles WHERE company_key = ?",
                       (normalize.company_key(company),)).fetchone()
    if row is None:
        return None
    return {"name": row["name"], "industry": row["industry"], "size_band": row["size_band"],
            "kind": row["kind"], "source": row["source"], "source_url": row["source_url"],
            "updated_at": row["updated_at"]}


def set_profile(conn: sqlite3.Connection, company: str, data: object) -> dict:
    """Record what is known about a company, from the posting's text (`source:
    "posting"`) or a linked source; a field left out or "unknown" stays unknown."""
    if not isinstance(company, str) or not normalize.company_key(company):
        _fail("give the company's name")
    if not isinstance(data, dict):
        _fail("expected an object with industry, size_band, kind, and source")
    source = data.get("source")
    if not isinstance(source, str) or not source.strip():
        _fail("'source' is required: \"posting\" or the name of the linked source")
    url = None
    if source.strip() != "posting":
        url = normalize.safe_url(data.get("source_url"), "source_url")
    held = profile(conn, company) or {}
    values = {}
    for field in ("industry", "size_band", "kind"):
        value = data.get(field, held.get(field))
        if value is not None and (not isinstance(value, str) or not value.strip()):
            _fail(f"'{field}' must be text or omitted")
        values[field] = None if value is None or value.strip().casefold() == "unknown" \
            else value.strip()
    conn.execute(
        "INSERT INTO company_profiles (company_key, name, industry, size_band, kind, source,"
        " source_url, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (company_key) DO"
        " UPDATE SET name = excluded.name, industry = excluded.industry, size_band ="
        " excluded.size_band, kind = excluded.kind, source = excluded.source, source_url ="
        " excluded.source_url, updated_at = excluded.updated_at",
        (normalize.company_key(company), company.strip(), values["industry"],
         values["size_band"], values["kind"], source.strip(), url, now_iso()))
    bump_changes(conn)
    return profile(conn, company)  # type: ignore[return-value]


def history(conn: sqlite3.Connection, row: sqlite3.Row) -> list[dict]:
    """The user's own salary data, the same company first: salaries offered to the user
    (recorded on applications) and salaries published in stored postings."""
    company = normalize.company_key(row["company"])
    family = title_family(row["title"])
    items = []
    for offer in conn.execute(
        "SELECT a.job_id, a.offered_salary_amount AS amount, a.offered_salary_currency AS"
        " currency, a.offered_salary_basis AS basis, a.updated_at, p.id AS posting_id,"
        " p.company, p.title, p.seniority, p.country, p.work_mode, p.url FROM applications a"
        " JOIN postings p ON p.id = a.posting_id WHERE a.offered_salary_amount IS NOT NULL"
        " AND p.is_demo = (SELECT is_demo FROM postings WHERE id = ?)", (row["id"],)):
        items.append({"kind": "offer", "application": offer["job_id"],
                      "posting_id": offer["posting_id"], "company": offer["company"],
                      "title": offer["title"], "level": offer["seniority"],
                      "country": offer["country"], "work_mode": offer["work_mode"],
                      "amount_min": offer["amount"], "amount_max": offer["amount"],
                      "currency": offer["currency"], "basis": offer["basis"] or "gross",
                      "date": (offer["updated_at"] or "")[:10], "url": offer["url"]})
    for other in conn.execute(
        "SELECT id, company, title, seniority, country, work_mode, url, posted_at, captured_at,"
        " published_salary FROM postings WHERE published_salary IS NOT NULL AND id != ?"
        " AND is_demo = (SELECT is_demo FROM postings WHERE id = ?)", (row["id"], row["id"])):
        monthly = _monthly(json.loads(other["published_salary"]))
        if monthly is None:
            continue
        items.append({"kind": "published", "posting_id": other["id"], "company": other["company"],
                      "title": other["title"], "level": other["seniority"],
                      "country": other["country"], "work_mode": other["work_mode"],
                      "amount_min": monthly["min"], "amount_max": monthly["max"],
                      "currency": monthly["currency"], "basis": monthly["basis"],
                      "date": other["posted_at"] or other["captured_at"][:10], "url": other["url"]})
    for item in items:
        item["same_company"] = normalize.company_key(item["company"]) == company
        item["same_family"] = title_family(item["title"]) == family
        item["profile"] = profile(conn, item["company"])
    items = sorted(items, key=lambda i: (not i["same_company"], not i["same_family"],
                                         i["country"] != row["country"]))
    return items[:HISTORY_LIMIT]


def lookup(conn: sqlite3.Connection, posting_id: int, today: date | None = None) -> dict:
    """Everything available for the agent's analysis of one posting, without searching:
    the offered salary, the user's history, fresh evidence for the company key (60 days)
    and the market key (30 days), and which sources were already checked for each."""
    today = today or _today()
    row = _posting(conn, posting_id)
    keys = _keys(row)
    company_since = (today - timedelta(days=CACHE_DAYS)).isoformat()
    market_since = (today - timedelta(days=MARKET_DAYS)).isoformat()
    company_items = [_evidence_dict(e) for e in conn.execute(
        "SELECT * FROM salary_evidence WHERE scope = 'company' AND research_company = ?"
        " AND role_family = ? AND country = ? AND substr(created_at, 1, 10) >= ? ORDER BY id",
        (keys["company"]["company"], keys["company"]["family"], keys["company"]["country"],
         company_since))]
    market_items = [_evidence_dict(e) for e in conn.execute(
        "SELECT * FROM salary_evidence WHERE scope = 'market' AND role_family = ?"
        " AND lower(level) = ? AND country = ? AND substr(created_at, 1, 10) >= ? ORDER BY id",
        (keys["market"]["family"], keys["market"]["level"], keys["market"]["country"],
         market_since))]
    # Evidence stored before scopes existed: the same company, role, and location.
    legacy = [_evidence_dict(e) for e in conn.execute(
        "SELECT * FROM salary_evidence WHERE role_family IS NULL AND research_company = ?"
        " AND research_role = ? AND research_location = ? AND substr(created_at, 1, 10) >= ?"
        " ORDER BY id", (*_posting_key(row), company_since))]
    checked = []
    for scope, since in (("company", company_since), ("market", market_since)):
        for check in conn.execute(
                "SELECT source, found, detail, checked_at FROM salary_checks WHERE scope = ?"
                " AND key = ? AND substr(checked_at, 1, 10) >= ? ORDER BY id DESC",
                (scope, _key_text(keys[scope]), since)):
            checked.append({"scope": scope, "source": check["source"],
                            "found": bool(check["found"]), "detail": check["detail"],
                            "checked_at": check["checked_at"]})
    research = [
        {"posting_id": r["posting_id"], "outcome": r["outcome"],
         "checked": json.loads(r["checked"]) if r["checked"] else None,
         "created_at": r["created_at"]}
        for r in conn.execute(
            "SELECT * FROM salary_research_log WHERE research_company = ? AND research_role = ?"
            " AND research_location = ? AND substr(created_at, 1, 10) >= ? ORDER BY id DESC",
            (*_posting_key(row), company_since))
    ]
    evidence_items = company_items + market_items + [e for e in legacy if e["id"] not in {
        i["id"] for i in company_items + market_items}]
    comparable = []
    if row["country"] and row["seniority"]:
        for item in evidence_items:
            criteria = {"country": row["country"], "level": row["seniority"],
                        "currency": item["currency"], "basis": item["basis"]}
            if not comparability(item, criteria, today):
                comparable.append(item["id"])
    published = json.loads(row["published_salary"]) if row["published_salary"] else None
    return {
        "posting_id": posting_id,
        "posting": {"title": row["title"], "company": row["company"], "level": row["seniority"],
                    "country": row["country"], "work_mode": row["work_mode"],
                    "profile": profile(conn, row["company"])},
        "offered": _monthly(published),
        "offered_as_published": published,
        "keys": keys,
        "history": history(conn, row),
        "evidence": {"company": company_items, "market": market_items, "earlier": [
            e for e in legacy if e["id"] not in {i["id"] for i in company_items + market_items}]},
        "checked": checked,
        "current": current(conn, posting_id),
        "key": {"company": _posting_key(row)[0], "role": _posting_key(row)[1],
                "location": _posting_key(row)[2]},
        "research": research,
        "comparable_evidence_ids": comparable,
        "recently_without_data": any(r["outcome"] == "no_data" for r in research),
    }
