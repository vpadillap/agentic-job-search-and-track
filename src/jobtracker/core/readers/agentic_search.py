"""Agentic web search reader: the reading part of providers/agentic-search.md.

The agent discovers postings with its web-search tools and passes the links it
found with --found; this reader reads them politely and verbatim:

- refuses, before any request, links on another provider's `domains`, links that
  are not web pages, sign-in, account or application pages, and paths the host's
  robots.txt disallows;
- fetches over plain HTTP with an honest user agent, at least the provider's
  interval between two requests to the same host (across calls of a run);
- renders a page that needs JavaScript once in a plain headless browser
  (Playwright, when installed: no stealth, no cookies kept, no sign-in);
- ends a host for the run when it refuses (401, 403, 429, a challenge page),
  never retrying it another way;
- drafts postings from their `JobPosting` structured data, or from the lines of
  a captured page the agent points at, so no description is ever retyped;
- reads Lever and Ashby boards through their public posting APIs, and returns
  the matching links of any other careers listing;
- follows a copy's pointer to the original posting and keeps one draft per
  posting, from the most direct source.

Standard library only; Playwright is imported only when a page needs it.
"""
from __future__ import annotations

import html as html_lib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from collections.abc import Callable
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path

from .. import db, providers
from ..errors import JobTrackerError
from ..paths import Paths
from . import common
from .glassdoor import plain_text

PROVIDER = "agentic-search"
LABEL = "Web search (company sites)"
USER_AGENT = "jobtracker/0.1 (local job-search assistant; reads public job postings)"
ROBOTS_AGENT = "jobtracker"
INSTALL = "Install the browser with: jt providers install agentic-search"
MIN_POSTING_CHARS = 400          # visible text below this, with no posting data: maybe JS
LISTING_LINKS = 2                # matching links that make a page a careers listing

TRACKING = re.compile(r"^(utm_.*|ref|refid|source|src|gh_src|gh_jid_src|lever-source.*|"
                      r"lever-origin|trk|trackingid|fbclid|gclid|mc_.*|_hs.*)$", re.I)
NOT_PAGES = re.compile(r"/(log-?in|sign-?in|sign-?up|register|account|my-?account|apply|"
                       r"postular|postulacion|auth|oauth|session)(/|$|\?)", re.I)
CHALLENGE = re.compile(r"(cf-challenge|challenge-platform|captcha|verify you are human|"
                       r"are you a robot|attention required|verifica que eres humano|"
                       r"request unsuccessful\. incapsula)", re.I)
JS_SHELL = re.compile(r"(<div[^>]+id=[\"'](root|app|__next|__nuxt)[\"'][^>]*>\s*</div>|"
                      r"enable javascript|habilita javascript|requires javascript|"
                      r"activa javascript)", re.I)
CLOSED = re.compile(r"(no longer accepting applications|this (job|position|posting) "
                    r"(is|has been) (closed|filled|expired)|job (is )?no longer available|"
                    r"ya no (está|esta) disponible|convocatoria (cerrada|finalizada)|"
                    r"(oferta|vacante|aviso) (cerrada|finalizada|expirada))", re.I)
ATS_HOSTS = ("lever.co", "ashbyhq.com", "myworkdayjobs.com", "smartrecruiters.com",
             "workable.com", "bamboohr.com", "teamtailor.com", "recruitee.com",
             "breezy.hr", "jobvite.com", "icims.com", "successfactors.com",
             "taleo.net", "personio.de", "personio.com", "pinpointhq.com", "rippling.com",
             "jazzhr.com", "applytojob.com", "eightfold.ai", "oraclecloud.com")
LEVER = re.compile(r"^https://jobs\.(?:eu\.)?lever\.co/(?P<co>[\w.-]+)(?:/(?P<id>[0-9a-f-]{36}))?"
                   r"/?$")
ASHBY = re.compile(r"^https://jobs\.ashbyhq\.com/(?P<co>[\w.%-]+)(?:/(?P<id>[0-9a-f-]{36}))?/?$")
REMOTE = ("remote", "remoto", "anywhere", "teletrabajo")

Getter = Callable[[str], tuple[int | None, str, str]]      # url -> (status, body, final url)
Renderer = Callable[[str], tuple[int | None, str]]          # url -> (status, rendered html)


# ── network ──────────────────────────────────────────────────────────────

def http_get(url: str) -> tuple[int | None, str, str]:
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT, "Accept-Language": "es,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.5"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            charset = response.headers.get_content_charset() or "utf-8"
            return response.status, response.read().decode(charset, "replace"), response.url
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace"), url


def playwright_renderer() -> Renderer | None:
    """A plain headless Chromium page per call, or None when Playwright is missing."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return None

    def render(url: str) -> tuple[int | None, str]:
        from playwright.sync_api import Error, sync_playwright
        try:
            with sync_playwright() as play:
                browser = play.chromium.launch(headless=True)
                try:
                    probe = browser.new_page()
                    agent = f"{probe.evaluate('navigator.userAgent')} {USER_AGENT}"
                    probe.close()
                    page = browser.new_context(user_agent=agent).new_page()
                    response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except Error:
                        pass
                    return (response.status if response else None), page.content()
                finally:
                    browser.close()
        except Error as error:
            raise JobTrackerError("missing_dependency", f"the headless browser failed: "
                                  f"{error}. {INSTALL}", tool="playwright") from error
    return render


# ── links ────────────────────────────────────────────────────────────────

def canonical(url: str) -> str:
    """The link without tracking parameters or fragment; host lowercased."""
    parts = urllib.parse.urlsplit(url.strip())
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
             if not TRACKING.match(k)]
    path = parts.path or "/"
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path,
                                    urllib.parse.urlencode(query), ""))


def host_of(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower()


def is_ats(host: str) -> bool:
    return any(providers.host_matches(host, d) for d in ATS_HOSTS)


def refusal(url: str) -> str | None:
    """Why a link is never requested here, or None."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return "not_a_web_page"
    if providers.owner_of(parts.hostname, besides=PROVIDER):
        return "provider_domain"
    if NOT_PAGES.search(parts.path):
        return "sign_in_or_apply_page"
    return None


def parse_found(items: object) -> list[dict]:
    if not isinstance(items, list):
        raise JobTrackerError("invalid_found", "--found must be a JSON list of links or "
                              "objects with a 'url'")
    found = []
    for index, item in enumerate(items):
        entry = {"url": item} if isinstance(item, str) else item
        if not isinstance(entry, dict) or not isinstance(entry.get("url"), str):
            raise JobTrackerError("invalid_found", f"item {index + 1} of --found has no 'url'")
        lines = entry.get("lines")
        if lines is not None and not (
                isinstance(lines, list) and len(lines) == 2
                and all(isinstance(n, int) and n > 0 for n in lines) and lines[0] <= lines[1]):
            raise JobTrackerError("invalid_found", f"item {index + 1}: 'lines' must be "
                                  "[first, last], line numbers of the captured text")
        url = canonical(entry["url"])
        if is_ats(host_of(url)) and url.split("?")[0].endswith("/apply"):
            url = url.split("?")[0][:-len("/apply")]     # the posting, not its form
        found.append({**entry, "url": url})
    return found


# ── page content ─────────────────────────────────────────────────────────

def _json_ld_items(page: str) -> list[dict]:
    items: list[dict] = []
    for block in re.finditer(
            r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
            page or "", re.S | re.I):
        try:
            data = json.loads(block.group(1).strip())
        except ValueError:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            item = stack.pop(0)
            if isinstance(item, dict):
                items.append(item)
                stack.extend(item.get("@graph") or [])
            elif isinstance(item, list):
                stack.extend(item)
    return items


def job_posting(page: str) -> dict | None:
    for item in _json_ld_items(page):
        kind = item.get("@type")
        if kind == "JobPosting" or (isinstance(kind, list) and "JobPosting" in kind):
            return item
    return None


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str, str]] = []    # (href, text, rel)
        self._open: list[list[str]] = []
        self.canonical: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        values = {k: v or "" for k, v in attrs}
        if tag == "link" and "canonical" in values.get("rel", "").lower():
            self.canonical = values.get("href") or None
        if tag == "a" and values.get("href"):
            self._open.append([values["href"], "", values.get("rel", "")])

    def handle_data(self, data: str) -> None:
        if self._open:
            self._open[-1][1] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._open:
            href, text, rel = self._open.pop()
            self.links.append((href, " ".join(text.split()), rel))


def page_links(page: str, base: str) -> tuple[list[tuple[str, str]], str | None]:
    parser = _Links()
    parser.feed(page or "")
    links = [(canonical(urllib.parse.urljoin(base, href)), text)
             for href, text, _ in parser.links
             if not href.startswith(("#", "mailto:", "tel:", "javascript:"))]
    found = parser.canonical
    return links, canonical(urllib.parse.urljoin(base, found)) if found else None


def needs_browser(page: str) -> bool:
    if job_posting(page):
        return False
    return bool(JS_SHELL.search(page or "")) or len(plain_text(page)) < MIN_POSTING_CHARS


def numbered(url: str, text: str) -> str:
    lines = text.splitlines()
    width = len(str(len(lines)))
    return url + "\n" + "\n".join(f"{n:>{width}}| {line}" for n, line in enumerate(lines, 1))


def cut_lines(numbered_text: str, first: int, last: int) -> str:
    """Lines first..last of a captured text, without their numbers."""
    rows = numbered_text.splitlines()[1:]
    if last > len(rows):
        raise JobTrackerError("invalid_found", f"the capture has {len(rows)} lines, not {last}")
    return "\n".join(re.sub(r"^\s*\d+\| ?", "", row, count=1)
                     for row in rows[first - 1:last]).strip()


def _text(value: object) -> str | None:
    if isinstance(value, dict):
        value = value.get("name") or value.get("value")
    text = " ".join(html_lib.unescape(str(value or "")).split())
    return text or None


def _location(posting: dict) -> tuple[str | None, list[str]]:
    """(readable location, country codes or names) from JSON-LD jobLocation."""
    places = posting.get("jobLocation") or []
    places = places if isinstance(places, list) else [places]
    names, countries = [], []
    for place in places:
        address = (place or {}).get("address") if isinstance(place, dict) else None
        if isinstance(address, dict):
            parts = [_text(address.get(k)) for k in
                     ("addressLocality", "addressRegion", "addressCountry")]
            names.append(", ".join(p for p in parts if p))
            if _text(address.get("addressCountry")):
                countries.append(_text(address.get("addressCountry")) or "")
        elif isinstance(address, str):
            names.append(address)
    if str(posting.get("jobLocationType") or "").upper() == "TELECOMMUTE":
        names.append("Remote")
    location = "; ".join(n for n in names if n) or None
    return location, countries


def _date(value: object) -> str | None:
    text = str(value or "")
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return text[:10]
    return None


def is_closed(posting: dict | None, page_text: str, today: str) -> bool:
    if posting is not None:
        until = _date(posting.get("validThrough"))
        if until and until < today:
            return True
    return bool(CLOSED.search(page_text or ""))


# ── the reader ───────────────────────────────────────────────────────────

def read(paths: Paths, run_id: int, title: str, location: str | None = None, *,
         found: str | None = None, get: Getter = http_get,
         renderer: Renderer | None | bool = True,
         clock: Callable[[], float] = time.time,
         sleep: Callable[[float], None] = time.sleep) -> dict:
    """Read the links the agent found for one title and write drafts. `location` is
    optional place words ("Peru; Lima") that place a posting in the profile's country."""
    title = " ".join((title or "").split())
    if not title:
        raise JobTrackerError("invalid_title", "give the title to search with --title")
    if not found:
        raise JobTrackerError("invalid_found", "give the links you found with --found <file>, "
                              "a JSON list (see providers/agentic-search.md)")
    path = Path(found)
    if not path.is_file():
        raise JobTrackerError("not_found", f"There is no file at '{found}'")
    try:
        items = parse_found(json.loads(path.read_text(encoding="utf-8")))
    except ValueError as error:
        raise JobTrackerError("invalid_found", f"--found is not JSON: {error}") from error
    if renderer is True:
        renderer = playwright_renderer()
    with db.session(paths) as conn:
        ctx = common.context(conn, paths, run_id, PROVIDER, LABEL)
    ctx.folder.mkdir(parents=True, exist_ok=True)
    lock = common.lock(ctx, LABEL, clock())
    try:
        return _Reader(paths, ctx, title, location, get, renderer or None, clock, sleep).run(
            items)
    finally:
        lock.unlink(missing_ok=True)


class _Reader:
    def __init__(self, paths: Paths, ctx: common.Context, title: str, location: str | None,
                 get: Getter, renderer: Renderer | None, clock: Callable[[], float],
                 sleep: Callable[[float], None]) -> None:
        self.paths, self.ctx, self.title, self.get = paths, ctx, title, get
        self.renderer, self.clock, self.sleep = renderer, clock, sleep
        self.places = [w.strip() for w in re.split(r"[;,]", location or "") if w.strip()]
        self.today = date.today().isoformat()
        self.state = common.load_state(ctx)
        for key, empty in (("hosts", {}), ("refused_hosts", {}), ("robots", {}),
                           ("pages", {}), ("fingerprints", {})):
            self.state.setdefault(key, empty)
        self.pages_read = 0
        self.drafts: dict[str, dict] = {}       # fingerprint -> draft (this call)
        self.ranks: dict[str, int] = {}
        self.seen: list[dict] = []
        self.summary: dict = {
            "provider": PROVIDER, "title": title, "requests": 0, "links": 0,
            "pages_read": 0, "rendered": 0, "refused": [], "refused_hosts": {},
            "suggest_provider": [], "needs_browser": [], "no_structured_data": [],
            "candidate_links": [], "other_title": [], "closed": [], "gone": [],
            "copies": [], "not_original": [], "unreadable": [], "duplicate_in_run": 0,
            "already_seen": 0, "new": 0,
            "capped": False, "drafts_path": None, "stopped": None,
            "browser": "installed" if renderer else f"not installed: {INSTALL}"}

    # ── requests ──
    def _pace(self, host: str) -> None:
        last = self.state["hosts"].get(host, 0.0)
        wait = last + self.ctx.min_seconds - self.clock()
        if last and wait > 0:
            self.sleep(wait)

    def _request(self, url: str, *, render: bool = False) -> tuple[int | None, str, str]:
        host = host_of(url)
        self._pace(host)
        self.state["requests"] += 1
        self.summary["requests"] += 1
        try:
            if render and self.renderer:
                status, body = self.renderer(url)
                final = url
            else:
                status, body, final = self.get(url)
        except (OSError, ValueError) as error:
            status, body, final = None, str(error), url
        self.state["hosts"][host] = self.clock()
        self.state["last_request_at"] = self.clock()
        common.save_state(self.ctx, self.state)
        return status, body or "", final or url

    def _robots_allows(self, url: str) -> bool:
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname or ""
        rules = self.state["robots"].get(host)
        if rules is None:
            status, body, _ = self._request(f"{parts.scheme}://{parts.netloc}/robots.txt")
            if status is not None and 400 <= status < 500 and status not in (401, 403, 429):
                rules = ""                                   # no robots.txt: allowed
            elif status == 200:
                rules = body
                (self.ctx.folder / f"{PROVIDER}-robots-{host}.txt").write_text(
                    body, encoding="utf-8")
            else:
                self._refuse_host(host, "robots_unreachable" if status not in (401, 403, 429)
                                  else "site_refused", f"robots.txt answered {status}")
                return False
            self.state["robots"][host] = rules
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(rules.splitlines())
        return parser.can_fetch(ROBOTS_AGENT, url)

    def _refuse_host(self, host: str, reason: str, detail: str) -> None:
        self.state["refused_hosts"][host] = {"reason": reason, "detail": detail}
        self.summary["refused_hosts"][host] = reason
        common.save_state(self.ctx, self.state)

    def _capture(self, url: str, body: str) -> dict:
        n = len(self.state["pages"]) + 1
        html_name, text_name = f"{PROVIDER}-{n}.html", f"{PROVIDER}-{n}.txt"
        (self.ctx.folder / html_name).write_text(body, encoding="utf-8")
        text = plain_text(body)
        (self.ctx.folder / text_name).write_text(numbered(url, text), encoding="utf-8")
        page = {"html": html_name, "text": text_name, "lines": len(text.splitlines())}
        self.state["pages"][url] = page
        common.save_state(self.ctx, self.state)
        return page

    def _fetch_page(self, url: str) -> str | None:
        """The page's HTML (fetched, rendered when needed, and captured), or None."""
        host = host_of(url)
        if host in self.state["refused_hosts"]:
            self.summary["refused"].append({"url": url, "reason": "site_refused"})
            return None
        if self.pages_read >= self.ctx.max_results:
            self.summary["capped"] = True
            return None
        if not self._robots_allows(url):
            refused = self.state["refused_hosts"].get(host)
            self.summary["refused"].append(
                {"url": url, "reason": refused["reason"] if refused else "robots"})
            if refused and refused["reason"] == "site_refused" and not is_ats(host):
                self.summary["suggest_provider"].append(host)
            return None
        status, body, final = self._request(url)
        self.pages_read += 1
        if status in (401, 403, 429) or (status == 200 and CHALLENGE.search(body[:20000])
                                         and not job_posting(body)):
            self._refuse_host(host, "site_refused", f"{status} from {url}")
            self.summary["refused"].append({"url": url, "reason": "site_refused"})
            if not is_ats(host):
                self.summary["suggest_provider"].append(host)
            return None
        if status in (404, 410):
            self.summary["gone"].append(url)
            return None
        if status != 200:
            self.summary["unreadable"].append({"url": url, "status": status})
            return None
        if host_of(final) != host and refusal(final):
            self.summary["refused"].append({"url": final, "reason": refusal(final)})
            return None
        if needs_browser(body):
            if self.renderer:
                rendered_status, rendered = self._request(url, render=True)[:2]
                self.summary["rendered"] += 1
                if rendered_status == 200 and rendered:
                    body = rendered
            else:
                self.summary["needs_browser"].append(url)
        self.summary["pages_read"] += 1
        self._capture(url, body)
        return body

    def _api(self, url: str) -> object | None:
        """A public posting API (Lever, Ashby): JSON, paced, captured; robots not asked."""
        if self.pages_read >= self.ctx.max_results:
            self.summary["capped"] = True
            return None
        status, body, _ = self._request(url)
        self.pages_read += 1
        n = len(self.state["pages"]) + 1
        (self.ctx.folder / f"{PROVIDER}-{n}.json").write_text(body, encoding="utf-8")
        self.state["pages"][url] = {"json": f"{PROVIDER}-{n}.json"}
        if status in (401, 403, 429):
            self._refuse_host(host_of(url), "site_refused", f"{status} from {url}")
            return None
        if status != 200:
            self.summary["gone"].append(url)
            return None
        try:
            return json.loads(body)
        except ValueError:
            self.summary["gone"].append(url)
            return None

    # ── drafts ──
    def _country(self, location: str | None, countries: list[str]) -> str | None:
        code = (self.ctx.country or "").upper()
        if not code:
            return None
        if any(c.strip().upper() == code for c in countries):
            return code
        text = " ".join(common.words(" ".join([location or "", *countries])))
        if any(" ".join(common.words(p)) and re.search(
                rf"\b{re.escape(' '.join(common.words(p)))}\b", text) for p in self.places):
            return code
        return None

    def _rank(self, url: str, company: str | None) -> int:
        """2: the company's own site; 1: an applicant-tracking board; 0: anything else."""
        host = host_of(url)
        if is_ats(host):
            return 1
        labels = set(re.split(r"[.-]", host))
        if any(len(w) >= 4 and w in labels for w in common.words(company or "")):
            return 2
        return 0

    def _keep(self, draft: dict, synonym: bool = False) -> None:
        if not synonym and not common.title_matches(self.title, draft["title"] or ""):
            self.summary["other_title"].append({"url": draft["url"], "title": draft["title"]})
            return
        if draft["external_id"] in self.ctx.known:
            self.seen.append({"external_id": draft["external_id"],
                              "posted_at": draft["posted_at"]})
            return
        key = "|".join(" ".join(common.words(draft[f] or "")) for f in
                       ("company", "title", "location"))
        rank = self._rank(draft["url"], draft["company"])
        earlier = self.state["fingerprints"].get(key)
        if earlier and key not in self.drafts:           # drafted by an earlier call
            if earlier == draft["url"]:
                self.summary["duplicate_in_run"] += 1
            else:
                self.summary["copies"].append({"url": draft["url"], "kept": earlier})
            return
        if key in self.drafts:
            kept = self.drafts[key]
            if kept["url"] == draft["url"]:
                return
            if rank <= self.ranks[key]:
                self.summary["copies"].append({"url": draft["url"], "kept": kept["url"]})
                return
            self.summary["copies"].append({"url": kept["url"], "kept": draft["url"]})
        self.drafts[key], self.ranks[key] = draft, rank
        self.state["fingerprints"][key] = draft["url"]

    def _draft(self, url: str, **fields: object) -> dict:
        draft = {
            "provider": PROVIDER, "external_id": url, "url": url, "source_site": host_of(url),
            "title": None, "company": None, "location": None, "country": None,
            "posted_at": None, "description": None, "seniority": None, "contract_type": None,
            "form_questions": [],
            "work_mode": None, "work_mode_detail": None, "language": None, "flags": [],
            "published_salary": None,
        }
        draft.update(fields)
        return draft

    def _from_json_ld(self, url: str, posting: dict, body_text: str) -> dict | None:
        if is_closed(posting, body_text, self.today):
            self.summary["closed"].append(url)
            return None
        location, countries = _location(posting)
        employment = posting.get("employmentType")
        employment = employment[0] if isinstance(employment, list) and employment else employment
        salary = posting.get("baseSalary") if isinstance(posting.get("baseSalary"), dict) else None
        value = (salary or {}).get("value") if isinstance((salary or {}).get("value"),
                                                          dict) else {}
        return self._draft(
            url, title=_text(posting.get("title")),
            company=_text(posting.get("hiringOrganization")),
            location=location, country=self._country(location, countries),
            posted_at=_date(posting.get("datePosted")),
            description=plain_text(html_lib.unescape(str(posting.get("description") or ""))),
            contract_type={"FULL_TIME": "full-time", "PART_TIME": "part-time",
                           "CONTRACTOR": "contractor"}.get(str(employment or "").upper()),
            site_salary={"currency": (salary or {}).get("currency"),
                         "min": value.get("minValue"), "max": value.get("maxValue"),
                         "unit": value.get("unitText")} if salary else None,
            site_employment_type=employment, site_valid_through=_date(
                posting.get("validThrough")))

    def _original(self, url: str, page: str, posting: dict | None) -> str | None:
        """A link to the same posting on its original site, when this page is a copy."""
        host = host_of(url)
        if is_ats(host):
            return None
        links, canonical_link = page_links(page, url)
        candidates = []
        if posting and isinstance(posting.get("url"), str):
            candidates.append(canonical(urllib.parse.urljoin(url, posting["url"])))
        if canonical_link:
            candidates.append(canonical_link)
        candidates += [link for link, _ in links if is_ats(host_of(link))
                       and len([s for s in urllib.parse.urlsplit(link).path.split("/") if s]) >= 2]
        for link in candidates:
            other = host_of(link)
            if other and other != host and not refusal(link):
                return link
        return None

    # ── links ──
    def _read_link(self, item: dict, depth: int = 0) -> None:
        url = item["url"]
        why = refusal(url)
        if why:
            self.summary["refused"].append({"url": url, "reason": why})
            return
        lever, ashby = LEVER.match(url), ASHBY.match(url)
        if (lever or ashby) and item.get("synonym"):        # an API posting: read it again
            match = lever or ashby
            if match.group("id"):
                (self._lever if lever else self._ashby)(
                    urllib.parse.unquote(match.group("co")), match.group("id"))
                return
        if item.get("lines") or item.get("synonym"):
            self._from_capture(item)
            return
        if lever:
            self._lever(lever.group("co"), lever.group("id"))
            return
        if ashby:
            self._ashby(urllib.parse.unquote(ashby.group("co")), ashby.group("id"))
            return
        if url in self.state["pages"]:
            page_html = (self.ctx.folder / self.state["pages"][url]["html"]).read_text(
                encoding="utf-8") if "html" in self.state["pages"][url] else None
        else:
            page_html = self._fetch_page(url)
        if page_html is None:
            return
        posting = job_posting(page_html)
        original = self._original(url, page_html, posting) if depth == 0 else None
        if original and original not in self.state["pages"]:
            before = dict(self.state["fingerprints"])
            self._read_link({"url": original}, depth + 1)
            if self.state["fingerprints"] != before:         # the original was drafted
                self.summary["copies"].append({"url": url, "kept": original})
                return
        text = plain_text(page_html)
        if posting:
            draft = self._from_json_ld(url, posting, text)
            if draft:
                if self._rank(url, draft["company"]) == 0:
                    self.summary["not_original"].append(url)
                self._keep(draft)
            return
        if is_closed(None, text, self.today):
            self.summary["closed"].append(url)
            return
        links, _ = page_links(page_html, url)
        matching = []
        for link, label in links:
            if (label and common.title_matches(self.title, label) and link != url
                    and (host_of(link) == host_of(url) or is_ats(host_of(link)))
                    and link not in matching and not refusal(link)):
                matching.append(link)
        if len(matching) >= LISTING_LINKS or (matching and depth == 0 and len(text) < 3000):
            self.summary["candidate_links"].append({"page": url, "links": matching[:40]})
            return
        page = self.state["pages"][url]
        self.summary["no_structured_data"].append(
            {"url": url, "text_file": str(self.ctx.folder / page["text"]),
             "lines": page["lines"]})

    def _from_capture(self, item: dict) -> None:
        url = item["url"]
        page = self.state["pages"].get(url)
        if not page or "text" not in page:
            raise JobTrackerError("not_captured", f"{url} was not read in this run yet: pass it "
                                  "without 'lines' or 'synonym' first")
        page_html = (self.ctx.folder / page["html"]).read_text(encoding="utf-8")
        posting = job_posting(page_html)
        if item.get("lines"):
            numbered_text = (self.ctx.folder / page["text"]).read_text(encoding="utf-8")
            first, last = item["lines"]
            description = cut_lines(numbered_text, first, last)
            fields = {k: " ".join(str(item[k]).split()) or None
                      for k in ("title", "company", "location") if item.get(k)}
            missing = [k for k in ("title", "company") if k not in fields]
            if missing:
                raise JobTrackerError("invalid_found", f"{url}: with 'lines', give the "
                                      f"posting's {' and '.join(missing)} as the page shows them")
            text = plain_text(page_html)
            for key in ("title", "company"):
                if fields[key].casefold() not in text.casefold():
                    raise JobTrackerError("invalid_found", f"{url}: the {key} "
                                          f"'{fields[key]}' is not on the captured page")
            if is_closed(posting, description, self.today):
                self.summary["closed"].append(url)
                return
            draft = self._draft(url, description=description,
                                country=self._country(fields.get("location"), []),
                                posted_at=_date(posting.get("datePosted")) if posting else None,
                                **fields)
            if self._rank(url, draft["company"]) == 0:
                self.summary["not_original"].append(url)
            self._keep(draft, synonym=bool(item.get("synonym")))
            return
        if posting is None:
            raise JobTrackerError("invalid_found", f"{url} has no posting data: pass 'lines' "
                                  "with 'synonym'")
        draft = self._from_json_ld(url, posting, plain_text(page_html))
        if draft:
            self._keep(draft, synonym=True)

    def _matches_place(self, location: str | None, country: str | None,
                       remote: bool) -> bool:
        if self._country(location, [country] if country else []):
            return True
        return remote or any(w in common.words(location or "") for w in REMOTE)

    def _lever(self, company: str, posting_id: str | None) -> None:
        base = f"https://api.lever.co/v0/postings/{company}"
        data = self._api(f"{base}/{posting_id}" if posting_id else f"{base}?mode=json")
        jobs = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
        for job in jobs:
            if not isinstance(job, dict) or not job.get("id"):
                continue
            categories = job.get("categories") or {}
            location = _text(categories.get("location"))
            remote = str(job.get("workplaceType") or "").lower() == "remote"
            if not posting_id and not self._matches_place(location, job.get("country"), remote):
                continue
            parts = [str(job.get("descriptionPlain") or "").strip()]
            for block in job.get("lists") or []:
                if isinstance(block, dict):
                    items = plain_text(str(block.get("content") or ""))
                    parts.append(f"{block.get('text') or ''}\n{items}".strip())
            parts.append(str(job.get("additionalPlain") or "").strip())
            created = job.get("createdAt")
            url = canonical(str(job.get("hostedUrl") or f"https://jobs.lever.co/{company}/"
                                                       f"{job['id']}"))
            draft = self._draft(
                url, title=_text(job.get("text")), company=company, location=location,
                country=self._country(location, [str(job.get("country") or "")]),
                posted_at=datetime.fromtimestamp(created / 1000, UTC).date().isoformat()
                if isinstance(created, int) else None,
                description="\n\n".join(p for p in parts if p),
                contract_type={"full-time": "full-time", "part-time": "part-time",
                               "contract": "contractor"}.get(
                                   str(categories.get("commitment") or "").lower()),
                site_workplace_type=job.get("workplaceType"),
                site_commitment=categories.get("commitment"),
                flags=[])
            if draft["posted_at"] and draft["posted_at"] < self.ctx.since:
                continue
            self._keep(draft, synonym=bool(posting_id))

    def _ashby(self, org: str, posting_id: str | None) -> None:
        data = self._api("https://api.ashbyhq.com/posting-api/job-board/"
                         f"{urllib.parse.quote(org)}?includeCompensation=true")
        jobs = (data or {}).get("jobs") if isinstance(data, dict) else None
        for job in jobs or []:
            if not isinstance(job, dict) or not job.get("id"):
                continue
            if posting_id and job["id"] != posting_id:
                continue
            if job.get("isListed") is False:
                continue
            address = ((job.get("address") or {}).get("postalAddress") or {})
            location = _text(job.get("location"))
            country = _text(address.get("addressCountry"))
            if not posting_id and not self._matches_place(
                    f"{location or ''} {country or ''}", None, bool(job.get("isRemote"))):
                continue
            url = canonical(str(job.get("jobUrl") or f"https://jobs.ashbyhq.com/{org}/"
                                                     f"{job['id']}"))
            draft = self._draft(
                url, title=_text(job.get("title")), company=org, location=location,
                country=self._country(location, [country] if country else []),
                posted_at=_date(job.get("publishedAt")),
                description=str(job.get("descriptionPlain") or "").strip()
                or plain_text(str(job.get("descriptionHtml") or "")),
                site_employment_type=job.get("employmentType"),
                site_remote=job.get("isRemote"))
            if draft["posted_at"] and draft["posted_at"] < self.ctx.since:
                continue
            self._keep(draft, synonym=bool(posting_id))

    def run(self, items: list[dict]) -> dict:
        self.summary["links"] = len(items)
        try:
            for item in items:
                if self.summary["capped"] or len(self.drafts) >= self.ctx.max_results:
                    self.summary["capped"] = True
                    break
                self._read_link(item)
        except common.Stop as stop:
            self.summary["stopped"] = {"reason": stop.reason, "detail": stop.detail}
        self.summary["suggest_provider"] = sorted(set(self.summary["suggest_provider"]))
        for host, info in self.state["refused_hosts"].items():
            self.summary["refused_hosts"].setdefault(host, info["reason"])
        return common.finish(self.paths, self.ctx, self.state, self.summary,
                             list(self.drafts.values()), self.seen)
