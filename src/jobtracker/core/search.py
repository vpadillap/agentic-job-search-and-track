"""Search runs and postings: start, import with de-duplication, filter, finish, summarize.

The agent does the browsing and the judgement; this module decides what is a
duplicate, what was already seen, and what each run found, so results are
consistent between runs.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta

from . import normalize, providers
from . import profile as profile_service
from .db import bump_changes, now_iso
from .errors import JobTrackerError
from .paths import Paths

FILTER_REASONS = (
    "title", "work_mode", "contract_type", "location", "language", "company", "salary", "rule",
)
PROVIDER_STATUSES = ("pending", "ok", "skipped", "failed", "disabled")
SKIP_REASONS = (
    "live_walk", "login_required", "missing_dependency", "invalid_file", "disabled", "error",
    "blocked", "not_searched",
)
QUESTION_KINDS = ("text", "long_text", "choice", "multi_choice", "number", "yes_no", "file")
DUPLICATE_DAYS = 7   # publication dates this close make a same company+title a possible duplicate
DEFAULT_AGE_DAYS = 7
MAX_AGE_DAYS = 90
WORK_MODE_DETAIL_MAX = 200  # characters of free text describing the work arrangement


def _fail(message: str, **details: object):
    raise JobTrackerError("invalid_posting", message, **details)


def _local_today() -> date:
    return datetime.now().date()


# ── runs ──────────────────────────────────────────────────────────────────

def _run_row(conn: sqlite3.Connection, run_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM search_runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise JobTrackerError("not_found", f"There is no search run {run_id}")
    return row


def _run_providers(row: sqlite3.Row) -> list[dict]:
    return json.loads(row["providers"])


def _save_run_providers(conn: sqlite3.Connection, run_id: int, items: list[dict]) -> None:
    conn.execute("UPDATE search_runs SET providers = ? WHERE id = ?",
                 (json.dumps(items, ensure_ascii=False), run_id))


def start_run(
    conn: sqlite3.Connection, paths: Paths, days: int | None = None, *,
    demo: bool = False, started_at: str | None = None,
    demo_providers: list[dict] | None = None, demo_titles: list[str] | None = None,
) -> dict:
    """Open a run: the titles and providers to search and where raw captures go.

    `demo_*` arguments are used only by `jobtracker demo seed`.
    """
    active = profile_service.get_active(conn)
    if active is None and not demo:
        raise JobTrackerError("no_profile", "There is no profile yet. Run /setup first.")
    titles = profile_service.included_titles(active)
    if not titles and not demo:
        raise JobTrackerError(
            "no_titles", "The profile has no included target titles. Confirm titles in /setup."
        )
    if days is None:
        days = int(active["posting_age_days"]) if active else DEFAULT_AGE_DAYS
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= MAX_AGE_DAYS:
        raise JobTrackerError(
            "invalid_run", f"days must be a whole number from 1 to {MAX_AGE_DAYS}")

    run_providers = []
    for provider in providers.with_state(conn):
        if provider.get("valid", True) and provider.get("kind") not in ("jobs", "both"):
            continue
        item = {"id": str(provider["id"]), "name": str(provider.get("name") or provider["id"]),
                "status": "pending", "reason": None, "detail": None,
                "live_walk": bool(provider.get("live_walk")),
                "requires_login": bool(provider.get("requires_login")),
                "file": provider["file"]}
        if not provider["enabled"]:
            item.update(status="disabled", reason="disabled")
        elif not provider.get("valid", True):
            item.update(status="skipped", reason="invalid_file",
                        detail="; ".join(map(str, provider["problems"])))  # type: ignore[call-overload]
        run_providers.append(item)
    if demo and demo_providers is not None:
        run_providers = [
            {"id": p["id"], "name": p["name"], "status": "pending", "reason": None,
             "detail": None, "live_walk": bool(p.get("live_walk")), "requires_login": False,
             "file": None}
            for p in demo_providers
        ]
    if demo and demo_titles is not None:
        titles = demo_titles

    started = started_at or now_iso()
    folder = None
    if not demo:
        local_start = datetime.now()
        target = paths.search_folder(local_start)
        suffix = 2
        while target.exists():
            target = paths.search_folder(local_start).with_name(
                f"{local_start:%Y%m%d-%H%M}-{suffix}")
            suffix += 1
        target.mkdir(parents=True)
        folder = target.relative_to(paths.home).as_posix()
    season = conn.execute("SELECT id FROM seasons WHERE is_active = 1").fetchone()
    cursor = conn.execute(
        "INSERT INTO search_runs (season_id, started_at, status, posting_age_days, titles,"
        " providers, capture_folder, is_demo) VALUES (?, ?, 'running', ?, ?, ?, ?, ?)",
        (season["id"] if season else None, started, days, json.dumps(titles, ensure_ascii=False),
         json.dumps(run_providers, ensure_ascii=False), folder, int(demo)),
    )
    run_id = int(cursor.lastrowid)  # type: ignore[arg-type]
    bump_changes(conn)
    start_day = _local_today() if started_at is None else normalize.parse_date(started)
    return {
        "run_id": run_id,
        "started_at": started,
        "posting_age_days": days,
        "published_since": (start_day - timedelta(days=days)).isoformat(),
        "titles": titles,
        "capture_folder": str(paths.home / folder) if folder else None,
        "providers": run_providers,
        "to_search": [p["id"] for p in run_providers if p["status"] == "pending"],
    }


def record_provider(
    conn: sqlite3.Connection, run_id: int, provider_id: str, status: str,
    reason: str | None = None, detail: str | None = None,
) -> dict:
    """Record how a provider went in this run: searched, skipped, or failed."""
    row = _run_row(conn, run_id)
    if row["status"] != "running":
        raise JobTrackerError("run_finished", f"Run {run_id} is already finished")
    if status not in ("ok", "skipped", "failed"):
        raise JobTrackerError("invalid_run", "status must be ok, skipped, or failed")
    if status != "ok" and reason not in SKIP_REASONS:
        raise JobTrackerError(
            "invalid_run", f"a skipped or failed provider needs a reason: {', '.join(SKIP_REASONS)}"
        )
    items = _run_providers(row)
    for item in items:
        if item["id"] == provider_id:
            if item["status"] == "disabled":
                raise JobTrackerError(
                    "provider_disabled", f"'{provider_id}' is disabled; it is not searched"
                )
            item.update(status=status, reason=reason if status != "ok" else None,
                        detail=(detail or "").strip() or None)
            break
    else:
        raise JobTrackerError("not_found", f"'{provider_id}' is not a job provider of run {run_id}")
    _save_run_providers(conn, run_id, items)
    bump_changes(conn)
    return summary(conn, run_id)


def finish_run(conn: sqlite3.Connection, run_id: int) -> dict:
    row = _run_row(conn, run_id)
    if row["status"] == "finished":
        return summary(conn, run_id)
    now = now_iso()
    items = _run_providers(row)
    for item in items:
        if item["status"] == "pending":
            item.update(status="skipped", reason="not_searched")
        if item["status"] != "disabled" and not row["is_demo"]:
            providers.record_result(
                conn, item["id"], item["status"],
                item["detail"] or item["reason"] if item["status"] != "ok" else None, now,
            )
    _save_run_providers(conn, run_id, items)
    conn.execute("UPDATE search_runs SET status = 'finished', finished_at = ? WHERE id = ?",
                 (now, run_id))
    bump_changes(conn)
    return summary(conn, run_id)


def latest_run_id(conn: sqlite3.Connection) -> int | None:
    row = conn.execute("SELECT id FROM search_runs ORDER BY started_at DESC, id DESC LIMIT 1"
                       ).fetchone()
    return int(row["id"]) if row else None


def _counts(conn: sqlite3.Connection, run_id: int) -> dict:
    counts = {"found": 0, "new": 0, "filtered": 0, "duplicate": 0, "seen": 0}
    for row in conn.execute(
        "SELECT outcome, COUNT(*) AS n FROM run_results WHERE run_id = ? GROUP BY outcome",
        (run_id,),
    ):
        counts[row["outcome"]] = row["n"]
        counts["found"] += row["n"]
    counts["duplicate_or_seen"] = counts["duplicate"] + counts["seen"]
    return counts


def summary(conn: sqlite3.Connection, run_id: int, top: int = 5) -> dict:
    """The run as both the agent's report and the panel show it."""
    from . import scoring  # local import: scoring depends on postings

    row = _run_row(conn, run_id)
    found = {
        r["provider"]: r["n"] for r in conn.execute(
            "SELECT provider, COUNT(*) AS n FROM run_results WHERE run_id = ? GROUP BY provider",
            (run_id,),
        )
    }
    items = []
    for item in _run_providers(row):
        items.append({
            "id": item["id"], "name": item["name"], "status": item["status"],
            "reason": item["reason"], "detail": item["detail"],
            "found": found.get(item["id"], 0),
        })
    top_rows = []
    for result in conn.execute(
        "SELECT p.id, p.title, p.company FROM run_results r JOIN postings p ON p.id = r.posting_id"
        " WHERE r.run_id = ? AND r.outcome = 'new'", (run_id,),
    ):
        score = scoring.current(conn, result["id"])
        top_rows.append({"posting_id": result["id"], "title": result["title"],
                         "company": result["company"],
                         "score": score["total"] if score else None})
    top_rows.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0), r["posting_id"]))
    return {
        "id": row["id"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "status": row["status"],
        "posting_age_days": row["posting_age_days"],
        "titles": json.loads(row["titles"]),
        "title_count": len(json.loads(row["titles"])),
        "counts": _counts(conn, run_id),
        "providers": items,
        "skipped": [i for i in items if i["status"] in ("skipped", "failed")],
        "top": top_rows[:top],
        "is_demo": bool(row["is_demo"]),
    }


def list_runs(conn: sqlite3.Connection) -> list[dict]:
    result = []
    for row in conn.execute("SELECT * FROM search_runs ORDER BY started_at DESC, id DESC"):
        result.append({
            "id": row["id"], "started_at": row["started_at"], "status": row["status"],
            "posting_age_days": row["posting_age_days"], "counts": _counts(conn, row["id"]),
        })
    return result


# ── import ────────────────────────────────────────────────────────────────

def _text(record: dict, field: str, where: str, required: bool = True) -> str | None:
    value = record.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            _fail(f"{where}: '{field}' is required", field=field)
        return None
    if not isinstance(value, str | int) or isinstance(value, bool):
        _fail(f"{where}: '{field}' must be text", field=field)
    return str(value)


def _published_salary(value: object, where: str) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        _fail(f"{where}: 'published_salary' must be an object or null")
    amounts = [value.get(k) for k in ("min", "max") if value.get(k) is not None]  # type: ignore[union-attr]
    if not amounts or any(isinstance(a, bool) or not isinstance(a, int) or a <= 0
                          for a in amounts):
        _fail(f"{where}: 'published_salary' needs a positive whole 'min' and/or 'max'")
    currency = value.get("currency")  # type: ignore[union-attr]
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isupper():
        _fail(f"{where}: 'published_salary.currency' must be a 3-letter code such as PEN")
    period = value.get("period", "month")  # type: ignore[union-attr]
    if period not in ("month", "year", "hour", "day", "week"):
        _fail(f"{where}: 'published_salary.period' must be month, year, week, day, or hour")
    basis = value.get("basis")  # type: ignore[union-attr]
    if basis not in (None, "gross", "net"):
        _fail(f"{where}: 'published_salary.basis' must be gross, net, or omitted")
    return {"min": min(amounts), "max": max(amounts), "currency": currency, "period": period,
            "basis": basis}


def _questions(value: object, where: str) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list):
        _fail(f"{where}: 'form_questions' must be a list")
    result = []
    for index, item in enumerate(value):  # type: ignore[arg-type]
        if isinstance(item, str):
            item = {"text": item}
        if not isinstance(item, dict) or not isinstance(item.get("text"), str) \
                or not item["text"].strip():
            _fail(f"{where}: form question {index + 1} needs a 'text'")
        kind = item.get("kind", "text")
        if kind not in QUESTION_KINDS:
            _fail(f"{where}: form question kind must be one of: {', '.join(QUESTION_KINDS)}")
        options = item.get("options")
        if options is not None and (not isinstance(options, list)
                                    or any(not isinstance(o, str) for o in options)):
            _fail(f"{where}: form question options must be a list of texts")
        result.append({"text": item["text"].strip(), "kind": kind, "options": options,
                       "required": bool(item.get("required", False))})
    return result


def _validate_record(record: object, index: int, reference: date) -> dict:
    where = f"posting {index + 1}"
    if not isinstance(record, dict):
        _fail(f"{where}: must be an object", index=index)
    provider = _text(record, "provider", where)
    external_id = _text(record, "external_id", where)
    url = normalize.safe_url(record.get("url"), f"{where}: url")
    title = normalize.clean_text(_text(record, "title", where) or "")
    company = normalize.clean_text(_text(record, "company", where) or "")
    description = record.get("description")
    if not isinstance(description, str) or not description.strip():
        _fail(f"{where}: 'description' is required, verbatim as published", field="description")
    location = _text(record, "location", where, required=False)
    country = _text(record, "country", where, required=False)
    if country is not None and (len(country) != 2 or not country.isalpha()):
        _fail(f"{where}: 'country' must be a 2-letter ISO code such as PE")
    if record.get("posted_at"):
        posted = normalize.parse_date(str(record["posted_at"]))
    elif record.get("posted_ago"):
        captured = normalize.parse_date(str(record["captured_at"])) if record.get(
            "captured_at") else reference
        posted = normalize.relative_date(str(record["posted_ago"]), captured)
    else:
        posted = None
    flags = record.get("flags") or []
    if not isinstance(flags, list) or any(not isinstance(f, str) or not f.strip() for f in flags):
        _fail(f"{where}: 'flags' must be a list of texts")
    return {
        "provider": provider, "external_id": external_id, "url": url, "title": title,
        "company": company, "location": normalize.clean_text(location) if location else None,
        "country": country.upper() if country else None,
        "work_mode": normalize.work_mode(record.get("work_mode")),
        "work_mode_detail": work_mode_detail(record.get("work_mode_detail"), where),
        "contract_type": normalize.contract_type(record.get("contract_type")),
        "seniority": _text(record, "seniority", where, required=False),
        "posted_at": posted.isoformat() if posted else None,
        "description": description,
        "published_salary": _published_salary(record.get("published_salary"), where),
        "language": _text(record, "language", where, required=False),
        "flags": [f.strip() for f in flags],
        "form_questions": _questions(record.get("form_questions"), where),
    }


def _store_questions(conn: sqlite3.Connection, posting_id: int, questions: list[dict]) -> None:
    conn.execute("DELETE FROM form_questions WHERE posting_id = ?", (posting_id,))
    for position, question in enumerate(questions, start=1):
        conn.execute(
            "INSERT INTO form_questions (posting_id, position, text, kind, options, required)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (posting_id, position, question["text"], question["kind"],
             json.dumps(question["options"], ensure_ascii=False)
             if question["options"] is not None else None, int(question["required"])),
        )


def _seen_reason(conn: sqlite3.Connection, posting_id: int) -> str:
    if conn.execute("SELECT 1 FROM dismissals WHERE posting_id = ?", (posting_id,)).fetchone():
        return "dismissed"
    if conn.execute("SELECT 1 FROM applications WHERE posting_id = ?", (posting_id,)).fetchone():
        return "tracked"
    return "earlier_run"


def import_postings(conn: sqlite3.Connection, run_id: int, records: object) -> dict:
    """Store what providers returned. Every record is validated before anything is stored."""
    run = _run_row(conn, run_id)
    if run["status"] != "running":
        raise JobTrackerError("run_finished", f"Run {run_id} is already finished")
    if not isinstance(records, list):
        raise JobTrackerError("invalid_posting", "expected a list of postings")
    reference = (
        datetime.fromisoformat(run["started_at"].replace("Z", "+00:00")).astimezone().date()
        if run["is_demo"] else _local_today()
    )
    run_items = {item["id"]: item for item in _run_providers(run)}
    validated = []
    for index, record in enumerate(records):
        item = _validate_record(record, index, reference)
        provider_item = run_items.get(item["provider"])
        if provider_item is None:
            _fail(f"posting {index + 1}: '{item['provider']}' is not a job provider of this run")
        if provider_item["status"] == "disabled":
            _fail(f"posting {index + 1}: '{item['provider']}' is disabled; nothing is stored "
                  "for it")
        validated.append(item)

    since = reference - timedelta(days=run["posting_age_days"])
    now = now_iso()
    report = {"run_id": run_id, "received": len(validated), "new": 0, "seen": 0, "duplicate": 0,
              "outside_window": 0, "postings": []}
    for item in validated:
        if item["posted_at"] and date.fromisoformat(item["posted_at"]) < since:
            report["outside_window"] += 1
            report["postings"].append({"external_id": item["external_id"],
                                       "provider": item["provider"], "outcome": "outside_window"})
            continue
        # The only identity: the same site's own id, or the same URL. The same job on
        # another site is a separate posting (see possible_duplicates).
        url_key = normalize.url_key(item["url"])
        existing = conn.execute(
            "SELECT id FROM postings WHERE (provider = ? AND external_id = ?) OR url_key = ?"
            " ORDER BY id LIMIT 1",
            (item["provider"], item["external_id"], url_key),
        ).fetchone()
        posting_id = existing["id"] if existing else None
        created = False
        if posting_id is None:
            cursor = conn.execute(
                "INSERT INTO postings (provider, external_id, url, url_key, title, company,"
                " location, country, work_mode, work_mode_detail, contract_type, seniority,"
                " posted_at,"
                " description, published_salary, language, flags, match_key, first_run_id,"
                " captured_at, is_demo)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (item["provider"], item["external_id"], item["url"], url_key, item["title"],
                 item["company"], item["location"], item["country"], item["work_mode"],
                 item["work_mode_detail"], item["contract_type"], item["seniority"],
                 item["posted_at"],
                 item["description"],
                 json.dumps(item["published_salary"]) if item["published_salary"] else None,
                 item["language"], json.dumps(item["flags"], ensure_ascii=False),
                 normalize.match_key(item["company"], item["title"]), run_id, now,
                 run["is_demo"]),
            )
            posting_id = int(cursor.lastrowid)  # type: ignore[arg-type]
            created = True
        if item["form_questions"] and (created or not conn.execute(
                "SELECT 1 FROM form_questions WHERE posting_id = ?", (posting_id,)).fetchone()):
            _store_questions(conn, posting_id, item["form_questions"])

        in_run = conn.execute(
            "SELECT outcome FROM run_results WHERE run_id = ? AND posting_id = ?",
            (run_id, posting_id),
        ).fetchone()
        reason = None
        if in_run is not None:
            outcome = "duplicate"
        elif not created and conn.execute(
                "SELECT first_run_id FROM postings WHERE id = ?", (posting_id,)
        ).fetchone()["first_run_id"] != run_id:
            outcome = "seen"
            reason = _seen_reason(conn, posting_id)
            if reason == "tracked":
                application = conn.execute(
                    "SELECT job_id FROM applications WHERE posting_id = ?", (posting_id,)
                ).fetchone()
                conn.execute(
                    "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
                    " VALUES ('application', ?, 'reposted', ?, ?)",
                    (application["job_id"], json.dumps(
                        {"run_id": run_id, "provider": item["provider"], "url": item["url"]}),
                     now),
                )
        else:
            outcome = "new"
        conn.execute(
            "INSERT INTO run_results (run_id, posting_id, provider, outcome, reason,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, posting_id, item["provider"], outcome, reason, now),
        )
        report[outcome] += 1
        report["postings"].append({"posting_id": posting_id, "external_id": item["external_id"],
                                   "provider": item["provider"], "outcome": outcome,
                                   "reason": reason})
        provider_item = run_items[item["provider"]]
        if provider_item["status"] == "pending":
            provider_item["status"] = "ok"
    _save_run_providers(conn, run_id, list(run_items.values()))
    bump_changes(conn)
    return report


# ── after import ──────────────────────────────────────────────────────────

def filter_postings(conn: sqlite3.Connection, run_id: int, records: object) -> dict:
    """Mark new postings of a run as filtered out, each with its reason."""
    _run_row(conn, run_id)
    if not isinstance(records, list) or not records:
        raise JobTrackerError("invalid_filter", "expected a non-empty list of exclusions")
    checked = []
    for index, record in enumerate(records):
        where = f"exclusion {index + 1}"
        if not isinstance(record, dict) or isinstance(record.get("posting_id"), bool) \
                or not isinstance(record.get("posting_id"), int):
            raise JobTrackerError("invalid_filter", f"{where}: 'posting_id' is required")
        if record.get("reason") not in FILTER_REASONS:
            raise JobTrackerError(
                "invalid_filter", f"{where}: 'reason' must be one of: {', '.join(FILTER_REASONS)}"
            )
        row = conn.execute(
            "SELECT id FROM run_results WHERE run_id = ? AND posting_id = ? AND outcome = 'new'",
            (run_id, record["posting_id"]),
        ).fetchone()
        if row is None:
            raise JobTrackerError(
                "invalid_filter",
                f"{where}: posting {record['posting_id']} is not a new result of run {run_id}",
            )
        detail = record.get("detail")
        checked.append((row["id"], record["reason"], str(detail).strip() if detail else None))
    for result_id, reason, detail in checked:
        conn.execute(
            "UPDATE run_results SET outcome = 'filtered', reason = ?, reason_detail = ?"
            " WHERE id = ?", (reason, detail, result_id),
        )
    bump_changes(conn)
    return {"filtered": len(checked), "summary": summary(conn, run_id)}


def work_mode_detail(value: object, where: str = "work_mode_detail") -> str | None:
    """How a posting describes its arrangement beyond the mode: trimmed text, or None."""
    if value is None:
        return None
    if not isinstance(value, str):
        _fail(f"{where}: 'work_mode_detail' must be text", field="work_mode_detail")
    text = normalize.clean_text(value)
    if not text:
        return None
    if len(text) > WORK_MODE_DETAIL_MAX:
        _fail(f"{where}: 'work_mode_detail' is longer than {WORK_MODE_DETAIL_MAX} characters",
              field="work_mode_detail")
    return text


def set_work_mode(conn: sqlite3.Connection, posting_id: int, mode: str | None,
                  detail: str | None, *, source: str = "user") -> dict:
    """Set or correct a posting's work mode and its detail; later imports never undo it."""
    if source not in ("agent", "user"):
        raise JobTrackerError("invalid_posting", "source must be agent or user")
    row = _posting_row(conn, posting_id)
    new_mode = normalize.work_mode(mode) if mode not in (None, "", "none") else None
    new_detail = work_mode_detail(detail)
    now = now_iso()
    conn.execute(
        "UPDATE postings SET work_mode = ?, work_mode_detail = ?, work_mode_source = ?"
        " WHERE id = ?", (new_mode, new_detail, source, posting_id))
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
        " VALUES ('posting', ?, 'work_mode', ?, ?)",
        (str(posting_id), json.dumps({
            "from": {"mode": row["work_mode"], "detail": row["work_mode_detail"],
                     "source": row["work_mode_source"]},
            "to": {"mode": new_mode, "detail": new_detail}, "source": source,
        }, ensure_ascii=False), now))
    bump_changes(conn)
    return posting(conn, posting_id, detail=False)


def _posting_row(conn: sqlite3.Connection, posting_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM postings WHERE id = ?", (posting_id,)).fetchone()
    if row is None:
        raise JobTrackerError("not_found", f"There is no posting {posting_id}")
    return row


def add_flag(conn: sqlite3.Connection, posting_id: int, text: str) -> dict:
    row = _posting_row(conn, posting_id)
    if not text.strip():
        raise JobTrackerError("invalid_posting", "a flag needs a text")
    flags = json.loads(row["flags"])
    if text.strip() not in flags:
        flags.append(text.strip())
        conn.execute("UPDATE postings SET flags = ? WHERE id = ?",
                     (json.dumps(flags, ensure_ascii=False), posting_id))
        bump_changes(conn)
    return posting(conn, posting_id)


def set_questions(conn: sqlite3.Connection, posting_id: int, questions: object) -> dict:
    _posting_row(conn, posting_id)
    _store_questions(conn, posting_id, _questions(questions, f"posting {posting_id}"))
    bump_changes(conn)
    return posting(conn, posting_id)


def questions(conn: sqlite3.Connection, posting_id: int) -> list[dict]:
    return [
        {"position": r["position"], "text": r["text"], "kind": r["kind"],
         "options": json.loads(r["options"]) if r["options"] else None,
         "required": bool(r["required"])}
        for r in conn.execute(
            "SELECT * FROM form_questions WHERE posting_id = ? ORDER BY position", (posting_id,))
    ]


def posting(conn: sqlite3.Connection, posting_id: int, *, detail: bool = True) -> dict:
    row = _posting_row(conn, posting_id)
    result = {
        "id": row["id"], "provider": row["provider"], "external_id": row["external_id"],
        "url": row["url"], "title": row["title"], "company": row["company"],
        "location": row["location"], "country": row["country"], "work_mode": row["work_mode"],
        "work_mode_detail": row["work_mode_detail"], "work_mode_source": row["work_mode_source"],
        "contract_type": row["contract_type"], "seniority": row["seniority"],
        "posted_at": row["posted_at"], "captured_at": row["captured_at"],
        "published_salary": json.loads(row["published_salary"])
        if row["published_salary"] else None,
        "language": row["language"], "flags": json.loads(row["flags"]),
        "form_question_count": conn.execute(
            "SELECT COUNT(*) FROM form_questions WHERE posting_id = ?", (posting_id,)
        ).fetchone()[0],
    }
    if detail:
        result["description"] = row["description"]
        result["form_questions"] = questions(conn, posting_id)
    return result


def possible_duplicates(
    conn: sqlite3.Connection, posting_id: int, run_id: int | None = None,
) -> list[dict]:
    """Other postings that may be the same job: a visible hint, never a merge.

    A match has the same company and title, a publication date within
    DUPLICATE_DAYS (or an unknown date), and is either part of the same search
    run or already tracked. Each stays its own row; the user picks the site.
    """
    row = _posting_row(conn, posting_id)
    result = []
    for other in conn.execute(
        "SELECT p.id, p.provider, p.url, p.title, p.company, p.posted_at, a.job_id,"
        " EXISTS (SELECT 1 FROM run_results r WHERE r.run_id = ? AND r.posting_id = p.id)"
        " AS in_run FROM postings p LEFT JOIN applications a ON a.posting_id = p.id"
        " WHERE p.match_key = ? AND p.id != ? ORDER BY p.id",
        (run_id, row["match_key"], posting_id),
    ):
        if not other["in_run"] and other["job_id"] is None:
            continue
        if row["posted_at"] and other["posted_at"]:
            gap = abs((date.fromisoformat(row["posted_at"])
                       - date.fromisoformat(other["posted_at"])).days)
            if gap > DUPLICATE_DAYS:
                continue
        result.append({
            "posting_id": other["id"], "provider": other["provider"], "url": other["url"],
            "title": other["title"], "company": other["company"],
            "posted_at": other["posted_at"], "job_id": other["job_id"],
            "where": "tracked" if other["job_id"] else "this_search",
        })
    return result


def list_postings(
    conn: sqlite3.Connection, run_id: int | None = None, outcome: str | None = None
) -> list[dict]:
    """Postings of a run (latest by default) with their outcome, for the agent."""
    from . import salary, scoring

    run_id = run_id or latest_run_id(conn)
    if run_id is None:
        return []
    query = ("SELECT r.posting_id, r.outcome, r.reason, r.reason_detail, r.provider"
             " FROM run_results r WHERE r.run_id = ?")
    params: list = [run_id]
    if outcome:
        query += " AND r.outcome = ?"
        params.append(outcome)
    query += " ORDER BY r.id"
    result = []
    for row in conn.execute(query, params):
        item = posting(conn, row["posting_id"])
        score = scoring.current(conn, row["posting_id"])
        suggestion = salary.current(conn, row["posting_id"])
        item.update(outcome=row["outcome"], reason=row["reason"],
                    reason_detail=row["reason_detail"], found_on=row["provider"],
                    score=score["total"] if score else None,
                    salary_status=suggestion["status"] if suggestion else None,
                    possible_duplicates=possible_duplicates(conn, row["posting_id"], run_id))
        result.append(item)
    return result
