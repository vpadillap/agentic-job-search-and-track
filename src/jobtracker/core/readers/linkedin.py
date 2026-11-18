"""LinkedIn reader: the request and extraction part of providers/linkedin.md.

One call searches one title on LinkedIn's guest search (logged out, no
cookies, no redirects followed), opens the public page of each new posting,
and writes a drafts file to the run's capture folder. The pacing, the page
limit, and the stop conditions of the provider file are applied here, also
across calls of the same run. What needs judgment (work mode and its detail,
language, flags, a salary in the text) is left to the agent's reading.
"""
from __future__ import annotations

import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from html.parser import HTMLParser

from .. import db
from ..errors import JobTrackerError
from ..paths import Paths
from . import common

PROVIDER = "linkedin"
LABEL = "LinkedIn"
SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
POSTING_URL = "https://www.linkedin.com/jobs/view/{id}/"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/131.0 Safari/537.36")
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
TIMEOUT_SECONDS = 30
PAGE_SIZE = 10           # cards per guest search page
WINDOWS = ((1, "r86400"), (7, "r604800"), (30, "r2592000"))   # posting age LinkedIn offers
CONTRACT_TYPES = {"Full-time": "full-time", "Part-time": "part-time", "Contract": "contractor"}
SIGN_IN_MARKERS = ("session_key", "sign-in-form", "authwall")
UNREADABLE = (404, 410)  # the posting was removed: listed, not a reason to stop
LOCK_FILE = "linkedin.lock"
STALE_LOCK_SECONDS = common.STALE_LOCK_SECONDS

Fetch = Callable[[str], tuple[int, bytes, "str | None"]]


# ── HTTP ──────────────────────────────────────────────────────────────────

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # a redirect is answered, never followed
        return None


def fetch(url: str) -> tuple[int, bytes, str | None]:
    """GET without cookies or redirects: (status, body, where a redirect points)."""
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, response.read(), None
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers.get("Location")


def window(days: int) -> str:
    """The smallest posting-age window LinkedIn offers visitors that covers `days`."""
    for limit, value in WINDOWS:
        if days <= limit:
            return value
    return WINDOWS[-1][1]


# ── HTML ──────────────────────────────────────────────────────────────────

CARD = "base-search-card"
CARD_FIELDS = {"base-search-card__title": "title", "base-search-card__subtitle": "company",
               "job-search-card__location": "location",
               "job-search-card__salary-info": "salary_shown"}
DESCRIPTION = "show-more-less-html__markup"
CRITERIA_HEADER = "description__job-criteria-subheader"
CRITERIA_TEXT = "description__job-criteria-text"
BLOCK_TAGS = {"p", "div", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}
VOID_TAGS = {"br", "img", "input", "meta", "link", "hr", "source", "wbr", "area", "col", "embed"}


def _line_text(text: str) -> str:
    return " ".join(text.split())


def plain_text(raw: str) -> str:
    """Spaces collapsed within each line, at most one blank line in a row, and no
    blank line between two list items."""
    lines = [_line_text(line) for line in raw.splitlines()]
    kept: list[str] = []
    for index, line in enumerate(lines):
        if not line:
            following = next((n for n in lines[index + 1:] if n), "")
            if not kept or not kept[-1] or (kept[-1].startswith("• ")
                                             and following.startswith("• ")):
                continue
        kept.append(line)
    return "\n".join(kept).strip()


@dataclass
class _Capture:
    key: str
    tag: str
    depth: int = 1
    parts: list[str] = field(default_factory=list)


class _Parser(HTMLParser):
    """Text of the elements LinkedIn marks with known classes (cards, posting page)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[dict] = []
        self.capture: _Capture | None = None
        self.description: list[str] | None = None
        self.description_depth = 0
        self.description_done = False
        self.after_bullet = False
        self.criteria: dict[str, str] = {}
        self.pending_header: str | None = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if self.description is not None and not self.description_done:
            self._description_start(tag)
            return
        if CARD in classes and "jobPosting:" in (attributes.get("data-entity-urn") or ""):
            job_id = attributes["data-entity-urn"].rsplit(":", 1)[-1]
            self.cards.append({"external_id": job_id})
            return
        if tag == "time" and self.cards and "posted_at" not in self.cards[-1]:
            when = attributes.get("datetime")
            if when and re.fullmatch(r"\d{4}-\d{2}-\d{2}", when):
                self.cards[-1]["posted_at"] = when
        if self.capture is not None:
            if tag == self.capture.tag and tag not in VOID_TAGS:
                self.capture.depth += 1
            return
        if DESCRIPTION in classes and not self.description_done:
            self.description, self.description_depth = [], 1 if tag == "div" else 0
            return
        for name, key in CARD_FIELDS.items():
            if name in classes and self.cards:
                self.capture = _Capture(key, tag)
                return
        if CRITERIA_HEADER in classes:
            self.capture = _Capture("criteria_header", tag)
        elif CRITERIA_TEXT in classes:
            self.capture = _Capture("criteria_text", tag)

    def _description_start(self, tag: str) -> None:
        parts = self.description
        assert parts is not None
        if tag == "div":
            self.description_depth += 1
        if tag == "br":
            parts.append("\n")
        elif tag == "li":
            parts.append("\n• ")
            self.after_bullet = True
        elif tag in BLOCK_TAGS and not self.after_bullet:  # <li><p>…: keep the text on the bullet
            parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.description is not None and not self.description_done:
            if tag == "div":
                self.description_depth -= 1
                if self.description_depth <= 0:
                    self.description_done = True
                    return
            if tag in BLOCK_TAGS and tag != "li":
                self.description.append("\n")
            return
        if self.capture is None or tag != self.capture.tag:
            return
        self.capture.depth -= 1
        if self.capture.depth > 0:
            return
        capture, self.capture = self.capture, None
        text = _line_text("".join(capture.parts))
        if capture.key == "criteria_header":
            self.pending_header = text
        elif capture.key == "criteria_text":
            if self.pending_header:
                self.criteria[self.pending_header] = text
            self.pending_header = None
        elif self.cards and text:
            self.cards[-1].setdefault(capture.key, text)

    def handle_data(self, data: str) -> None:
        if self.description is not None and not self.description_done:
            # As in a browser, line breaks in the source are spaces; only <br> and
            # block elements start a new line.
            text = re.sub(r"\s+", " ", data)
            self.description.append(text)
            if text.strip():
                self.after_bullet = False
        elif self.capture is not None:
            self.capture.parts.append(data)


def parse_search(page: str) -> dict:
    """The cards of a guest search page, and how many job ids the page mentions."""
    parser = _Parser()
    parser.feed(page)
    parser.close()
    ids = set(re.findall(r"urn:li:jobPosting:(\d+)", page))
    return {"cards": parser.cards, "job_ids": len(ids)}


def parse_posting(page: str) -> dict:
    """The description (plain text) and the criteria of a public posting page."""
    parser = _Parser()
    parser.feed(page)
    parser.close()
    description = plain_text("".join(parser.description)) if parser.description is not None \
        else None
    return {"description": description, "criteria": parser.criteria}


# ── the reader ────────────────────────────────────────────────────────────

_Stop = common.Stop


def _check(status: int, where: str | None, url: str) -> None:
    """The provider file's stop conditions for any answer that is not a page."""
    if status in (429, 999):
        raise _Stop("blocked", f"{status} {url}")
    if 300 <= status < 400:
        raise _Stop("blocked", f"{status} redirect to {where or 'an unknown page'} from {url}")
    if status != 200:
        raise _Stop("error", f"{status} {url}")


def _draft(card: dict, posting: dict, ctx: common.Context) -> dict:
    criteria = posting["criteria"]
    seniority = criteria.get("Seniority level")
    employment = criteria.get("Employment type")
    return {
        "provider": PROVIDER, "external_id": card["external_id"],
        "url": POSTING_URL.format(id=card["external_id"]),
        "title": card.get("title"), "company": card.get("company"),
        "location": card.get("location"), "country": ctx.country,
        "posted_at": card.get("posted_at"), "description": posting["description"],
        "seniority": None if seniority in (None, "Not Applicable") else seniority,
        "contract_type": CONTRACT_TYPES.get(employment or ""),
        "employment_type": employment, "salary_shown": card.get("salary_shown"),
        # The agent's reading (see providers/linkedin.md):
        "work_mode": None, "work_mode_detail": None, "language": None, "flags": [],
        "published_salary": None,
    }


def read(paths: Paths, run_id: int, title: str, location: str | None = None, *,
         fetch: Fetch = fetch, clock: Callable[[], float] = time.time,
         sleep: Callable[[float], None] = time.sleep) -> dict:
    """Search one title and write the drafts of its new postings. Returns a summary."""
    title = _line_text(title or "")
    if not title:
        raise JobTrackerError("invalid_title", "give the title to search with --title")
    location = _line_text(location or "") or None
    with db.session(paths) as conn:
        ctx = common.context(conn, paths, run_id, PROVIDER, LABEL)
    ctx.folder.mkdir(parents=True, exist_ok=True)
    lock = common.lock(ctx, LABEL, clock())
    try:
        return _read(paths, ctx, title, location, fetch, clock, sleep)
    finally:
        lock.unlink(missing_ok=True)


def _read(paths: Paths, ctx: common.Context, title: str, location: str | None, fetch: Fetch,
          clock: Callable[[], float], sleep: Callable[[float], None]) -> dict:
    state = common.load_state(ctx)
    handled = set(state["job_ids"])
    summary: dict = {"provider": PROVIDER, "title": title, "requests": 0, "pages": 0,
                     "cards": 0, "outside_window": 0, "duplicate_in_run": 0, "already_seen": 0,
                     "new": 0, "unreadable": [], "drafts_path": None, "stopped": None}
    drafts: list[dict] = []
    seen: list[dict] = []
    max_pages = max(1, ctx.max_results // PAGE_SIZE)

    def get(url: str) -> tuple[int, str, str | None]:
        wait = state["last_request_at"] + ctx.min_seconds - clock()
        if state["last_request_at"] and wait > 0:
            sleep(wait)
        state["requests"] += 1
        summary["requests"] += 1
        try:
            status, body, where = fetch(url)
        except (urllib.error.URLError, OSError) as error:
            raise _Stop("error", f"network error ({error}) on {url}") from error
        finally:
            state["last_request_at"] = clock()
            common.save_state(ctx, state)
        (ctx.folder / f"{PROVIDER}-{state['requests']}.html").write_bytes(body)
        return status, body.decode("utf-8", "replace"), where

    def keep(job_id: str) -> None:
        handled.add(job_id)
        state["job_ids"].append(job_id)

    try:
        for page in range(max_pages):
            query = {"keywords": title, "location": location, "f_TPR": window(ctx.days),
                     "start": page * PAGE_SIZE}
            url = SEARCH_URL + "?" + urllib.parse.urlencode(
                {k: v for k, v in query.items() if v is not None}, quote_via=urllib.parse.quote)
            status, text, where = get(url)
            _check(status, where, url)
            summary["pages"] += 1
            found = parse_search(text)
            cards = found["cards"]
            if not cards:
                if any(marker in text for marker in SIGN_IN_MARKERS):
                    raise _Stop("blocked", f"a sign-in page instead of results on {url}")
                if found["job_ids"]:
                    raise _Stop("error", f"job ids without '{CARD}' cards on {url}: the page "
                                "layout changed")
                break  # no (more) results for this title
            for card in cards:
                summary["cards"] += 1
                job_id = card["external_id"]
                if card.get("posted_at") and card["posted_at"] < ctx.since:
                    summary["outside_window"] += 1
                elif job_id in handled:
                    summary["duplicate_in_run"] += 1
                elif job_id in ctx.known:
                    seen.append(card)
                    keep(job_id)
                else:
                    posting_url = POSTING_URL.format(id=job_id)
                    status, text, where = get(posting_url)
                    keep(job_id)
                    if status in UNREADABLE:
                        summary["unreadable"].append({"external_id": job_id, "url": posting_url,
                                                      "reason": f"HTTP {status}"})
                        continue
                    _check(status, where, posting_url)
                    posting = parse_posting(text)
                    if not posting["description"]:
                        raise _Stop("error", f"no '{DESCRIPTION}' on {posting_url}: the page "
                                    "layout changed")
                    drafts.append(_draft(card, posting, ctx))
            if len(cards) < PAGE_SIZE:
                break
    except _Stop as stop:
        summary["stopped"] = {"reason": stop.reason, "detail": stop.detail}
    return common.finish(paths, ctx, state, summary, drafts, seen)
