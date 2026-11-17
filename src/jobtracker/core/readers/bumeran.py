"""Bumeran Perú reader: the browsing and extraction part of providers/bumeran.md.

Bumeran's pages are a JavaScript application whose data comes from the site's
own API, which Cloudflare refuses to anything but a real browser. One call
opens, in a real Chromium window without an account or saved cookies, the
public search page for one title and posting age, then the public page of each
new posting, and keeps the JSON those pages receive from the site. The reader
never calls the API itself, never clicks, and cancels any application request.
Pacing, the page limit, and the stop conditions of the provider file are
applied here, also across calls of the same run. What needs judgment (work
mode and its detail, language, flags, a stated salary) is left to the agent.
"""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path

from .. import db, providers, search
from ..errors import JobTrackerError
from ..paths import Paths
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
MIN_SECONDS = 5          # the provider file may ask for more, never for less
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
BLOCK_STATUSES = (403, 429)
SKIPPED_RESOURCES = ("image", "font", "media")
STATE_FILE = "bumeran-state.json"
LOCK_FILE = "bumeran.lock"
STALE_LOCK_SECONDS = 30 * 60
INSTALL_PACKAGE = "pip install playwright (or: uv sync --extra browser)"
INSTALL_BROWSER = "python -m playwright install chromium"


# ── the browser ───────────────────────────────────────────────────────────

@dataclass
class Page:
    """What one page load gave: the document's answer and the site data it received."""
    status: int | None
    title: str
    url: str
    responses: list[dict] = field(default_factory=list)   # {url, status, body}


Open = Callable[[str, tuple[str, ...]], Page]


def _route(route) -> None:
    request = route.request
    if request.resource_type in SKIPPED_RESOURCES or "postular" in request.url.lower():
        route.abort()
    else:
        route.continue_()


@contextmanager
def playwright_browser() -> Iterator[Open]:
    """A visible Chromium window with a fresh context: no account, no saved cookies,
    nothing edited about the browser. Yields `open(url, watch)`."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise JobTrackerError(
            "missing_dependency",
            f"Bumeran needs the Playwright package, which is not installed. {INSTALL_PACKAGE}, "
            f"then: {INSTALL_BROWSER}", tool="playwright") from error
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=False)
        except PlaywrightError as error:
            raise JobTrackerError(
                "missing_dependency",
                f"Bumeran needs Playwright's Chromium, which could not start ({error}). "
                f"Install it with: {INSTALL_BROWSER}", tool="chromium") from error
        try:
            context = browser.new_context(locale=LOCALE, viewport=VIEWPORT)
            context.route("**/*", _route)
            tab = context.new_page()

            def open_page(url: str, watch: tuple[str, ...]) -> Page:
                captured: list[dict] = []

                def on_response(response) -> None:
                    if any(part in response.url for part in watch):
                        try:
                            body = response.json()
                        except Exception:  # not JSON: kept as missing
                            body = None
                        captured.append({"url": response.url, "status": response.status,
                                         "body": body})

                tab.on("response", on_response)
                try:
                    answer = tab.goto(url, wait_until="domcontentloaded",
                                      timeout=RESPONSE_TIMEOUT * 1000)
                    deadline = time.monotonic() + RESPONSE_TIMEOUT
                    while not captured and time.monotonic() < deadline:
                        if any(t in tab.title().lower() for t in BLOCK_TITLES):
                            break
                        tab.wait_for_timeout(500)
                    tab.wait_for_timeout(1000)
                    return Page(status=answer.status if answer else None, title=tab.title(),
                                url=tab.url, responses=captured)
                except PlaywrightError as error:
                    raise _Stop("error", f"the browser could not load {url}: {error}") from error
                finally:
                    tab.remove_listener("response", on_response)

            yield open_page
        finally:
            browser.close()


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


# ── run context, state, lock ──────────────────────────────────────────────

@dataclass
class _Context:
    run_id: int
    folder: Path
    since: str
    days: int
    max_pages: int
    min_seconds: int
    known: set[str]


def _context(conn, paths: Paths, run_id: int) -> _Context:
    run = conn.execute("SELECT * FROM search_runs WHERE id = ?", (run_id,)).fetchone()
    if run is None:
        raise JobTrackerError("not_found", f"There is no search run {run_id}")
    if run["status"] != "running":
        raise JobTrackerError("run_finished", f"Run {run_id} is already finished")
    if run["is_demo"] or not run["capture_folder"]:
        raise JobTrackerError("invalid_run", f"Run {run_id} has no capture folder")
    item = next((p for p in json.loads(run["providers"]) if p["id"] == PROVIDER), None)
    if item is None:
        raise JobTrackerError("not_found", f"'{PROVIDER}' is not a job provider of run {run_id}")
    if item["status"] == "failed":
        raise JobTrackerError(
            "provider_stopped", f"Bumeran is stopped for run {run_id}: "
            f"{item.get('detail') or item.get('reason')}. Do not try it again in this run.")
    if item["status"] not in ("pending", "ok"):
        raise JobTrackerError(
            "provider_not_searched", f"Bumeran is {item['status']} in run {run_id}")
    meta = next((p for p in providers.list_providers() if p["id"] == PROVIDER), None)
    if meta is None or not meta.get("valid"):
        raise JobTrackerError("invalid_file", f"providers/{PROVIDER}.md is missing or invalid")
    started = datetime.fromisoformat(run["started_at"].replace("Z", "+00:00")).astimezone().date()
    days = int(run["posting_age_days"])
    known = {row["external_id"] for row in conn.execute(
        "SELECT external_id FROM postings WHERE provider = ?", (PROVIDER,))}
    return _Context(
        run_id=run_id, folder=paths.home / run["capture_folder"],
        since=(started - timedelta(days=days)).isoformat(), days=days,
        max_pages=max(1, int(meta["max_results_per_query"]) // PAGE_SIZE),
        min_seconds=max(MIN_SECONDS, int(meta["min_seconds_between_requests"])),
        known=known,
    )


def _load_state(folder: Path) -> dict:
    path = folder / STATE_FILE
    state = {"last_page_at": 0.0, "pages": 0, "ids": [], "drafts": []}
    if path.is_file():
        state.update(json.loads(path.read_text(encoding="utf-8")))
    return state


def _save_state(folder: Path, state: dict) -> None:
    (folder / STATE_FILE).write_text(json.dumps(state, indent=1), encoding="utf-8")


def _lock(folder: Path, now: float) -> Path:
    """One reader call at a time per run (shared pacing state). A lock older than any
    call can last was left by a crashed call."""
    path = folder / LOCK_FILE
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
                    "reader_busy", "Another Bumeran read is running for this run. Read the "
                    "titles one at a time, never in parallel; wait for it to finish.",
                    lock=str(path)) from None
            path.unlink(missing_ok=True)
            continue
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            file.write(str(now))
        return path
    raise JobTrackerError("reader_busy", "Another Bumeran read is running for this run.")


class _Stop(Exception):
    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason, self.detail = reason, detail


def _check(page: Page, url: str) -> None:
    """The provider file's stop conditions for one page load."""
    if page.status in BLOCK_STATUSES:
        raise _Stop("blocked", f"{page.status} on {url} ({page.title or 'no title'})")
    if any(t in (page.title or "").lower() for t in BLOCK_TITLES):
        raise _Stop("blocked", f"a Cloudflare page ('{page.title}') instead of {url}")
    for response in page.responses:
        if response["status"] in BLOCK_STATUSES:
            raise _Stop("blocked", f"{response['status']} on the site data for {url}")


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


def _seen_records(conn, entries: list[dict]) -> list[dict]:
    """Postings stored by an earlier run, as import records, with this run's date."""
    records = []
    for entry in entries:
        row = conn.execute("SELECT * FROM postings WHERE provider = ? AND external_id = ?",
                           (PROVIDER, str(entry["id"]))).fetchone()
        records.append({
            "provider": PROVIDER, "external_id": row["external_id"], "url": row["url"],
            "title": row["title"], "company": row["company"], "location": row["location"],
            "country": row["country"],
            "posted_at": _date(entry.get("fechaPublicacion")) or row["posted_at"],
            "description": row["description"], "seniority": row["seniority"],
            "contract_type": row["contract_type"], "work_mode": row["work_mode"],
            "work_mode_detail": row["work_mode_detail"], "language": row["language"],
            "flags": json.loads(row["flags"]) if row["flags"] else [],
            "published_salary": json.loads(row["published_salary"])
            if row["published_salary"] else None,
        })
    return records


# ── the reader ────────────────────────────────────────────────────────────

def read(paths: Paths, run_id: int, title: str, location: str | None = None, *,
         browser: Callable = playwright_browser, clock: Callable[[], float] = time.time,
         sleep: Callable[[float], None] = time.sleep) -> dict:
    """Search one title and write the drafts of its new postings. Returns a summary.
    `location` is accepted for the common reader interface and not used."""
    title = " ".join((title or "").split())
    if not title or not slug(title):
        raise JobTrackerError("invalid_title", "give the title to search with --title")
    with db.session(paths) as conn:
        ctx = _context(conn, paths, run_id)
    ctx.folder.mkdir(parents=True, exist_ok=True)
    lock = _lock(ctx.folder, clock())
    try:
        with browser() as open_page:   # a missing browser stops here, before any page
            return _read(paths, ctx, title, open_page, clock, sleep)
    finally:
        lock.unlink(missing_ok=True)


def _read(paths: Paths, ctx: _Context, title: str, open_page: Open,
          clock: Callable[[], float], sleep: Callable[[float], None]) -> dict:
    run_id = ctx.run_id
    state = _load_state(ctx.folder)
    handled = set(state["ids"])
    summary: dict = {"provider": PROVIDER, "title": title, "requests": 0, "pages": 0,
                     "cards": 0, "outside_window": 0, "duplicate_in_run": 0, "already_seen": 0,
                     "new": 0, "unreadable": [], "unknown_questions": 0, "drafts_path": None,
                     "stopped": None}
    drafts: list[dict] = []
    seen: list[dict] = []

    def load(url: str, watch: str) -> Page:
        wait = state["last_page_at"] + ctx.min_seconds - clock()
        if state["last_page_at"] and wait > 0:
            sleep(wait)
        state["pages"] += 1
        summary["requests"] += 1
        try:
            page = open_page(url, (watch,))
        finally:
            state["last_page_at"] = clock()
            _save_state(ctx.folder, state)
        (ctx.folder / f"{PROVIDER}-{state['pages']}.json").write_text(json.dumps(
            {"url": url, "status": page.status, "title": page.title, "final_url": page.url,
             "responses": page.responses}, ensure_ascii=False, indent=1), encoding="utf-8")
        _check(page, url)
        return page

    def keep(posting_id: str) -> None:
        handled.add(posting_id)
        state["ids"].append(posting_id)

    try:
        for number in range(1, ctx.max_pages + 1):
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
                    seen.append(entry)
                    keep(posting_id)
                else:
                    posting_url = BASE_URL + POSTING_PATH.format(id=posting_id)
                    page = load(posting_url, POSTING_API + posting_id)
                    keep(posting_id)
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
            if len(entries) < PAGE_SIZE or number * PAGE_SIZE >= int(found.get("total") or 0):
                break
    except _Stop as stop:
        summary["stopped"] = {"reason": stop.reason, "detail": stop.detail}

    if drafts:
        name = f"{PROVIDER}-drafts-{len(state['drafts']) + 1}.json"
        (ctx.folder / name).write_text(json.dumps(drafts, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
        state["drafts"].append(name)
        summary["drafts_path"] = str(ctx.folder / name)
    _save_state(ctx.folder, state)
    summary["new"] = len(drafts)
    summary["already_seen"] = len(seen)
    with db.session(paths) as conn:
        if seen:
            search.import_postings(conn, run_id, _seen_records(conn, seen))
        if summary["stopped"]:
            search.record_provider(conn, run_id, PROVIDER, "failed",
                                   reason=summary["stopped"]["reason"],
                                   detail=summary["stopped"]["detail"])
    return summary

