"""Get on Board reader: the reading part of providers/getonbrd.md.

Get on Board publishes a free public API (no key): GET https://www.getonbrd.com/api/v0/
search/jobs. Each answer carries every posting's complete description, date,
remote scope, salary range, and (expanded) company, seniority, and modality. Per
title the reader runs two searches: the profile's country (postings there and
remote postings open to it) and `remote=true` (remote from anywhere, which the
country filter leaves out); it keeps the postings whose title matches, inside the
run's window, and writes drafts. Standard library only.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import date, datetime

from .. import db
from ..errors import JobTrackerError
from ..paths import Paths
from . import common
from .glassdoor import plain_text

PROVIDER = "getonbrd"
LABEL = "Get on Board"
API = "https://www.getonbrd.com/api/v0/search/jobs"
PER_PAGE = 120
MAX_PAGES = 5                      # per search; the site rarely has more for one title
FAILURES_IN_A_ROW = 3
EXPAND = '["company","seniority","modality"]'
USER_AGENT = "jobtracker (local job-search assistant; Get on Board public API)"
SECTIONS = (("description_headline", "description"), (None, "projects"),
            ("functions_headline", "functions"), ("desirable_headline", "desirable"),
            ("benefits_headline", "benefits"))

Getter = Callable[[str], tuple[int, str]]


def http_get(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def search_url(title: str, *, country: str | None = None, remote: bool = False,
               page: int = 1) -> str:
    query: dict[str, object] = {"query": title, "per_page": PER_PAGE, "page": page,
                                "expand": EXPAND}
    if country:
        query["country_code"] = country.lower()
    if remote:
        query["remote"] = "true"
    return f"{API}?{urllib.parse.urlencode(query)}"


# ── API data to drafts ────────────────────────────────────────────────────

def _expanded_name(relation: object) -> str | None:
    data = relation.get("data") if isinstance(relation, dict) else None
    attributes = data.get("attributes") if isinstance(data, dict) else None
    name = attributes.get("name") if isinstance(attributes, dict) else None
    return " ".join(str(name).split()) or None if name else None


def description(attributes: dict) -> str:
    """The posting's sections in the site's order, each headline over its text."""
    parts = []
    for headline, body in SECTIONS:
        text = plain_text(str(attributes.get(body) or ""))
        if not text:
            continue
        title = " ".join(str(attributes.get(headline) or "").split()) if headline else ""
        parts.append(f"{title}\n{text}" if title else text)
    return "\n\n".join(parts)


def posted_on(attributes: dict) -> str | None:
    stamp = attributes.get("published_at")
    if isinstance(stamp, int | float) and not isinstance(stamp, bool):
        return datetime.fromtimestamp(stamp).date().isoformat()
    return None


def _salary(attributes: dict) -> dict | None:
    low, high = attributes.get("min_salary"), attributes.get("max_salary")
    if not low and not high:
        return None
    return {"min": low, "max": high, "currency": None,
            "note": "Get on Board does not state the currency in its data"}


def _draft(job: dict, ctx: common.Context) -> dict:
    a = job.get("attributes") or {}
    countries = [str(c) for c in a.get("countries") or [] if c]
    return {
        "provider": PROVIDER, "external_id": str(job["id"]),
        "url": str((job.get("links") or {}).get("public_url")
                   or f"https://www.getonbrd.com/jobs/{job['id']}"),
        "title": " ".join(str(a.get("title") or "").split()) or None,
        "company": _expanded_name(a.get("company")), "location": ", ".join(countries) or None,
        "country": ctx.country, "posted_at": posted_on(a), "description": description(a),
        "seniority": None, "contract_type": None,
        # What the site states (hints for the agent's reading, never imported as they are):
        "site_remote": a.get("remote_modality"), "site_seniority": _expanded_name(
            a.get("seniority")), "site_modality": _expanded_name(a.get("modality")),
        "site_salary": _salary(a), "site_perks": list(a.get("perks") or []),
        "site_category": a.get("category_name"),
        # The agent's reading (see providers/getonbrd.md):
        "work_mode": None, "work_mode_detail": None, "language": None, "flags": [],
        "published_salary": None,
    }


# ── the reader ────────────────────────────────────────────────────────────

def read(paths: Paths, run_id: int, title: str, location: str | None = None, *,
         get: Getter = http_get, clock: Callable[[], float] = time.time,
         sleep: Callable[[float], None] = time.sleep) -> dict:
    """Search one title (the profile's country and remote from anywhere) and write the
    drafts of its new postings. `location` is not used: the API filters by country."""
    title = " ".join((title or "").split())
    if not title:
        raise JobTrackerError("invalid_title", "give the title to search with --title")
    with db.session(paths) as conn:
        ctx = common.context(conn, paths, run_id, PROVIDER, LABEL)
    ctx.folder.mkdir(parents=True, exist_ok=True)
    lock = common.lock(ctx, LABEL, clock())
    try:
        return _read(paths, ctx, title, get, clock, sleep)
    finally:
        lock.unlink(missing_ok=True)


def _read(paths: Paths, ctx: common.Context, title: str, get: Getter,
          clock: Callable[[], float], sleep: Callable[[float], None]) -> dict:
    state = common.load_state(ctx)
    handled = set(state["job_ids"])
    summary: dict = {"provider": PROVIDER, "title": title, "requests": 0, "searches": [],
                     "cards": 0, "other_title": 0, "outside_window": 0,
                     "duplicate_in_run": 0, "already_seen": 0, "new": 0, "capped": False,
                     "drafts_path": None, "stopped": None, "note": None}
    drafts: list[dict] = []
    seen: list[dict] = []
    failures = 0
    since = date.fromisoformat(ctx.since)

    def fetch(url: str) -> dict | None:
        nonlocal failures
        wait = state["last_request_at"] + ctx.min_seconds - clock()
        if state["last_request_at"] and wait > 0:
            sleep(wait)
        state["requests"] += 1
        summary["requests"] += 1
        try:
            status, body = get(url)
        except (OSError, ValueError) as error:
            status, body = None, str(error)
        state["last_request_at"] = clock()
        (ctx.folder / f"{PROVIDER}-{state['requests']}.json").write_text(body, encoding="utf-8")
        common.save_state(ctx, state)
        if status in (403, 429):
            raise common.Stop("blocked", f"{status} from {url}")
        try:
            data = json.loads(body)
            if status != 200 or not isinstance(data, dict) or not isinstance(data.get("data"),
                                                                            list):
                raise ValueError(f"status {status}")
        except ValueError as error:
            failures += 1
            if failures >= FAILURES_IN_A_ROW:
                raise common.Stop("error", f"{FAILURES_IN_A_ROW} unreadable answers in a row "
                                  f"(last {url}: {error})") from error
            return None
        failures = 0
        return data

    searches = []
    if ctx.country:
        searches.append(("country", {"country": ctx.country}))
    else:
        summary["note"] = ("the profile has no country: only postings remote from anywhere "
                           "were searched")
    searches.append(("remote", {"remote": True}))

    try:
        for label, options in searches:
            added = 0
            for page in range(1, MAX_PAGES + 1):
                data = fetch(search_url(title, page=page, **options))
                if data is None:
                    break
                for job in data["data"]:
                    if len(drafts) + len(seen) >= ctx.max_results:
                        summary["capped"] = True
                        break
                    if not isinstance(job, dict) or not job.get("id"):
                        continue
                    attributes = job.get("attributes") or {}
                    job_id = str(job["id"])
                    summary["cards"] += 1
                    if not common.title_matches(title, str(attributes.get("title") or "")):
                        summary["other_title"] += 1
                        continue
                    posted = posted_on(attributes)
                    if posted and date.fromisoformat(posted) < since:
                        summary["outside_window"] += 1
                        continue
                    if job_id in handled:
                        summary["duplicate_in_run"] += 1
                        continue
                    handled.add(job_id)
                    state["job_ids"].append(job_id)
                    if job_id in ctx.known:
                        seen.append({"external_id": job_id, "posted_at": posted})
                        continue
                    drafts.append(_draft(job, ctx))
                    added += 1
                total_pages = int((data.get("meta") or {}).get("total_pages") or 1)
                if summary["capped"] or page >= total_pages:
                    break
            summary["searches"].append({"search": label, "new": added})
            if summary["capped"]:
                break
    except common.Stop as stop:
        summary["stopped"] = {"reason": stop.reason, "detail": stop.detail}
    return common.finish(paths, ctx, state, summary, drafts, seen)
