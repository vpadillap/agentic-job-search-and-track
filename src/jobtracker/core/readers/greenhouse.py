"""Greenhouse reader: the reading part of providers/greenhouse.md.

Greenhouse has no public search across companies, but every company board has
a public Job Board API (no sign-in): https://boards-api.greenhouse.io/v1/boards/
<board>/jobs. The agent finds boards and postings for a title (the signed-in
MyGreenhouse search when the user is present, web search otherwise) and passes
their links with --found; this reader reads them, plus the boards remembered for
this user, keeps the postings for the title, the user's country, and the run's
window, and writes drafts with the complete description and the application-form
questions. Standard library only.
"""
from __future__ import annotations

import html
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import date
from pathlib import Path

from .. import db, providers
from ..errors import JobTrackerError
from ..paths import Paths
from . import common
from .glassdoor import plain_text

PROVIDER = "greenhouse"
LABEL = "Greenhouse"
API = "https://boards-api.greenhouse.io/v1/boards"
LINK = re.compile(
    r"^https?://(?:job-boards(?:\.eu)?|boards)\.greenhouse\.io/(?:embed/job_board\?for=)?"
    r"(?P<board>[A-Za-z0-9_-]+)(?:/jobs/(?P<job>\d+))?/?(?:[?#].*)?$")
REMOTE = ("remote", "remoto", "anywhere", "worldwide")
FAILURES_IN_A_ROW = 3
KINDS = {"input_text": "text", "textarea": "long_text", "input_file": "file",
         "multi_value_single_select": "choice", "multi_value_multi_select": "multi_choice"}
USER_AGENT = "jobtracker (local job-search assistant; Greenhouse Job Board API)"

# (status, body[, Retry-After]); the third item is optional.
Getter = Callable[[str], tuple]


def http_get(url: str) -> tuple[int, str, str | None]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return response.status, response.read().decode("utf-8"), None
    except urllib.error.HTTPError as error:
        return (error.code, error.read().decode("utf-8", "replace"),
                error.headers.get("Retry-After"))


# ── links, words, settings ────────────────────────────────────────────────

def parse_links(links: list[object]) -> tuple[list[tuple[str, str]], list[str], list[str]]:
    """(postings as (board, job id), boards, ignored) from the links the agent found."""
    postings: list[tuple[str, str]] = []
    boards: list[str] = []
    ignored: list[str] = []
    for link in links:
        match = LINK.match(str(link).strip()) if isinstance(link, str) else None
        if not match or match.group("board") in ("embed", "jobs"):
            ignored.append(str(link))
            continue
        board = match.group("board").lower()
        if match.group("job"):
            if (board, match.group("job")) not in postings:
                postings.append((board, match.group("job")))
        elif board not in boards:
            boards.append(board)
    return postings, boards, ignored


_words = common.words
title_matches = common.title_matches


def _split(words: str) -> list[str]:
    return [w.strip() for w in re.split(r"[;,]", words or "") if w.strip()]


def location_matches(texts: list[str], places: list[str], regions: list[str]) -> bool:
    """In the country (a place word), or remote for the country's region."""
    joined = " | ".join(" ".join(_words(t)) for t in texts if t)
    def has(word: str) -> bool:
        return re.search(rf"\b{re.escape(' '.join(_words(word)))}\b", joined) is not None
    if any(has(p) for p in places):
        return True
    return any(has(r) for r in REMOTE) and any(has(r) for r in regions)


def settings_path(paths: Paths) -> Path:
    return paths.home / "provider-settings" / f"{PROVIDER}.json"


def load_settings(paths: Paths) -> dict:
    path = settings_path(paths)
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    data.setdefault("boards", {})
    data.setdefault("countries", {})
    return data


def save_settings(paths: Paths, data: dict) -> None:
    path = settings_path(paths)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def country_words(paths: Paths, country: str | None, place_words: str | None,
                  settings: dict) -> tuple[list[str], list[str]]:
    """Place and region words for the country: the provider file's table, the user's
    saved words, or words the user gave now (saved for later)."""
    code = (country or "").upper()
    if not code:
        raise JobTrackerError("missing_country", "The profile has no country. Set it in /setup.")
    table = providers._countries_table(
        (providers.providers_dir() / f"{PROVIDER}.md").read_text(encoding="utf-8")) or {}
    row = table.get(code)
    if place_words:
        settings["countries"][code] = {"places": _split(place_words),
                                       "regions": _split(row[2]) if row and len(row) > 3 else []}
    saved = settings["countries"].get(code)
    if saved:
        return saved["places"], saved.get("regions") or []
    if row and len(row) >= 4:
        return _split(row[1]), _split(row[2])
    raise JobTrackerError(
        "missing_country", f"Greenhouse place words for {code} are not known yet. Ask the user "
        "which words mark a job as being in their country (the country's name in English and "
        "Spanish and its main cities), and pass them with --place-words \"Chile; Santiago; "
        "Valparaíso\" (they are saved, so this is asked once).", country=code)


# ── API data to drafts ────────────────────────────────────────────────────

def _question(item: dict) -> dict:
    fields = item.get("fields") or [{}]
    kind = KINDS.get(str(fields[0].get("type")), "text")
    values = fields[0].get("values") or []
    options = [str(v.get("label")) for v in values if isinstance(v, dict) and v.get("label")]
    return {"text": " ".join(str(item.get("label") or "").split()), "kind": kind,
            "options": options or None, "required": bool(item.get("required"))}


def form_questions(job: dict) -> list[dict]:
    items = list(job.get("questions") or []) + list(job.get("location_questions") or [])
    return [q for q in (_question(i) for i in items if isinstance(i, dict)) if q["text"]]


def posted_on(job: dict) -> str | None:
    value = str(job.get("first_published") or job.get("updated_at") or "")
    return value[:10] if re.match(r"\d{4}-\d{2}-\d{2}", value) else None


def _locations(job: dict) -> list[str]:
    texts = [str((job.get("location") or {}).get("name") or "")]
    texts += [str(o.get("name") or "") for o in job.get("offices") or [] if isinstance(o, dict)]
    return [t for t in texts if t]


def _draft(job: dict, board: str, ctx: common.Context) -> dict:
    return {
        "provider": PROVIDER, "external_id": str(job["id"]),
        "url": str(job.get("absolute_url") or f"https://job-boards.greenhouse.io/{board}/jobs/"
                                                f"{job['id']}"),
        "title": " ".join(str(job.get("title") or "").split()) or None,
        "company": " ".join(str(job.get("company_name") or "").split()) or board,
        "location": (job.get("location") or {}).get("name") or None, "country": ctx.country,
        "posted_at": posted_on(job),
        "description": plain_text(html.unescape(str(job.get("content") or ""))),
        "seniority": None, "contract_type": None, "form_questions": form_questions(job),
        # What the site states (hints for the agent's reading, never imported as they are):
        "site_language": job.get("language"),
        "site_departments": [d.get("name") for d in job.get("departments") or []
                             if isinstance(d, dict) and d.get("name")],
        "site_offices": [o.get("name") for o in job.get("offices") or []
                         if isinstance(o, dict) and o.get("name")],
        # The agent's reading (see providers/greenhouse.md):
        "work_mode": None, "work_mode_detail": None, "language": None, "flags": [],
        "published_salary": None,
    }


# ── the reader ────────────────────────────────────────────────────────────

def read(paths: Paths, run_id: int, title: str, location: str | None = None, *,
         found: str | None = None, place_words: str | None = None, get: Getter = http_get,
         clock: Callable[[], float] = time.time,
         sleep: Callable[[float], None] = time.sleep,
         rand: Callable[[], float] = random.random) -> dict:
    """Read the found postings and boards (and the remembered ones) for one title and
    write the drafts of its new postings. `location` is not used: Greenhouse postings
    are matched to the profile's country."""
    title = " ".join((title or "").split())
    if not title:
        raise JobTrackerError("invalid_title", "give the title to search with --title")
    links: list[object] = []
    if found:
        path = Path(found)
        if not path.is_file():
            raise JobTrackerError("not_found", f"There is no file at '{found}'")
        links = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(links, list):
            raise JobTrackerError("invalid_found", "--found must be a JSON list of links")
    with db.session(paths) as conn:
        ctx = common.context(conn, paths, run_id, PROVIDER, LABEL, now=clock())
    settings = load_settings(paths)
    places, regions = country_words(paths, ctx.country, place_words, settings)
    if place_words:
        save_settings(paths, settings)
    ctx.folder.mkdir(parents=True, exist_ok=True)
    lock = common.lock(ctx, LABEL, clock())
    try:
        return _read(paths, ctx, title, links, places, regions, settings, get, clock, sleep,
                     rand)
    finally:
        lock.unlink(missing_ok=True)


def _read(paths: Paths, ctx: common.Context, title: str, links: list[object],
          places: list[str], regions: list[str], settings: dict, get: Getter,
          clock: Callable[[], float], sleep: Callable[[float], None],
          rand: Callable[[], float]) -> dict:
    state = common.load_state(ctx)
    handled = set(state["job_ids"])
    postings, found_boards, ignored = parse_links(links)
    remembered = sorted(settings["boards"])
    boards = found_boards + [b for b in remembered if b not in found_boards]
    summary: dict = {"provider": PROVIDER, "title": title, "requests": 0,
                     "found_postings": len(postings), "boards": len(boards),
                     "boards_gone": [], "ignored_links": ignored, "cards": 0,
                     "outside_window": 0, "other_country": 0, "other_title": 0,
                     "duplicate_in_run": 0, "already_seen": 0, "new": 0, "capped": False,
                     "drafts_path": None, "stopped": None}
    drafts: list[dict] = []
    seen: list[dict] = []
    today = date.today().isoformat()
    failures = 0

    def fetch(url: str, capture: str) -> dict | None:
        """One API request, paced, saved, and repeated after a throttle; None for a 404."""
        return common.attempt(lambda: fetch_once(url, capture), state,
                              min_seconds=ctx.min_seconds, clock=clock, sleep=sleep, rand=rand)

    def fetch_once(url: str, capture: str) -> dict | None:
        nonlocal failures
        wait = state["last_request_at"] + ctx.min_seconds - clock()
        if state["last_request_at"] and wait > 0:
            sleep(wait)
        state["requests"] += 1
        summary["requests"] += 1
        rest: list = []
        try:
            status, body, *rest = get(url)
        except (OSError, ValueError) as error:
            status, body = None, str(error)
        state["last_request_at"] = clock()
        (ctx.folder / capture).write_text(body, encoding="utf-8")
        common.save_state(ctx, state)
        retry_after = common.parse_retry_after(rest[0] if rest else None, clock())
        if common.soft_status(status, retry_after):
            raise common.Throttle(f"{status} from {url}", retry_after)
        if status == 403:
            raise common.Stop("blocked", f"{status} from {url}")
        if status == 404:
            return None
        try:
            data = json.loads(body)
            if status != 200 or not isinstance(data, dict):
                raise ValueError(f"status {status}")
        except ValueError as error:
            failures += 1
            if failures >= FAILURES_IN_A_ROW:
                raise common.Stop("error", f"{FAILURES_IN_A_ROW} unreadable answers in a row "
                                  f"(last {url}: {error})") from error
            return None
        failures = 0
        return data

    def remember(board: str, company: str | None, via: str, matched: bool = True) -> None:
        item = settings["boards"].setdefault(board, {"company": company, "titles": [],
                                                     "found_via": via, "first_seen": today})
        item["company"] = company or item.get("company")
        item["last_checked"] = today
        if matched and title not in item["titles"]:
            item["titles"].append(title)

    def full() -> bool:
        if len(drafts) + len(seen) >= ctx.max_results:
            summary["capped"] = True
        return summary["capped"]

    def kept_elsewhere(job_id: str, posted: str | None) -> bool:
        """Already handled in this run, or stored by an earlier run (then seen)."""
        if job_id in handled:
            summary["duplicate_in_run"] += 1
            return True
        handled.add(job_id)
        state["job_ids"].append(job_id)
        if job_id in ctx.known:
            seen.append({"external_id": job_id, "posted_at": posted})
            return True
        return False

    def in_scope(job: dict) -> bool:
        if not location_matches(_locations(job), places, regions):
            summary["other_country"] += 1
            return False
        posted = posted_on(job)
        if posted and posted < ctx.since:
            summary["outside_window"] += 1
            return False
        return True

    def details(board: str, job_id: str) -> dict | None:
        return fetch(f"{API}/{board}/jobs/{job_id}?questions=true",
                     f"{PROVIDER}-{board}-{job_id}.json")

    try:
        # Postings from the signed-in search: Greenhouse matched the title already.
        for board, job_id in postings:
            if full():
                break
            summary["cards"] += 1
            if job_id in handled or job_id in ctx.known:
                kept_elsewhere(job_id, None)
                continue
            job = details(board, job_id)
            if job is None or not in_scope(job) or kept_elsewhere(job_id, posted_on(job)):
                continue
            drafts.append(_draft(job, board, ctx))
            remember(board, job.get("company_name"), "search")
        # Boards: found now or remembered; their postings are matched here.
        for board in boards:
            if summary["capped"]:
                break
            capture = ctx.folder / f"{PROVIDER}-board-{board}.json"
            if capture.is_file():                            # read earlier in this run
                listing = json.loads(capture.read_text(encoding="utf-8"))
            else:
                listing = fetch(f"{API}/{board}/jobs?content=true", capture.name)
            if listing is None:
                if board in settings["boards"]:
                    settings["boards"].pop(board)
                    summary["boards_gone"].append(board)
                continue
            jobs = [j for j in listing.get("jobs") or [] if isinstance(j, dict) and j.get("id")]
            kept_before = len(drafts) + len(seen)
            for job in jobs:
                if full():
                    break
                summary["cards"] += 1
                job_id = str(job["id"])
                if not title_matches(title, str(job.get("title") or "")):
                    summary["other_title"] += 1
                    continue
                if not in_scope(job) or kept_elsewhere(job_id, posted_on(job)):
                    continue
                detail = details(board, job_id)
                if detail is not None:
                    drafts.append(_draft(detail, board, ctx))
            matched = len(drafts) + len(seen) > kept_before
            if matched or board in settings["boards"]:
                company = next((j.get("company_name") for j in jobs if j.get("company_name")),
                               None)
                remember(board, company, "web search" if board in found_boards else "remembered",
                         matched)
    except common.Stop as stop:
        summary["stopped"] = common.stopped(stop)
    finally:
        save_settings(paths, settings)
    return common.finish(paths, ctx, state, summary, drafts, seen, None,
                         now=clock())
