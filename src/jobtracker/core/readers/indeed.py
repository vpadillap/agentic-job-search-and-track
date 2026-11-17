"""Indeed reader: the browsing and extraction part of providers/indeed.md.

One call searches one title on the Indeed site of the profile's country in an
ordinary visible Chromium with a fresh profile (logged out by construction: no
cookies, no account). The postings come from the job-card data the search page
embeds; each new posting is clicked and its description copied from the side
panel. Posting pages (`/viewjob`) are never opened: they ask to sign in.
Pacing, the one-call lock, postings already stored, and stops are shared with
the other readers (`common`). What needs judgment is left to the agent.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from .. import db
from ..errors import JobTrackerError
from ..paths import Paths
from . import common

PROVIDER = "indeed"
LABEL = "Indeed"
FROMAGE = (1, 3, 7, 14)          # posting ages (days) Indeed's search offers
PAGE_STEP = 10                   # Indeed's `start` advances by 10
JOBCARDS = 'window.mosaic.providerData["mosaic-provider-jobcards"]'
BLOCK_MARKERS = ("Blocked", "Security Check", "Just a moment", "Verificación de seguridad")
SIGN_IN_MARKERS = ("Iniciar sesión", "Sign in", "Cuentas Indeed", "Indeed Accounts")
# Indeed's job types that say the contract type clearly; anything else is left to the agent.
CONTRACT_TYPES = {"tiempo completo": "full-time", "full-time": "full-time",
                  "medio tiempo": "part-time", "part-time": "part-time",
                  "contract": "contractor", "contractor": "contractor",
                  "freelance": "contractor", "independiente": "contractor"}
LOCALES = {"PE": "es-PE", "MX": "es-MX", "CO": "es-CO", "CL": "es-CL", "AR": "es-AR",
           "ES": "es-ES", "US": "en-US", "GB": "en-GB", "CA": "en-CA"}


class Browser(Protocol):
    def search(self, url: str) -> tuple[int | None, str, str]:
        """Open a search page: (HTTP status, page HTML, page title)."""

    def open(self, job_id: str) -> tuple[str | None, str]:
        """Click a posting on the current search page: (side-panel text, page title)."""

    def close(self) -> None: ...


# ── search parameters and parsing ─────────────────────────────────────────

def site(country: str | None) -> str:
    code = (country or "US").upper()
    return "www.indeed.com" if code == "US" else f"{code.lower()}.indeed.com"


def fromage(days: int) -> int:
    """The smallest posting age Indeed offers that covers `days` (14 at most)."""
    return next((value for value in FROMAGE if days <= value), FROMAGE[-1])


def search_url(host: str, title: str, location: str | None, days: int, start: int) -> str:
    query = {"q": title, "l": location, "fromage": fromage(days), "start": start or None}
    return f"https://{host}/jobs?" + urllib.parse.urlencode(
        {k: v for k, v in query.items() if v is not None})


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

class PlaywrightBrowser:
    """An ordinary visible Chromium with a fresh profile: no cookies, no account."""

    PANEL = ".simple-job-description-html"

    def __init__(self, locale: str) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise JobTrackerError(
                "missing_dependency", "Indeed needs Playwright: pip install playwright, then "
                "python -m playwright install chromium") from error
        self._playwright = sync_playwright().start()
        try:
            self._browser = self._playwright.chromium.launch(headless=False)
        except Exception as error:  # the browser itself is not installed
            self._playwright.stop()
            raise JobTrackerError(
                "missing_dependency", "Indeed needs Chromium for Playwright: "
                "python -m playwright install chromium") from error
        self._context = self._browser.new_context(locale=locale)
        self._page = self._context.new_page()
        self._last_panel = ""

    def search(self, url: str) -> tuple[int | None, str, str]:
        response = self._page.goto(url, wait_until="domcontentloaded", timeout=45000)
        self._page.wait_for_timeout(3000)  # a check, if any, completes by itself
        return (response.status if response else None, self._page.content(),
                self._page.title())

    def open(self, job_id: str) -> tuple[str | None, str]:
        link = self._page.locator(f'a.jcs-JobTitle[data-jk="{job_id}"]')
        if link.count() == 0:
            return None, self._page.title()
        link.first.click()
        panel = self._page.locator(self.PANEL)
        text = None
        for _ in range(20):  # up to 10 s for this posting's description
            self._page.wait_for_timeout(500)
            if f"vjk={job_id}" in self._page.url and panel.count():
                candidate = panel.first.inner_text()
                if candidate.strip() and candidate != self._last_panel:
                    text = candidate
                    break
        if text is not None:
            self._last_panel = text
        return text, self._page.title()

    def close(self) -> None:
        try:
            self._context.close()
            self._browser.close()
        finally:
            self._playwright.stop()


# ── the reader ────────────────────────────────────────────────────────────

BrowserFactory = Callable[[str], Browser]


def read(paths: Paths, run_id: int, title: str, location: str | None = None, *,
         browser: BrowserFactory = PlaywrightBrowser, clock: Callable[[], float] = time.time,
         sleep: Callable[[float], None] = time.sleep) -> dict:
    """Search one title and write the drafts of its new postings. Returns a summary."""
    title = " ".join((title or "").split())
    if not title:
        raise JobTrackerError("invalid_title", "give the title to search with --title")
    location = " ".join((location or "").split()) or None
    with db.session(paths) as conn:
        ctx = common.context(conn, paths, run_id, PROVIDER, LABEL)
    ctx.folder.mkdir(parents=True, exist_ok=True)
    lock = common.lock(ctx, LABEL, clock())
    try:
        return _read(paths, ctx, title, location, browser, clock, sleep)
    finally:
        lock.unlink(missing_ok=True)


def _blocked(status: int | None, title: str, url: str) -> None:
    if status in (403, 429) or any(marker in title for marker in BLOCK_MARKERS):
        raise common.Stop("blocked", f"{status} '{title}' on {url}")
    if any(marker in title for marker in SIGN_IN_MARKERS):
        raise common.Stop("blocked", f"a sign-in page ('{title}') instead of results on {url}")


def _read(paths: Paths, ctx: common.Context, title: str, location: str | None,
          browser_factory: BrowserFactory, clock: Callable[[], float],
          sleep: Callable[[float], None]) -> dict:
    state = common.load_state(ctx)
    handled = set(state["job_ids"])
    host = site(ctx.country)
    summary: dict = {"provider": PROVIDER, "title": title, "requests": 0, "pages": 0,
                     "cards": 0, "outside_window": 0, "duplicate_in_run": 0, "already_seen": 0,
                     "new": 0, "unreadable": [], "drafts_path": None, "stopped": None}
    drafts: list[dict] = []
    seen: list[dict] = []
    browser: Browser | None = None

    def pace() -> None:
        wait = state["last_request_at"] + ctx.min_seconds - clock()
        if state["last_request_at"] and wait > 0:
            sleep(wait)
        state["requests"] += 1
        summary["requests"] += 1

    def done(capture: str, suffix: str) -> None:
        state["last_request_at"] = clock()
        (ctx.folder / f"{PROVIDER}-{state['requests']}.{suffix}").write_text(
            capture, encoding="utf-8")
        common.save_state(ctx, state)

    def keep(job_id: str) -> None:
        handled.add(job_id)
        state["job_ids"].append(job_id)

    try:
        browser = browser_factory(LOCALES.get((ctx.country or "").upper(), "en-US"))
        start = 0
        while summary["cards"] < ctx.max_results:
            url = search_url(host, title, location, ctx.days, start)
            pace()
            try:
                status, html, page_title = browser.search(url)
            except Exception as error:  # the browser could not load the page
                raise common.Stop("error", f"the browser failed on {url}: {error}") from error
            finally:
                state["last_request_at"] = clock()
            done(html, "html")
            _blocked(status, page_title, url)
            summary["pages"] += 1
            cards = parse_cards(html)
            if cards is None:
                raise common.Stop("error", f"no job-card data on {url}: the page changed")
            if not any(c["external_id"] not in handled for c in cards):
                break  # no (more) new results for this title
            for card in cards:
                if summary["cards"] >= ctx.max_results:
                    break
                summary["cards"] += 1
                job_id = card["external_id"]
                if card["posted_at"] and card["posted_at"] < ctx.since:
                    summary["outside_window"] += 1
                elif job_id in handled:
                    summary["duplicate_in_run"] += 1
                elif job_id in ctx.known:
                    seen.append(card)
                    keep(job_id)
                else:
                    pace()
                    try:
                        text, page_title = browser.open(job_id)
                    except Exception as error:
                        raise common.Stop("error", f"the browser failed opening {job_id} on "
                                          f"{url}: {error}") from error
                    finally:
                        state["last_request_at"] = clock()
                    keep(job_id)
                    _blocked(None, page_title, url)
                    if not text or not text.strip():
                        done("", "txt")
                        raise common.Stop("error", f"no description panel for {job_id} on "
                                          f"{url}: the page changed")
                    description = plain_text(text)
                    done(description, "txt")
                    drafts.append(_draft(card, description, ctx, host))
            if len(cards) < PAGE_STEP:
                break  # a short page is the last one
            start += PAGE_STEP
    except common.Stop as stop:
        summary["stopped"] = {"reason": stop.reason, "detail": stop.detail}
    finally:
        if browser is not None:
            browser.close()
    return common.finish(paths, ctx, state, summary, drafts, seen)
