"""Bumeran Perú reader: the browsing and extraction part of providers/bumeran.md.

Bumeran's pages are a JavaScript application whose data comes from the site's
own API, which Cloudflare refuses to anything but a real browser. One call
opens, in a headless Scrapling stealth session without an account or saved
cookies (no window), the
public search page for one title and posting age, then the public page of each
new posting, and keeps the JSON those pages receive from the site. The reader
never calls the API itself, never clicks, and cancels any application request.
Pacing, the page limit, and the stop conditions of the provider file are
applied here, also across calls of the same run. What needs judgment (work
mode and its detail, language, flags, a stated salary) is left to the agent.
"""
from __future__ import annotations

import json
import random
import re
import time
import unicodedata
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser

from .. import db
from ..errors import JobTrackerError
from ..paths import Paths
from . import common
from .linkedin import plain_text

PROVIDER = "bumeran"
BASE_URL = "https://www.bumeran.com.pe"
SEARCH_PATH = "/empleos-{window}busqueda-{slug}.html"
POSTING_PATH = "/empleos/{id}.html"
SEARCH_API = "api/avisos/searchV2"
POSTING_API = "api/candidates/fichaAvisoNormalizada/"
COUNTRY = "PE"
LOCALE = "es-PE"
VIEWPORT = {"width": 1366, "height": 900}
PAGE_SIZE = 20           # list entries per results page
RESPONSE_TIMEOUT = 30.0  # seconds a page has to receive its data
# Posting-age windows the site offers (days covered, URL part).
WINDOWS = ((2, "publicacion-menor-a-2-dias"), (3, "publicacion-menor-a-3-dias"),
           (4, "publicacion-menor-a-4-dias"), (5, "publicacion-menor-a-5-dias"),
           (6, "publicacion-menor-a-6-dias"), (7, "publicacion-menor-a-7-dias"),
           (15, "publicacion-menor-a-15-dias"), (30, "publicacion-menor-a-1-mes"))
CONTRACT_TYPES = {"full-time": "full-time", "part-time": "part-time"}
WORK_MODES = {"presencial": "onsite", "hibrido": "hybrid", "remoto": "remote"}
BLOCK_TITLES = ("attention required", "just a moment", "access denied")
SKIPPED_RESOURCES = ("image", "font", "media")
LOCK_FILE = "bumeran.lock"
INSTALL = "jt providers install bumeran"


# ── the browser ───────────────────────────────────────────────────────────

@dataclass
class Page:
    """What one page load gave: the document's answer and the site data it received."""
    status: int | None
    title: str
    url: str
    responses: list[dict] = field(default_factory=list)   # {url, status, body[, retry_after]}
    retry_after: str | None = None                        # the document's Retry-After


Open = Callable[[str, tuple[str, ...]], Page]


def _route(route) -> None:
    request = route.request
    if request.resource_type in SKIPPED_RESOURCES or "postular" in request.url.lower():
        route.abort()
    else:
        route.continue_()


@contextmanager
def scrapling_browser() -> Iterator[Open]:
    """A headless Scrapling stealth session: no account, no saved cookies, no window.
    Yields `open(url, watch)`: load one public page and keep the site data it receives."""
    try:
        from scrapling.fetchers import StealthySession
    except ImportError as error:
        raise JobTrackerError(
            "missing_dependency", f"Bumeran needs Scrapling, which is not installed. Run: "
            f"{INSTALL}", tool="scrapling") from error
    import logging

    logging.getLogger("scrapling").setLevel(logging.WARNING)  # keep the CLI output clean
    try:
        session = StealthySession(headless=True, solve_cloudflare=True, locale=LOCALE, retries=1,
                                  timeout=int(RESPONSE_TIMEOUT * 3000), wait=0)
        session.__enter__()
    except Exception as error:  # the browser itself is not installed
        raise JobTrackerError(
            "missing_dependency", f"Scrapling's browser could not start ({error}). Run: "
            f"{INSTALL}", tool="scrapling") from error

    def open_page(url: str, watch: tuple[str, ...]) -> Page:
        captured: list[dict] = []
        seen_title = {"value": ""}

        def on_response(response) -> None:
            if any(part in response.url for part in watch):
                try:
                    body = response.json()
                except Exception:  # not JSON: kept as missing
                    body = None
                captured.append({"url": response.url, "status": response.status,
                                 "body": body,
                                 "retry_after": (response.headers or {}).get("retry-after")})

        def setup(page):
            page.set_viewport_size(VIEWPORT)
            page.route("**/*", _route)
            page.on("response", on_response)
            return page

        def settle(page):
            deadline = time.monotonic() + RESPONSE_TIMEOUT
            while not captured and time.monotonic() < deadline:
                if any(t in page.title().lower() for t in BLOCK_TITLES):
                    break
                page.wait_for_timeout(500)
            page.wait_for_timeout(1000)
            seen_title["value"] = page.title()
            return page

        try:
            answer = session.fetch(url, page_setup=setup, page_action=settle)
        except Exception as error:
            raise _Stop("error", f"the browser could not load {url}: {error}") from error
        headers = getattr(answer, "headers", None) or {}
        return Page(status=answer.status, title=seen_title["value"],
                    url=str(getattr(answer, "url", url) or url), responses=captured,
                    retry_after=headers.get("retry-after") or headers.get("Retry-After"))

    try:
        yield open_page
    finally:
        session.__exit__(None, None, None)


# ── URLs and values ───────────────────────────────────────────────────────

def slug(title: str) -> str:
    """'Analista de Datos Sr.' -> 'analista-de-datos-sr'."""
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def window(days: int) -> str | None:
    """The smallest posting-age window the site offers that covers `days` (None above 30)."""
    for limit, value in WINDOWS:
        if days <= limit:
            return value
    return None


def search_url(title: str, days: int, page: int = 1) -> str:
    part = window(days)
    url = BASE_URL + SEARCH_PATH.format(window=f"{part}-" if part else "", slug=slug(title))
    return url if page == 1 else f"{url}?page={page}"


def _date(value: str | None) -> str | None:
    """'16-11-2026' (day first) -> '2026-11-16'."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip()[:10], "%d-%m-%Y").date().isoformat()
    except ValueError:
        return None


def _key(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return text.strip().lower()


def _name(value: object) -> str | None:
    if isinstance(value, dict):
        value = value.get("nombre")
    return str(value).strip() if value else None


class _Text(HTMLParser):
    """Plain text of a description: paragraphs and line breaks kept, list items as "• "."""

    BLOCKS = {"p", "div", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n• ")
        elif tag in self.BLOCKS:
            self.parts.append("\n\n")

    def handle_endtag(self, tag) -> None:
        if tag in self.BLOCKS or tag == "li":
            self.parts.append("\n")

    def handle_data(self, data) -> None:
        self.parts.append(data)


def description_text(markup: str | None) -> str:
    parser = _Text()
    parser.feed(markup or "")
    parser.close()
    return plain_text("".join(parser.parts))


def questions(raw: object) -> tuple[list[dict], int]:
    """Form questions in the import shape, and how many had an unknown shape. The
    answer the employer expects (`indiceCorrecta`) is never kept."""
    result, unknown = [], 0
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict) or not item:
            continue
        kind, data = next(iter(item.items()))
        data = data if isinstance(data, dict) else {}
        text = " ".join(str(data.get("texto") or "").split())
        if not text:
            unknown += 1
            continue
        if kind == "choice":
            options = [" ".join(str(o.get("opcion") or "").split())
                       for o in data.get("opciones") or [] if isinstance(o, dict)]
            result.append({"text": text, "kind": "choice",
                           "options": [o for o in options if o]})
        else:
            if kind != "simple":
                unknown += 1
            result.append({"text": text, "kind": "text"})
    return result, unknown


_Stop = common.Stop
LABEL = "Bumeran"
HARD_TITLES = ("attention required", "access denied")


def _check(page: Page, url: str) -> None:
    """The provider file's stop conditions for one page load: a throttle (429, a
    challenge page that was not passed) is waited out; a block (403, a block page)
    stops Bumeran for the run."""
    title = (page.title or "").lower()
    if page.status == 403 or any(t in title for t in HARD_TITLES):
        raise _Stop("blocked", f"{page.status} on {url} ({page.title or 'no title'})")
    if page.status == 429 or common.is_challenge(title):
        raise common.Throttle(f"{page.status} on {url} ({page.title or 'no title'})",
                              common.parse_retry_after(page.retry_after, time.time()))
    for response in page.responses:
        if response["status"] == 403:
            raise _Stop("blocked", f"403 on the site data for {url}")
        if response["status"] == 429:
            raise common.Throttle(f"429 on the site data for {url}", common.parse_retry_after(
                response.get("retry_after"), time.time()))


def _data(page: Page, part: str, url: str) -> dict:
    for response in page.responses:
        if part in response["url"] and response["status"] == 200 \
                and isinstance(response["body"], dict):
            return response["body"]
    raise _Stop("error", f"{url} sent no readable data ({part}) within "
                f"{int(RESPONSE_TIMEOUT)} s: the site may have changed")


# ── records ───────────────────────────────────────────────────────────────

def _draft(entry: dict, posting: dict) -> tuple[dict, int]:
    company = posting.get("empresa") or {}
    hidden = bool(company.get("confidencial") or entry.get("confidencial"))
    work = _name(posting.get("modalidadTrabajo")) or entry.get("modalidadTrabajo")
    job_type = _name(posting.get("tipoTrabajo")) or entry.get("tipoTrabajo")
    seniority = _name(posting.get("nivelLaboral"))
    salary = ((posting.get("requisitos") or {}).get("salario")) or {}
    asked, unknown = questions(posting.get("preguntas"))
    link = posting.get("seoFriendlyUrl") or POSTING_PATH.format(id=entry["id"])
    site_salary = {"min": salary.get("salarioMinimo"), "max": salary.get("salarioMaximo"),
                   "frequency": salary.get("frecuenciaPago"), "type": salary.get("tipo")} \
        if salary.get("salarioMinimo") or salary.get("salarioMaximo") else None
    draft = {
        "provider": PROVIDER, "external_id": str(entry["id"]), "url": BASE_URL + link,
        "title": posting.get("titulo") or entry.get("titulo"),
        "company": "Confidencial" if hidden
        else (company.get("denominacion") or entry.get("empresa")),
        "location": entry.get("localizacion"), "country": COUNTRY,
        "posted_at": _date(posting.get("fechaPublicacion") or entry.get("fechaPublicacion")),
        "description": description_text(posting.get("descripcion")),
        "seniority": None if _key(seniority) in ("", "otro") else seniority,
        "contract_type": CONTRACT_TYPES.get(_key(job_type)),
        "form_questions": asked,
        # Hints for the agent's reading (ignored by the import):
        "site_work_mode": WORK_MODES.get(_key(work)), "site_work_mode_text": work,
        "site_contract": {"type": job_type,
                          "hiring": _name(posting.get("tipoContratacion"))},
        "site_salary": site_salary,
        "asks_expected_salary": bool(salary.get("solicitarCandidato")),
        "closing_date": _date(posting.get("fechaFinalizacion")),
        # The agent's reading (see providers/bumeran.md):
        "work_mode": None, "work_mode_detail": None, "language": None, "flags": [],
        "published_salary": None,
    }
    return draft, unknown


# ── the reader ────────────────────────────────────────────────────────────

def read(paths: Paths, run_id: int, title: str, location: str | None = None, *,
         browser: Callable = scrapling_browser, clock: Callable[[], float] = time.time,
         sleep: Callable[[float], None] = time.sleep,
         rand: Callable[[], float] = random.random) -> dict:
    """Search one title and write the drafts of its new postings. Returns a summary.
    `location` is accepted for the common reader interface and not used."""
    title = " ".join((title or "").split())
    if not title or not slug(title):
        raise JobTrackerError("invalid_title", "give the title to search with --title")
    with db.session(paths) as conn:
        ctx = common.context(conn, paths, run_id, PROVIDER, LABEL, now=clock())
    ctx.folder.mkdir(parents=True, exist_ok=True)
    lock = common.lock(ctx, LABEL, clock())
    try:
        if common.already_done(ctx, title):   # before any browser starts
            return common.done_summary(PROVIDER, title)
        with browser() as open_page:   # a missing browser stops here, before any page
            return _read(paths, ctx, title, open_page, clock, sleep, rand)
    finally:
        lock.unlink(missing_ok=True)


def _read(paths: Paths, ctx: common.Context, title: str, open_page: Open,
          clock: Callable[[], float], sleep: Callable[[float], None],
          rand: Callable[[], float]) -> dict:
    state = common.load_state(ctx)
    handled = set(state["job_ids"])
    done_pages = common.progress(state, title)["pages"]
    max_pages = max(1, ctx.max_results // PAGE_SIZE)
    summary: dict = {"provider": PROVIDER, "title": title, "requests": 0, "pages": 0,
                     "cards": 0, "outside_window": 0, "duplicate_in_run": 0, "already_seen": 0,
                     "new": 0, "unreadable": [], "unknown_questions": 0, "drafts_path": None,
                     "stopped": None}
    drafts: list[dict] = []
    seen: list[dict] = []

    def load_once(url: str, watch: str) -> Page:
        wait = state["last_request_at"] + ctx.min_seconds - clock()
        if state["last_request_at"] and wait > 0:
            sleep(wait)
        state["requests"] += 1
        summary["requests"] += 1
        try:
            page = open_page(url, (watch,))
        finally:
            state["last_request_at"] = clock()
            common.save_state(ctx, state)
        (ctx.folder / f"{PROVIDER}-{state['requests']}.json").write_text(json.dumps(
            {"url": url, "status": page.status, "title": page.title, "final_url": page.url,
             "responses": page.responses}, ensure_ascii=False, indent=1), encoding="utf-8")
        _check(page, url)
        return page

    def load(url: str, watch: str) -> Page:
        return common.attempt(lambda: load_once(url, watch), state,
                              min_seconds=ctx.min_seconds, clock=clock, sleep=sleep, rand=rand)

    def keep(posting_id: str) -> None:
        handled.add(posting_id)
        state["job_ids"].append(posting_id)

    try:
        for number in range(done_pages + 1, max_pages + 1):
            url = search_url(title, ctx.days, number)
            found = _data(load(url, SEARCH_API), SEARCH_API, url)
            entries = found.get("content")
            if not isinstance(entries, list) or found.get("number") not in (None, number - 1):
                raise _Stop("error", f"{url} did not give results page {number}: the site "
                            "may have changed")
            summary["pages"] += 1
            for entry in entries:
                if not isinstance(entry, dict) or "id" not in entry:
                    raise _Stop("error", f"a result without an id on {url}")
                summary["cards"] += 1
                posting_id = str(entry["id"])
                posted = _date(entry.get("fechaPublicacion"))
                if posted and posted < ctx.since:
                    summary["outside_window"] += 1
                elif posting_id in handled:
                    summary["duplicate_in_run"] += 1
                elif posting_id in ctx.known:
                    seen.append({"external_id": posting_id, "posted_at": posted})
                    keep(posting_id)
                else:
                    posting_url = BASE_URL + POSTING_PATH.format(id=posting_id)
                    page = load(posting_url, POSTING_API + posting_id)
                    keep(posting_id)   # only now: a throttled posting is opened later
                    posting = _data(page, POSTING_API + posting_id, posting_url).get("aviso")
                    if not isinstance(posting, dict):
                        raise _Stop("error", f"no posting data on {posting_url}")
                    if _key(posting.get("estado")) not in ("", "activo"):
                        summary["unreadable"].append({
                            "external_id": posting_id, "url": posting_url,
                            "reason": f"the posting is {posting.get('estado')}"})
                        continue
                    draft, unknown = _draft(entry, posting)
                    if not draft["description"]:
                        summary["unreadable"].append({"external_id": posting_id,
                                                      "url": posting_url,
                                                      "reason": "no description"})
                        continue
                    summary["unknown_questions"] += unknown
                    drafts.append(draft)
            common.progress(state, title)["pages"] = number
            if len(entries) < PAGE_SIZE or number * PAGE_SIZE >= int(found.get("total") or 0):
                break
    except _Stop as stop:
        summary["stopped"] = common.stopped(stop)
    return common.finish(paths, ctx, state, summary, drafts, seen, title, now=clock())
