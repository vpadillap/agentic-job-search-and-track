"""What every reader shares: the run's context, per-run state and pacing, one call at
a time, postings already stored, the drafts file, recording a stop, and the policy for
soft blocks (waiting, retrying, cooling down)."""
from __future__ import annotations

import email.utils
import json
import os
import random
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TypeVar

from .. import db, providers, search
from .. import profile as profile_service
from ..errors import JobTrackerError
from ..paths import Paths

MIN_SECONDS = 5          # a provider file may ask for more, never for less
STALE_LOCK_SECONDS = 30 * 60   # longer than any call: requests with pacing and timeouts

# The soft-block policy (providers/<id>.md, "Limits and etiquette").
SOFT_STATUSES = (429, 999)     # throttles; 503 is one only with a Retry-After header
ATTEMPTS = 3                   # tries of one request, the first included
MAX_WAIT = 120.0               # longest wait inside a call; a longer one is a cool-down
RUN_RETRIES = 6                # retries per provider per run
BACKOFF_BASE = 20.0            # seconds before the first retry (before jitter)
THROTTLE_LOG = 20              # throttles kept in the state file for the audit
CHALLENGE_TITLES = ("just a moment", "un momento", "security | glassdoor", "security check",
                    "verificación de seguridad", "verificacion de seguridad")

T = TypeVar("T")


class Stop(Exception):
    """Stop the provider: `blocked` or `error` for the rest of the run, or `throttled`
    for a cool-down after which the same run goes on."""

    def __init__(self, reason: str, detail: str, retry_after: float | None = None) -> None:
        super().__init__(detail)
        self.reason, self.detail, self.retry_after = reason, detail, retry_after


class Throttle(Exception):
    """A soft block (a throttle): wait and repeat the same request."""

    def __init__(self, detail: str, retry_after: float | None = None) -> None:
        super().__init__(detail)
        self.detail, self.retry_after = detail, retry_after


def parse_retry_after(value: object, now: float) -> float | None:
    """Seconds to wait from a Retry-After value (delta-seconds or an HTTP date)."""
    text = str(value or "").strip()
    if not text:
        return None
    if text.isdigit():
        return float(text)
    try:
        when = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, when.timestamp() - now)


def backoff(attempt_number: int, rand: Callable[[], float] = random.random) -> float:
    """Exponential backoff with equal jitter: 10-20 s, then 20-40 s, at most MAX_WAIT."""
    base = min(MAX_WAIT, BACKOFF_BASE * 2 ** (attempt_number - 1))
    return base / 2 + rand() * base / 2


def is_challenge(title: str | None) -> bool:
    """A security check that was not passed: a soft block."""
    return any(marker in (title or "").lower() for marker in CHALLENGE_TITLES)


def soft_status(status: int | None, retry_after: float | None = None) -> bool:
    return status in SOFT_STATUSES or (status == 503 and retry_after is not None)


def attempt(request: Callable[[], T], state: dict, *, min_seconds: float,
            clock: Callable[[], float], sleep: Callable[[float], None],
            rand: Callable[[], float] = random.random) -> T:
    """Run one request (with its checks), repeating it after a soft block: after the
    site's Retry-After, else after a backoff; never sooner than `min_seconds`. When the
    attempts or the run's retries are used up, or the site asks for more than MAX_WAIT,
    raise Stop("throttled") so that the caller ends the call with a cool-down."""
    state.setdefault("retries", 0)
    for number in range(1, ATTEMPTS + 1):
        try:
            return request()
        except Throttle as throttle:
            log = state.setdefault("throttles", [])
            log.append({"at": round(clock(), 1), "detail": throttle.detail,
                        "retry_after": throttle.retry_after})
            del log[:-THROTTLE_LOG]
            wait = throttle.retry_after if throttle.retry_after is not None \
                else backoff(number, rand)
            if number == ATTEMPTS or state["retries"] >= RUN_RETRIES or wait > MAX_WAIT:
                raise Stop("throttled", throttle.detail, throttle.retry_after) from None
            state["retries"] += 1
            sleep(max(wait, float(min_seconds)))
    raise AssertionError("unreachable")  # pragma: no cover


def stopped(stop: Stop) -> dict:
    """The summary's `stopped` entry for a stop."""
    return {"reason": stop.reason, "detail": stop.detail, "retry_after": stop.retry_after}


@dataclass
class Context:
    provider: str
    run_id: int
    folder: Path
    since: str           # oldest publication date inside the run's window
    days: int            # the run's window
    max_results: int     # per title, from the provider file
    min_seconds: int     # between requests or browser actions
    country: str | None  # the profile's ISO country
    known: set[str]      # this site's job ids stored by any run


def context(conn, paths: Paths, run_id: int, provider: str, label: str,
            now: float | None = None) -> Context:
    run = conn.execute("SELECT * FROM search_runs WHERE id = ?", (run_id,)).fetchone()
    if run is None:
        raise JobTrackerError("not_found", f"There is no search run {run_id}")
    if run["status"] != "running":
        raise JobTrackerError("run_finished", f"Run {run_id} is already finished")
    if run["is_demo"] or not run["capture_folder"]:
        raise JobTrackerError("invalid_run", f"Run {run_id} has no capture folder")
    item = next((p for p in json.loads(run["providers"]) if p["id"] == provider), None)
    if item is None:
        raise JobTrackerError("not_found", f"'{provider}' is not a job provider of run {run_id}")
    if item["status"] == "failed":
        raise JobTrackerError(
            "provider_stopped", f"{label} is stopped for run {run_id}: "
            f"{item.get('detail') or item.get('reason')}. Do not try it again in this run.")
    if item["status"] not in ("pending", "ok"):
        raise JobTrackerError(
            "provider_not_searched", f"{label} is {item['status']} in run {run_id}")
    now = datetime.now(UTC).timestamp() if now is None else now
    until = search.cooling_until(item, now)
    if until:
        left = max(1, round((datetime.fromisoformat(until.replace("Z", "+00:00")).timestamp()
                             - now) / 60))
        raise JobTrackerError(
            "provider_cooling", f"{label} is cooling down after a throttle until {until} "
            f"(about {left} min). Send no {label} request before then: go on with the other "
            "providers, then call it again in this run.", resume_after=until, minutes_left=left)
    meta = next((p for p in providers.list_providers() if p["id"] == provider), None)
    if meta is None or not meta.get("valid"):
        raise JobTrackerError("invalid_file", f"providers/{provider}.md is missing or invalid")
    started = datetime.fromisoformat(run["started_at"].replace("Z", "+00:00")).astimezone().date()
    days = int(run["posting_age_days"])
    active = profile_service.get_active(conn) or {}
    known = {row["external_id"] for row in conn.execute(
        "SELECT external_id FROM postings WHERE provider = ?", (provider,))}
    return Context(
        provider=provider, run_id=run_id, folder=paths.home / run["capture_folder"],
        since=(started - timedelta(days=days)).isoformat(), days=days,
        max_results=int(meta["max_results_per_query"]),
        min_seconds=max(MIN_SECONDS, int(meta["min_seconds_between_requests"])),
        country=active.get("country"), known=known,
    )


def load_state(ctx: Context) -> dict:
    path = ctx.folder / f"{ctx.provider}-state.json"
    state: dict = {"last_request_at": 0.0, "requests": 0, "job_ids": [], "drafts": [],
                   "titles": {}, "retries": 0, "throttles": []}
    if path.is_file():
        stored = json.loads(path.read_text(encoding="utf-8"))
        for old, new in (("last_page_at", "last_request_at"), ("pages", "requests"),
                         ("ids", "job_ids")):   # Bumeran's keys before the shared state
            if old in stored and new not in stored:
                stored[new] = stored.pop(old)
        state.update(stored)
    return state


def save_state(ctx: Context, state: dict) -> None:
    (ctx.folder / f"{ctx.provider}-state.json").write_text(json.dumps(state, indent=1),
                                                            encoding="utf-8")


def title_key(title: str, location: str | None = None) -> str:
    return f"{title} | {location}" if location else title


def progress(state: dict, key: str) -> dict:
    """A title's progress in this run: search pages read and whether it is done."""
    return state["titles"].setdefault(key, {"pages": 0, "done": False})


def already_done(ctx: Context, key: str) -> bool:
    return bool(load_state(ctx)["titles"].get(key, {}).get("done"))


def done_summary(provider: str, title: str) -> dict:
    """A title completed earlier in the run: nothing is requested again."""
    return {"provider": provider, "title": title, "already_done": True, "requests": 0,
            "new": 0, "already_seen": 0, "drafts_path": None, "stopped": None}


def lock(ctx: Context, label: str, now: float) -> Path:
    """One reader call at a time per run: parallel calls would share the pacing state
    and reach the site together. A lock older than any call can last is stale."""
    path = ctx.folder / f"{ctx.provider}.lock"
    for _ in range(2):
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                started = float(path.read_text(encoding="utf-8") or 0)
            except (OSError, ValueError):
                started = 0.0
            if now - started < STALE_LOCK_SECONDS:
                raise JobTrackerError(
                    "reader_busy", f"Another {label} read is running for this run. Read the "
                    "titles one at a time, never in parallel; wait for it to finish.",
                    lock=str(path)) from None
            path.unlink(missing_ok=True)
            continue
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            file.write(str(now))
        return path
    raise JobTrackerError("reader_busy", f"Another {label} read is running for this run.")


def seen_records(conn, provider: str, cards: list[dict]) -> list[dict]:
    """Postings stored by an earlier run, as import records, with this run's date."""
    records = []
    for card in cards:
        row = conn.execute("SELECT * FROM postings WHERE provider = ? AND external_id = ?",
                           (provider, card["external_id"])).fetchone()
        records.append({
            "provider": provider, "external_id": row["external_id"], "url": row["url"],
            "title": row["title"], "company": row["company"], "location": row["location"],
            "country": row["country"], "posted_at": card.get("posted_at") or row["posted_at"],
            "description": row["description"], "seniority": row["seniority"],
            "contract_type": row["contract_type"], "work_mode": row["work_mode"],
            "work_mode_detail": row["work_mode_detail"], "language": row["language"],
            "flags": json.loads(row["flags"]) if row["flags"] else [],
            "published_salary": json.loads(row["published_salary"])
            if row["published_salary"] else None,
        })
    return records


def finish(paths: Paths, ctx: Context, state: dict, summary: dict, drafts: list[dict],
           seen: list[dict], key: str | None = None, now: float | None = None) -> dict:
    """Write the drafts, record postings already stored as seen, mark the title done, and
    record a stop: a cool-down for a throttle, a failure for anything else."""
    if key is not None and not summary["stopped"]:
        progress(state, key)["done"] = True
    if drafts:
        name = f"{ctx.provider}-drafts-{len(state['drafts']) + 1}.json"
        (ctx.folder / name).write_text(json.dumps(drafts, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
        state["drafts"].append(name)
        summary["drafts_path"] = str(ctx.folder / name)
    save_state(ctx, state)
    summary["new"] = len(drafts)
    summary["already_seen"] = len(seen)
    with db.session(paths) as conn:
        if seen:
            search.import_postings(conn, ctx.run_id, seen_records(conn, ctx.provider, seen))
        stop = summary["stopped"]
        if stop and stop["reason"] == "throttled":
            when = datetime.now(UTC).timestamp() if now is None else now
            stop.update(search.record_cooldown(conn, ctx.run_id, ctx.provider,
                                               stop.get("retry_after"), stop["detail"], when))
        elif stop:
            search.record_provider(conn, ctx.run_id, ctx.provider, "failed",
                                   reason=stop["reason"], detail=stop["detail"])
    return summary


# ── title matching (readers whose site matches words anywhere in a posting) ──

FILLER_WORDS = {"senior", "sr", "junior", "jr", "semi", "mid", "lead", "principal", "staff",
                "i", "ii", "iii", "iv", "de", "of", "the", "and", "y", "en", "a"}


def words(text: str) -> list[str]:
    """Lowercase ASCII words: accents removed, split on anything else."""
    ascii_text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return [w for w in re.split(r"[^a-z0-9]+", ascii_text.lower()) if w]


def title_matches(searched: str, posting: str) -> bool:
    """Every word of the searched title is in the posting's title, seniority and filler
    words aside: "Senior Data Engineer" matches "Data Engineer II", not "Data Analyst"."""
    wanted = [w for w in words(searched) if w not in FILLER_WORDS]
    have = set(words(posting))
    return bool(wanted) and all(w in have for w in wanted)
