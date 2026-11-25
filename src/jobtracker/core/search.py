"""Search runs and postings: start, import with de-duplication, filter, finish, summarize.

The agent does the browsing and the judgement; this module decides what is a
duplicate, what was already seen, and what each run found, so results are
consistent between runs.
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from datetime import UTC, date, datetime, timedelta

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
    "blocked", "not_searched", "other_country", "throttled",
)
COOLDOWN_MINUTES = (15, 30)   # the first and second cool-down of a provider in a run
SITE_HOST = re.compile(r"(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,63}")
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
    group: int | None = None, new_group: bool = False,
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

    country = active.get("country") if active else None
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
        elif (country and provider.get("coverage") == "local"
              and country not in (provider.get("countries") or [])):
            item.update(status="skipped", reason="other_country", detail=(
                f"works only in {', '.join(provider['countries'])}; "  # type: ignore[arg-type]
                f"the profile's country is {country}"))
        run_providers.append(item)
    if not demo:
        _inherit_cooldowns(conn, run_providers)
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
    season_id = season["id"] if season else None
    group_id = _choose_group(conn, season_id, demo, started, group, new_group)
    cursor = conn.execute(
        "INSERT INTO search_runs (season_id, started_at, status, posting_age_days, titles,"
        " providers, capture_folder, is_demo, group_id)"
        " VALUES (?, ?, 'running', ?, ?, ?, ?, ?, ?)",
        (season_id, started, days, json.dumps(titles, ensure_ascii=False),
         json.dumps(run_providers, ensure_ascii=False), folder, int(demo), group_id),
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
        "group": group_info(conn, group_id),
    }


# ── groups: the searches shown on one page ────────────────────────────────

def local_day(iso: str) -> date:
    """The user's local calendar date of a stored timestamp."""
    moment = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (moment.astimezone() if moment.tzinfo else moment).date()


def _choose_group(conn: sqlite3.Connection, season_id: int | None, demo: bool, started: str,
                  group: int | None, new_group: bool) -> int:
    """`group` joins that group; `new_group` starts one; otherwise the run joins the
    season's latest group when that group has a run on the same local day."""
    if group is not None and new_group:
        raise JobTrackerError("usage", "give --group or --new-group, not both")
    if group is not None:
        row = conn.execute("SELECT * FROM search_groups WHERE id = ?", (group,)).fetchone()
        if row is None:
            raise JobTrackerError("not_found", f"There is no search group {group}")
        if row["season_id"] != season_id or bool(row["is_demo"]) != demo:
            raise JobTrackerError("invalid_group",
                                  f"Search group {group} belongs to another season or the demo")
        return int(row["id"])
    if not new_group:
        latest = conn.execute(
            "SELECT g.id FROM search_groups g JOIN search_runs r ON r.group_id = g.id"
            " WHERE g.season_id IS ? AND g.is_demo = ? ORDER BY r.started_at DESC, r.id DESC"
            " LIMIT 1", (season_id, int(demo))).fetchone()
        if latest is not None:
            day = local_day(started)
            if any(local_day(r["started_at"]) == day for r in conn.execute(
                    "SELECT started_at FROM search_runs WHERE group_id = ?", (latest["id"],))):
                return int(latest["id"])
    cursor = conn.execute(
        "INSERT INTO search_groups (season_id, started_at, is_demo) VALUES (?, ?, ?)",
        (season_id, started, int(demo)))
    return int(cursor.lastrowid)  # type: ignore[arg-type]


def group_run_ids(conn: sqlite3.Connection, group_id: int) -> list[int]:
    """The group's runs, oldest first."""
    return [int(r["id"]) for r in conn.execute(
        "SELECT id FROM search_runs WHERE group_id = ? ORDER BY started_at, id", (group_id,))]


def group_info(conn: sqlite3.Connection, group_id: int) -> dict:
    rows = conn.execute("SELECT id, started_at FROM search_runs WHERE group_id = ?"
                        " ORDER BY started_at, id", (group_id,)).fetchall()
    days = [local_day(r["started_at"]).isoformat() for r in rows]
    return {"id": group_id, "runs": [int(r["id"]) for r in rows],
            "first_day": days[0] if days else None, "last_day": days[-1] if days else None}


def group_of_run(conn: sqlite3.Connection, run_id: int) -> int:
    return int(_run_row(conn, run_id)["group_id"])


def latest_group_id(conn: sqlite3.Connection, season: int | None = None) -> int | None:
    run_id = latest_run_id(conn, season)
    return group_of_run(conn, run_id) if run_id is not None else None


def _tried(item: dict) -> bool:
    """A run tried this provider: searched, failed, waiting, or skipped for a reason
    other than not being searched (switched off or left out of the run never counts)."""
    return item["status"] != "disabled" and not (
        item["status"] == "skipped" and item.get("reason") == "not_searched")


def group_summary(conn: sqlite3.Connection, group_id: int, top: int = 5) -> dict:
    """The page of a group: its runs' summaries added up, each posting once in the top."""
    run_ids = group_run_ids(conn, group_id)
    if not run_ids:
        raise JobTrackerError("not_found", f"There is no search group {group_id}")
    runs = [summary(conn, run_id, top=10_000) for run_id in run_ids]
    counts = {key: sum(r["counts"][key] for r in runs) for key in runs[0]["counts"]}
    # A provider's status on a page is its latest attempt (oldest run first, so a later
    # attempt replaces an earlier one); found postings add up over the page's runs.
    merged: dict[str, dict] = {}
    for run in runs:
        for item in run["providers"]:
            held = merged.get(item["id"])
            if held is None:
                merged[item["id"]] = dict(item)
                continue
            found = held["found"] + item["found"]
            last_searched = item["last_searched_at"] or held["last_searched_at"]
            if _tried(item) or not _tried(held):
                for key in ("cooldown_until", "cooldown_detail", "cooldowns"):
                    held.pop(key, None)
                held.update(item)
            held["found"] = found
            held["last_searched_at"] = last_searched
    titles: list[str] = []
    for run in runs:
        titles.extend(t for t in run["titles"] if t not in titles)
    best: dict[int, dict] = {}
    for run in runs:
        for item in run["top"]:
            best.setdefault(item["posting_id"], item)
    top_rows = sorted(best.values(), key=lambda r: (r["score"] is None, -(r["score"] or 0),
                                                    r["posting_id"]))
    items = list(merged.values())
    running = any(r["status"] == "running" for r in runs)
    last = runs[-1]
    return {
        "id": group_id,
        "group_id": group_id,
        "started_at": runs[0]["started_at"],
        "last_started_at": last["started_at"],
        "finished_at": None if running else last["finished_at"],
        "status": "running" if running else "finished",
        "posting_age_days": max(r["posting_age_days"] for r in runs),
        "titles": titles,
        "title_count": len(titles),
        "counts": counts,
        "providers": items,
        "skipped": [i for i in items if i["status"] in ("skipped", "failed")],
        "top": top_rows[:top],
        "is_demo": last["is_demo"],
        "run_count": len(runs),
        "runs": [{"id": r["id"], "started_at": r["started_at"], "status": r["status"],
                  "titles": r["titles"], "counts": r["counts"]} for r in runs],
    }


def _day_buckets(conn: sqlite3.Connection) -> list[list[sqlite3.Row]]:
    """Runs of the same season, demo or not, and local day, oldest first."""
    buckets: dict[tuple, list[sqlite3.Row]] = {}
    for row in conn.execute("SELECT id, season_id, is_demo, started_at, group_id"
                            " FROM search_runs ORDER BY started_at, id"):
        key = (row["season_id"], row["is_demo"], local_day(row["started_at"]))
        buckets.setdefault(key, []).append(row)
    return list(buckets.values())


def ungrouped_days(conn: sqlite3.Connection) -> int:
    """How many days have searches shown on more than one page."""
    return sum(1 for bucket in _day_buckets(conn) if len({r["group_id"] for r in bucket}) > 1)


def group_past_by_day(conn: sqlite3.Connection) -> dict:
    """Put the searches of each day on one page. Only joins pages, never splits one the
    user joined across days; pages left without runs are removed."""
    merged_days = 0
    for bucket in _day_buckets(conn):
        ids = [int(r["id"]) for r in bucket]
        marks = ",".join("?" * len(ids))
        current = [int(r["group_id"]) for r in conn.execute(
            f"SELECT group_id FROM search_runs WHERE id IN ({marks}) ORDER BY started_at, id",
            ids)]
        target = current[0]
        others = sorted(set(current) - {target})
        if not others:
            continue
        merged_days += 1
        for group_id in others:
            conn.execute("UPDATE search_runs SET group_id = ? WHERE group_id = ?",
                         (target, group_id))
    removed = conn.execute("DELETE FROM search_groups WHERE id NOT IN"
                           " (SELECT DISTINCT group_id FROM search_runs)").rowcount
    if merged_days:
        bump_changes(conn)
    return {"days_grouped": merged_days, "pages_removed": removed}


def list_groups(conn: sqlite3.Connection, season: int | None = None) -> list[dict]:
    """The pages to choose from, newest first."""
    where, params = _season_clause(conn, season)
    order: list[int] = []
    for row in conn.execute(f"SELECT group_id FROM search_runs{where}"
                            " ORDER BY started_at DESC, id DESC", params):
        if row["group_id"] not in order:
            order.append(row["group_id"])
    result = []
    for group_id in order:
        rows = conn.execute("SELECT id, started_at FROM search_runs WHERE group_id = ?"
                            " ORDER BY started_at, id", (group_id,)).fetchall()
        totals = {"found": 0, "new": 0, "filtered": 0, "duplicate": 0, "seen": 0,
                  "duplicate_or_seen": 0}
        for row in rows:
            for key, value in _counts(conn, row["id"]).items():
                totals[key] += value
        result.append({"id": group_id, "started_at": rows[0]["started_at"],
                       "last_started_at": rows[-1]["started_at"], "run_count": len(rows),
                       "counts": totals})
    return result


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


def _iso_at(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _seconds_of(iso: str) -> float:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def cooling_until(item: dict, now: float) -> str | None:
    """The end of a provider's cool-down when it has not passed yet."""
    until = item.get("cooldown_until")
    if until and _seconds_of(until) > now:
        return str(until)
    return None


def record_cooldown(conn: sqlite3.Connection, run_id: int, provider_id: str,
                    retry_after: float | None, detail: str, now: float) -> dict:
    """A throttle the retries did not clear: the provider waits before the next call of
    this run. The k-th cool-down lasts COOLDOWN_MINUTES[k-1] (or longer when the site
    asked); a throttle past the last one stops the provider for the run."""
    row = _run_row(conn, run_id)
    if row["status"] != "running":
        raise JobTrackerError("run_finished", f"Run {run_id} is already finished")
    items = _run_providers(row)
    item = next((i for i in items if i["id"] == provider_id), None)
    if item is None:
        raise JobTrackerError("not_found", f"'{provider_id}' is not a job provider of run {run_id}")
    count = int(item.get("cooldowns") or 0) + 1
    if count > len(COOLDOWN_MINUTES):
        item.update(status="failed", reason="blocked", detail=(
            f"throttled again after {len(COOLDOWN_MINUTES)} cool-downs: {detail}"))
        item.pop("cooldown_until", None)
        result = {"reason": "blocked", "detail": item["detail"], "resume_after": None}
    else:
        seconds = max(float(retry_after or 0), COOLDOWN_MINUTES[count - 1] * 60)
        until = _iso_at(now + seconds)
        item.update(cooldowns=count, cooldown_until=until, cooldown_detail=detail)
        result = {"reason": "throttled", "detail": detail, "resume_after": until,
                  "minutes": round(seconds / 60)}
    _save_run_providers(conn, run_id, items)
    bump_changes(conn)
    return result


def _inherit_cooldowns(conn: sqlite3.Connection, run_providers: list[dict]) -> None:
    """A cool-down from the latest earlier run still holds for a new run."""
    last = conn.execute("SELECT providers FROM search_runs WHERE is_demo = 0 "
                        "ORDER BY id DESC LIMIT 1").fetchone()
    if last is None:
        return
    now = datetime.now(UTC).timestamp()
    earlier = {i["id"]: i for i in json.loads(last["providers"] or "[]")}
    for item in run_providers:
        before = earlier.get(item["id"])
        if item["status"] == "pending" and before and cooling_until(before, now):
            item.update(cooldown_until=before["cooldown_until"],
                        cooldown_detail=before.get("cooldown_detail"))


def finish_run(conn: sqlite3.Connection, run_id: int) -> dict:
    row = _run_row(conn, run_id)
    if row["status"] == "finished":
        return summary(conn, run_id)
    now = now_iso()
    items = _run_providers(row)
    for item in items:
        until = cooling_until(item, _seconds_of(now)) if item["status"] == "pending" else None
        if until:
            item.update(status="failed", reason="throttled", detail=(
                f"cooling down until {until} after a throttle: "
                f"{item.get('cooldown_detail') or 'no detail'}"))
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


def _season_clause(conn: sqlite3.Connection, season: int | None) -> tuple[str, tuple]:
    """Runs of one season: the active one unless `season` names another."""
    from . import seasons

    if season is None:
        sid = seasons.active_id(conn)
        if sid is None:
            return "", ()
    else:
        sid = seasons.season_id(conn, season)
    return " WHERE season_id = ?", (sid,)


def latest_run_id(conn: sqlite3.Connection, season: int | None = None) -> int | None:
    """The latest run of the active season (or of season `season`)."""
    where, params = _season_clause(conn, season)
    row = conn.execute(f"SELECT id FROM search_runs{where} ORDER BY started_at DESC, id DESC"
                       " LIMIT 1", params).fetchone()
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
            # When this run read the site; on a page, the latest such time is kept.
            "last_searched_at": row["started_at"] if item["status"] == "ok" else None,
        })
        if item.get("cooldown_until") and item["status"] == "pending":
            items[-1].update(cooldown_until=item["cooldown_until"],
                             cooldown_detail=item.get("cooldown_detail"),
                             cooldowns=int(item.get("cooldowns") or 0))
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
    counts = _counts(conn, run_id)
    # New postings already scored: the search board's progress while the run is running.
    counts["scored"] = sum(1 for r in top_rows if r["score"] is not None)
    return {
        "id": row["id"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "status": row["status"],
        "posting_age_days": row["posting_age_days"],
        "titles": json.loads(row["titles"]),
        "title_count": len(json.loads(row["titles"])),
        "counts": counts,
        "providers": items,
        "skipped": [i for i in items if i["status"] in ("skipped", "failed")],
        "top": top_rows[:top],
        "is_demo": bool(row["is_demo"]),
    }


def list_runs(conn: sqlite3.Connection, season: int | None = None) -> list[dict]:
    result = []
    where, params = _season_clause(conn, season)
    for row in conn.execute(f"SELECT * FROM search_runs{where}"
                            " ORDER BY started_at DESC, id DESC", params):
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
    source_site = record.get("source_site")
    if source_site is not None:
        if not isinstance(source_site, str) or not SITE_HOST.fullmatch(source_site.strip().lower()):
            _fail(f"{where}: 'source_site' must be the site's host, such as careers.example.com",
                  field="source_site")
        source_site = source_site.strip().lower()
    return {
        "source_site": source_site,
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
        "flags": [f.strip() for f in flags if not is_work_mode_not_stated(f)],
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


_NOT_STATED = re.compile(
    r"(?:work[ -]?mode|modality|modalidad(?: de trabajo)?)"
    r" (?:not stated|not specified|no indicada|no especificada)")


def is_work_mode_not_stated(flag: str) -> bool:
    """Whether a flag only says the work mode is not stated.

    The work-mode chip already shows that, so such a flag is neither stored nor
    shown. Only a whole-text match counts: a flag that says more stays.
    """
    plain = "".join(c for c in unicodedata.normalize("NFKD", flag)
                    if not unicodedata.combining(c))
    text = " ".join(plain.casefold().split()).strip(" .;:!")
    return bool(_NOT_STATED.fullmatch(text))


def shown_flags(stored: str) -> list[str]:
    """The stored flags the panel shows."""
    return [f for f in json.loads(stored) if not is_work_mode_not_stated(f)]


READING_FIELDS = ("work_mode", "work_mode_detail", "language", "flags", "published_salary")


def merge_readings(drafts: object, readings: object) -> list[dict]:
    """Drafts written by a provider's reader, completed with the agent's reading of
    each one (matched by the site's id). A reading sets only READING_FIELDS, so the
    captured text of a draft is stored exactly as the reader wrote it."""
    if not isinstance(drafts, list):
        _fail("expected the drafts file to hold a list of postings")
    if not isinstance(readings, list):
        _fail("expected the readings file to hold a list of readings")
    by_id: dict[str, dict] = {}
    for index, reading in enumerate(readings):
        where = f"reading {index + 1}"
        if not isinstance(reading, dict):
            _fail(f"{where}: must be an object")
        external_id = str(reading.get("external_id") or "").strip()
        if not external_id:
            _fail(f"{where}: 'external_id' is required", field="external_id")
        extra = sorted(set(reading) - {"external_id", *READING_FIELDS})
        if extra:
            _fail(f"{where}: a reading cannot set '{extra[0]}'; only "
                  f"{', '.join(READING_FIELDS)}", field=extra[0])
        if external_id in by_id:
            _fail(f"{where}: a second reading for {external_id}", field="external_id")
        by_id[external_id] = reading
    merged, missing, ids = [], [], set()
    for index, draft in enumerate(drafts):
        if not isinstance(draft, dict):
            _fail(f"posting {index + 1}: must be an object", index=index)
        external_id = str(draft.get("external_id") or "")
        ids.add(external_id)
        reading = by_id.get(external_id)
        if reading is None:
            missing.append(external_id)
            continue
        merged.append({**draft, **{key: reading[key] for key in READING_FIELDS if key in reading}})
    if missing:
        _fail(f"no reading for {', '.join(missing)}: give one for every draft", missing=missing)
    unknown = sorted(set(by_id) - ids)
    if unknown:
        _fail(f"readings for postings that are not in the drafts: {', '.join(unknown)}",
              unknown=unknown)
    return merged


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
                " captured_at, is_demo, source_site)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (item["provider"], item["external_id"], item["url"], url_key, item["title"],
                 item["company"], item["location"], item["country"], item["work_mode"],
                 item["work_mode_detail"], item["contract_type"], item["seniority"],
                 item["posted_at"],
                 item["description"],
                 json.dumps(item["published_salary"]) if item["published_salary"] else None,
                 item["language"], json.dumps(item["flags"], ensure_ascii=False),
                 normalize.match_key(item["company"], item["title"]), run_id, now,
                 run["is_demo"], item["source_site"]),
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
        if is_restored(conn, record["posting_id"]):
            raise JobTrackerError(
                "restored_by_user",
                f"{where}: the user restored posting {record['posting_id']} from the filtered-out"
                " list; it is never filtered again, only scored",
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


def is_restored(conn: sqlite3.Connection, posting_id: int) -> bool:
    """The user brought this posting back from the filtered-out list (for good)."""
    return conn.execute(
        "SELECT 1 FROM events WHERE entity_type = 'posting' AND entity_id = ?"
        " AND kind = 'filter_restored'", (str(posting_id),)).fetchone() is not None


def restore_filtered(conn: sqlite3.Connection, posting_ids: object) -> list[int]:
    """Bring filtered-out postings back to the results as new and unscored. Each keeps a
    `filter_restored` event with the run, reason, and detail it had: it marks the posting
    as restored for good (never filtered again) and is a correction of the filter."""
    if not isinstance(posting_ids, list) or not posting_ids or not all(
            isinstance(i, int) and not isinstance(i, bool) for i in posting_ids):
        raise JobTrackerError("invalid_ids", "expected a non-empty list of posting ids")
    rows = {}
    for posting_id in posting_ids:
        found = conn.execute(
            "SELECT id, run_id, reason, reason_detail FROM run_results"
            " WHERE posting_id = ? AND outcome = 'filtered' ORDER BY id", (posting_id,),
        ).fetchall()
        if not found:
            raise JobTrackerError("not_filtered", f"Posting {posting_id} is not filtered out")
        rows[posting_id] = found
    now = now_iso()
    for posting_id, found in rows.items():
        for row in found:
            conn.execute("UPDATE run_results SET outcome = 'new', reason = NULL,"
                         " reason_detail = NULL WHERE id = ?", (row["id"],))
        last = found[-1]
        conn.execute(
            "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
            " VALUES ('posting', ?, 'filter_restored', ?, ?)",
            (str(posting_id), json.dumps({"run_id": last["run_id"], "reason": last["reason"],
                                          "detail": last["reason_detail"]},
                                         ensure_ascii=False), now),
        )
    bump_changes(conn)
    return list(rows)


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
        "language": row["language"], "flags": shown_flags(row["flags"]),
        "source_site": row["source_site"],
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
        " EXISTS (SELECT 1 FROM run_results r JOIN search_runs sr ON sr.id = r.run_id"
        "         WHERE sr.group_id = (SELECT group_id FROM search_runs WHERE id = ?)"
        "         AND r.posting_id = p.id)"
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
                    restored=is_restored(conn, row["posting_id"]),
                    possible_duplicates=possible_duplicates(conn, row["posting_id"], run_id))
        result.append(item)
    return result
