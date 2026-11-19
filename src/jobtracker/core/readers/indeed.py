"""Indeed reader: the browsing and extraction part of providers/indeed.md.

One call searches one title on the Indeed site of the profile's country with
headless Scrapling stealth sessions (logged out by construction: no cookies, no
account, no window). Logged out, Indeed serves only the first results page of a
search, so the reader loads the first page of several variants of the search
(relevance, date, last day, the other place, remote, last 3 days), each in a
fresh session, and clicks each new posting to copy its description from the side
panel. Posting pages (`/viewjob`) are never opened.
Pacing, the one-call lock, postings already stored, and stops are shared with
the other readers (`common`). What needs judgment is left to the agent.
"""
from __future__ import annotations

import json
import random
import re
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from .. import db
from ..errors import JobTrackerError
from ..paths import Paths
from . import common

PROVIDER = "indeed"
LABEL = "Indeed"
FROMAGE = (1, 3, 7, 14)          # posting ages (days) Indeed's search offers
EMPTY_VARIANTS_IN_A_ROW = 2      # variants adding nothing new: the title is done
INSTALL = "jt providers install indeed"
JOBCARDS = 'window.mosaic.providerData["mosaic-provider-jobcards"]'
# Security checks that do not clear are throttles (common.CHALLENGE_TITLES); these pages
# are hard blocks.
BLOCK_MARKERS = ("Blocked", "Attention Required", "Access denied")
SIGN_IN_MARKERS = ("Iniciar sesión", "Sign in", "Cuentas Indeed", "Indeed Accounts")
# Indeed's job types that say the contract type clearly; anything else is left to the agent.
CONTRACT_TYPES = {"tiempo completo": "full-time", "full-time": "full-time",
                  "medio tiempo": "part-time", "part-time": "part-time",
                  "contract": "contractor", "contractor": "contractor",
                  "freelance": "contractor", "independiente": "contractor"}
LOCALES = {"PE": "es-PE", "MX": "es-MX", "CO": "es-CO", "CL": "es-CL", "AR": "es-AR",
           "ES": "es-ES", "US": "en-US", "GB": "en-GB", "CA": "en-CA"}


class Browser(Protocol):
    def search(self, url: str, select: Callable[[str], list[str]]) -> SearchPage:
        """Load one first page in a fresh session, ask `select` which postings to open
        (given the page HTML), and click each one: the page and the panels' texts."""

    def close(self) -> None: ...


@dataclass
class SearchPage:
    status: int | None
    html: str
    title: str
    panels: dict[str, str | None] = field(default_factory=dict)   # job id -> description


# ── search parameters and parsing ─────────────────────────────────────────

def site(country: str | None) -> str:
    code = (country or "US").upper()
    return "www.indeed.com" if code == "US" else f"{code.lower()}.indeed.com"


def fromage(days: int) -> int:
    """The smallest posting age Indeed offers that covers `days` (14 at most)."""
    return next((value for value in FROMAGE if days <= value), FROMAGE[-1])


def search_url(host: str, title: str, location: str | None, days: int,
               sort: str | None = None) -> str:
    query = {"q": title, "l": location, "fromage": fromage(days), "sort": sort}
    return f"https://{host}/jobs?" + urllib.parse.urlencode(
        {k: v for k, v in query.items() if v is not None})


def variants(host: str, title: str, location: str | None, days: int) -> list[tuple[str, str]]:
    """First pages of the same search that Indeed answers logged out, in order: each
    one adds postings the others do not show (2026-11-18: about three times one page)."""
    window = fromage(days)
    found = [("relevance", search_url(host, title, location, days)),
             ("date", search_url(host, title, location, days, sort="date"))]
    if window > 1:
        found.append(("last day", search_url(host, title, location, 1)))
    if location:
        found.append(("whole country", search_url(host, title, None, days)))
    found.append(("remote", search_url(host, title, "remoto", days)))
    if window > 3:
        found.append(("last 3 days", search_url(host, title, location, 3)))
    return found


def site_total(html: str) -> int | None:
    """Indeed's own count of results for the search, from the page data."""
    match = re.search(r'"(?:totalJobCount|uniqueJobsCount)"\s*:\s*(\d+)', html or "")
    return int(match.group(1)) if match else None


def _salary_text(salary: dict | None) -> str | None:
    if not salary or not (salary.get("min") or salary.get("max")):
        return None
    low, high = salary.get("min"), salary.get("max")
    amount = f"{low}" if low == high or not high else f"{low}-{high}"
    return f"{amount} ({str(salary.get('type') or '').lower() or 'period not shown'})"


def parse_cards(html: str) -> list[dict] | None:
    """The postings of a search page from its embedded job-card data; None when the
    page has no such data (not a results page)."""
    start = html.find(JOBCARDS)
    if start < 0:
        return None
    brace = html.find("{", start)
    try:
        data, _ = json.JSONDecoder().raw_decode(html[brace:])
        results = data["metaData"]["mosaicProviderJobCardsModel"]["results"]
    except (ValueError, KeyError, TypeError):
        return None
    cards = []
    for item in results:
        job_id = item.get("jobkey")
        if not job_id:
            continue
        published = item.get("pubDate")
        cards.append({
            "external_id": str(job_id),
            "title": " ".join(str(item.get("title") or "").split()) or None,
            "company": " ".join(str(item.get("company") or "").split()) or None,
            "location": item.get("formattedLocation") or None,
            "posted_at": datetime.fromtimestamp(published / 1000).date().isoformat()
            if isinstance(published, int | float) else None,
            "job_types": [str(t) for t in item.get("jobTypes") or []],
            "remote_hint": bool(item.get("remoteLocation")),
            "salary_shown": _salary_text(item.get("extractedSalary")),
        })
    return cards


def plain_text(text: str) -> str:
    """Spaces collapsed within each line, at most one blank line in a row."""
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _contract(job_types: list[str]) -> str | None:
    found = {CONTRACT_TYPES[t.casefold()] for t in job_types if t.casefold() in CONTRACT_TYPES}
    return found.pop() if len(found) == 1 else None


def _draft(card: dict, description: str, ctx: common.Context, host: str) -> dict:
    return {
        "provider": PROVIDER, "external_id": card["external_id"],
        "url": f"https://{host}/viewjob?jk={card['external_id']}",
        "title": card["title"], "company": card["company"], "location": card["location"],
        "country": ctx.country, "posted_at": card["posted_at"], "description": description,
        "seniority": None, "contract_type": _contract(card["job_types"]),
        "job_types": card["job_types"], "remote_hint": card["remote_hint"],
        "salary_shown": card["salary_shown"],
        # The agent's reading (see providers/indeed.md):
        "work_mode": None, "work_mode_detail": None, "language": None, "flags": [],
        "published_salary": None,
    }


# ── the real browser ──────────────────────────────────────────────────────

class ScraplingBrowser:
    """Headless Scrapling stealth sessions: a fresh one for every first page, no
    cookies, no account, no window."""

    PANEL = ".simple-job-description-html"

    def __init__(self, locale: str, pause: float = common.MIN_SECONDS) -> None:
        try:
            from scrapling.fetchers import StealthySession
        except ImportError as error:
            raise JobTrackerError(
                "missing_dependency", f"Indeed needs Scrapling, which is not installed. Run: "
                f"{INSTALL}", tool="scrapling") from error
        import logging

        logging.getLogger("scrapling").setLevel(logging.WARNING)  # keep the output clean
        self._session_class = StealthySession
        self._locale = locale
        self._pause = pause

    def _panel_text(self, page, job_id: str, last: str) -> str | None:
        page.locator(f'a.jcs-JobTitle[data-jk="{job_id}"]').first.click()
        panel = page.locator(self.PANEL)
        for _ in range(20):  # up to 10 s for this posting's description
            page.wait_for_timeout(500)
            if f"vjk={job_id}" in page.url and panel.count():
                text = panel.first.inner_text()
                if text.strip() and text != last:
                    return text
        return None

    def search(self, url: str, select: Callable[[str], list[str]]) -> SearchPage:
        result = SearchPage(None, "", "")
        documents: list[int] = []

        def setup(page):
            page.on("response", lambda r: documents.append(r.status)
                    if r.request.resource_type == "document" and "/jobs" in r.url else None)
            return page

        def act(page):
            result.html, result.title = page.content(), page.title()
            last = ""
            for job_id in select(result.html):
                if page.locator(f'a.jcs-JobTitle[data-jk="{job_id}"]').count() == 0:
                    result.panels[job_id] = None
                    continue
                page.wait_for_timeout(int(self._pause * 1000))
                text = self._panel_text(page, job_id, last)
                result.panels[job_id] = text
                last = text or last
            return page

        try:
            session = self._session_class(headless=True, solve_cloudflare=True, retries=1,
                                          locale=self._locale, timeout=120000, wait=3000)
            session.__enter__()
        except Exception as error:  # the browser itself is not installed
            raise JobTrackerError(
                "missing_dependency", f"Scrapling's browser could not start ({error}). Run: "
                f"{INSTALL}", tool="scrapling") from error
        try:
            response = session.fetch(url, page_setup=setup, page_action=act)
            result.status = documents[-1] if documents else response.status
            if not result.html:
                result.html = response.html_content
        finally:
            session.__exit__(None, None, None)
        return result

    def close(self) -> None:
        return None


# ── the reader ────────────────────────────────────────────────────────────

BrowserFactory = Callable[[str], Browser]


def read(paths: Paths, run_id: int, title: str, location: str | None = None, *,
         browser: BrowserFactory = ScraplingBrowser, clock: Callable[[], float] = time.time,
         sleep: Callable[[float], None] = time.sleep,
         rand: Callable[[], float] = random.random) -> dict:
    """Search one title and write the drafts of its new postings. Returns a summary."""
    title = " ".join((title or "").split())
    if not title:
        raise JobTrackerError("invalid_title", "give the title to search with --title")
    location = " ".join((location or "").split()) or None
    with db.session(paths) as conn:
        ctx = common.context(conn, paths, run_id, PROVIDER, LABEL, now=clock())
    ctx.folder.mkdir(parents=True, exist_ok=True)
    lock = common.lock(ctx, LABEL, clock())
    try:
        if common.already_done(ctx, common.title_key(title, location)):
            return common.done_summary(PROVIDER, title)
        return _read(paths, ctx, title, location, browser, clock, sleep, rand)
    finally:
        lock.unlink(missing_ok=True)


def _blocked(status: int | None, title: str) -> tuple[bool, str] | None:
    """Why a page is not results, and whether it is a throttle (soft: 429, a security
    check that did not clear) rather than a hard block (403, a block page, a sign-in
    page); None when it is results."""
    if status == 403 or any(marker in title for marker in BLOCK_MARKERS):
        return False, f"{status} '{title}'"
    if any(marker in title for marker in SIGN_IN_MARKERS):
        return False, f"a sign-in page ('{title}') instead of results"
    if common.soft_status(status) or common.is_challenge(title):
        return True, f"{status} '{title}'"
    return None


def _read(paths: Paths, ctx: common.Context, title: str, location: str | None,
          browser_factory: BrowserFactory, clock: Callable[[], float],
          sleep: Callable[[float], None], rand: Callable[[], float]) -> dict:
    state = common.load_state(ctx)
    handled = set(state["job_ids"])
    host = site(ctx.country)
    summary: dict = {"provider": PROVIDER, "title": title, "requests": 0, "pages": 0,
                     "site_total": None, "variants": [], "ended_early": None, "cards": 0,
                     "outside_window": 0, "duplicate_in_run": 0, "already_seen": 0, "new": 0,
                     "capped": False, "unreadable": [], "drafts_path": None, "stopped": None,
                     "title_problem": None, "title_retries": 0}
    drafts: list[dict] = []
    seen: list[dict] = []
    in_title: set[str] = set()          # every job key met for this title
    browser: Browser | None = None
    missing = 0                         # chosen postings without a panel in a row

    def pace() -> None:
        wait = state["last_request_at"] + ctx.min_seconds - clock()
        if state["last_request_at"] and wait > 0:
            sleep(wait)
        state["requests"] += 1
        summary["requests"] += 1

    def keep(job_id: str) -> None:
        handled.add(job_id)
        state["job_ids"].append(job_id)

    try:
        browser = browser_factory(LOCALES.get((ctx.country or "").upper(), "en-US"))
        empty_in_a_row = 0
        for number, (name, url) in enumerate(variants(host, title, location, ctx.days)):
            if summary["capped"]:
                break
            chosen: dict[str, dict] = {}
            fresh: list[str] = []

            def select(html: str, chosen: dict[str, dict] = chosen,
                       fresh: list[str] = fresh) -> list[str]:
                cards = parse_cards(html) or []
                to_open = []
                for card in cards:
                    job_id = card["external_id"]
                    if job_id in in_title:
                        continue
                    in_title.add(job_id)
                    fresh.append(job_id)
                    summary["cards"] += 1
                    if len(drafts) + len(seen) + len(to_open) >= ctx.max_results:
                        summary["capped"] = True
                        break
                    if card["posted_at"] and card["posted_at"] < ctx.since:
                        summary["outside_window"] += 1
                    elif job_id in handled:
                        summary["duplicate_in_run"] += 1
                    elif job_id in ctx.known:
                        seen.append(card)
                        keep(job_id)
                    else:
                        chosen[job_id] = card
                        to_open.append(job_id)
                return to_open

            def once(url: str = url, select: Callable[[str], list[str]] = select,
                     first: bool = number == 0) -> SearchPage:
                assert browser is not None
                pace()
                try:
                    page = browser.search(url, select)
                except JobTrackerError:
                    raise
                except Exception as error:  # the browser could not load the page
                    raise common.Stop("error", f"the browser failed on {url}: "
                                      f"{error}") from error
                finally:
                    state["last_request_at"] = clock()
                summary["pages"] += 1
                (ctx.folder / f"{PROVIDER}-{state['requests']}.html").write_text(
                    page.html, encoding="utf-8")
                common.save_state(ctx, state)
                blocked = _blocked(page.status, page.title)
                if blocked and first:
                    soft, why = blocked
                    if soft:
                        raise common.Throttle(f"{why} on {url}")
                    raise common.Stop("blocked", f"{why} on {url}")
                return page

            def load(once: Callable[[], SearchPage] = once, url: str = url,
                     first: bool = number == 0) -> SearchPage:
                """The page; on the first variant, a page without job-card data is a
                title problem (retried once)."""
                page = common.attempt(once, state, min_seconds=ctx.min_seconds, clock=clock,
                                      sleep=sleep, rand=rand)
                if first and parse_cards(page.html) is None:
                    raise common.TitleProblem(
                        "no_card_data", f"no job-card data on {url}: the page may have "
                        "changed")
                return page

            page = common.retry_title(load, summary)
            blocked = _blocked(page.status, page.title)
            if blocked:   # later variants only: not a block, the title ends here
                summary["ended_early"] = f"{name}: {blocked[1]}"
                break
            if parse_cards(page.html) is None:   # later variants only
                summary["ended_early"] = f"{name}: no job-card data"
                break
            if summary["site_total"] is None:
                summary["site_total"] = site_total(page.html)
            added = 0
            for job_id, card in chosen.items():
                keep(job_id)
                text = page.panels.get(job_id)
                if not text or not text.strip():
                    summary["unreadable"].append(job_id)
                    missing += 1
                    if missing >= common.POSTING_PROBLEMS_IN_A_ROW:
                        raise common.TitleProblem(
                            "no_description", f"{missing} postings in a row without a "
                            f"description panel (last {job_id} on {url}): the page may have "
                            "changed")
                    continue
                missing = 0
                description = plain_text(text)
                (ctx.folder / f"{PROVIDER}-{state['requests']}-{job_id}.txt").write_text(
                    description, encoding="utf-8")
                drafts.append(_draft(card, description, ctx, host))
                added += 1
            summary["variants"].append({"variant": name, "cards": len(fresh), "new": added})
            empty_in_a_row = 0 if fresh else empty_in_a_row + 1
            if empty_in_a_row >= EMPTY_VARIANTS_IN_A_ROW:
                break
            total = summary["site_total"]
            if total is not None and len(in_title) >= total:
                break
    except common.TitleProblem as problem:
        common.title_problem(summary, problem)
    except common.Stop as stop:
        summary["stopped"] = common.stopped(stop)
    finally:
        if browser is not None:
            browser.close()
    return common.finish(paths, ctx, state, summary, drafts, seen,
                         common.title_key(title, location), now=clock())
