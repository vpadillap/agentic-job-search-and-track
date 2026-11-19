"""Glassdoor reader: the browsing and extraction part of providers/glassdoor.md.

One call searches one title in the profile's country with a headless Scrapling
stealth session (no cookies, no account; discarded after the call). The search
page's own "Show more jobs" button loads more results until the site shows no
more or the provider's cap is reached. The results come from the page's own data,
else its JSON-LD, its cards, or its posting links ("Similar jobs" never count); a
search page that cannot be read is loaded again, then ends only that title, and no
problem with a title stops the others. Each new posting's page is loaded and its
fields come from the page's structured data (`JobPosting`). The site's internal
endpoints are never called directly. A second call reads salary pages (up to three
titles, paced, with a cool-down after a refusal) and returns a salary evidence
draft. Pacing, the one-call lock, postings already stored, and stops are shared
with the other readers (`common`). What needs judgment is left to the agent.
"""
from __future__ import annotations

import json
import random
import re
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol

from .. import db, providers
from .. import profile as profile_service
from ..errors import JobTrackerError
from ..paths import Paths, slugify
from . import common

PROVIDER = "glassdoor"
LABEL = "Glassdoor"
SITE = "https://www.glassdoor.com"
FROM_AGE = (1, 3, 7, 14, 30)       # posting ages (days) Glassdoor's search offers
MIN_DESCRIPTION = 100              # shorter than this: no readable description
UNREADABLE_IN_A_ROW = 2            # unreadable postings in a row that end the title
SALARY_MIN_SECONDS = 20            # between salary pages, across calls
SALARY_COOLDOWNS = (15 * 60, 30 * 60, 60 * 60)   # after the 1st, 2nd, 3rd+ refusal in a row
SALARY_MAX_TITLES = 3
# Security checks Scrapling did not pass are throttles (common.CHALLENGE_TITLES); these
# pages are hard blocks.
BLOCK_MARKERS = ("Attention Required", "Access denied")
LOCALES = {"PE": "es-PE", "MX": "es-MX", "CO": "es-CO", "CL": "es-CL", "AR": "es-AR",
           "ES": "es-ES", "US": "en-US", "GB": "en-GB", "CA": "en-CA", "PT": "pt-PT",
           "BR": "pt-BR"}
SETTINGS_FILE = f"{PROVIDER}.json"
SEARCH_URL = re.compile(
    r"^https://(?:www\.)?glassdoor\.[a-z.]+/Job/(?P<segment>[^/?#]+)-SRCH_IL\.0,(?P<n>\d+)"
    r"_IN(?P<id>\d+)")


@dataclass
class SearchPage:
    status: int | None
    title: str
    html: str
    more: list[str] = field(default_factory=list)   # bodies of the "Show more" responses
    wall: bool = False                              # a sign-in prompt that would not close


class Fetcher(Protocol):
    def search(self, url: str, max_cards: int) -> SearchPage:
        """Load a search page and press "Show more jobs" until done or `max_cards`."""

    def page(self, url: str) -> tuple[int | None, str, str]:
        """Load one page: (HTTP status, page title, page HTML)."""

    def close(self) -> None: ...


# ── country, URLs ─────────────────────────────────────────────────────────

def from_age(days: int) -> int | None:
    """The smallest posting age Glassdoor offers that covers `days`; None beyond 30."""
    return next((value for value in FROM_AGE if days <= value), None)


def _keyword_slug(title: str) -> str:
    return slugify(title, max_length=120)


def _srch(place: str, loc_id: int, title: str) -> str:
    keyword = _keyword_slug(title)
    start = len(place) + 1
    return (f"{place}-{keyword}", f"SRCH_IL.0,{len(place)}_IN{loc_id}_KO{start},"
            f"{start + len(keyword)}")


def search_url(place: str, loc_id: int, title: str, days: int) -> str:
    head, srch = _srch(place, loc_id, title)
    age = from_age(days)
    return f"{SITE}/Job/{head}-jobs-{srch}.htm" + (f"?fromAge={age}" if age else "")


def salary_url(place: str, loc_id: int, title: str) -> str:
    head, srch = _srch(place, loc_id, title)
    return f"{SITE}/Salaries/{head}-salary-{srch}.htm"


def parse_search_url(url: str) -> dict:
    """The country id and place slug of a Glassdoor job-search URL the user pasted."""
    match = SEARCH_URL.match((url or "").strip())
    n = int(match.group("n")) if match else 0
    if not match or not 0 < n <= len(match.group("segment")):
        raise JobTrackerError(
            "invalid_search_url", "give a Glassdoor job-search URL such as "
            "https://www.glassdoor.com/Job/peru-data-engineer-jobs-SRCH_IL.0,4_IN189_KO5,18.htm")
    return {"id": int(match.group("id")), "place": match.group("segment")[:n],
            "from_url": url.strip()}


def _table_countries(text: str) -> dict[str, dict]:
    table = providers._countries_table(text) or {}
    found = {}
    for code, cells in table.items():
        if len(cells) >= 3 and cells[1].isdigit() and cells[2]:
            found[code] = {"id": int(cells[1]), "place": cells[2]}
    return found


def settings_path(paths: Paths) -> Path:
    return paths.home / "provider-settings" / SETTINGS_FILE


def _settings(paths: Paths) -> dict:
    path = settings_path(paths)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _write_settings(paths: Paths, data: dict) -> None:
    path = settings_path(paths)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _saved_countries(paths: Paths) -> dict[str, dict]:
    return {code: item for code, item in (_settings(paths).get("countries") or {}).items()
            if isinstance(item, dict) and isinstance(item.get("id"), int) and item.get("place")}


def _save_country(paths: Paths, country: str, item: dict) -> None:
    data = _settings(paths)
    data.setdefault("countries", {})[country] = item
    _write_settings(paths, data)


def resolve_country(paths: Paths, country: str | None, search_url_given: str | None) -> dict:
    """Glassdoor's id and place slug for the country: the provider file's table, the
    user's saved setting, or a search URL the user pasted (then saved for later)."""
    if search_url_given:
        item = parse_search_url(search_url_given)
        if country:
            _save_country(paths, country.upper(), item)
        return item
    code = (country or "").upper()
    if not code:
        raise JobTrackerError("missing_country", "The profile has no country. Set it in "
                              "/setup, or give a Glassdoor search URL with --search-url.")
    text = (providers.providers_dir() / f"{PROVIDER}.md").read_text(encoding="utf-8")
    item = _table_countries(text).get(code) or _saved_countries(paths).get(code)
    if item is None:
        raise JobTrackerError(
            "missing_country", f"Glassdoor's id for {code} is not known yet. Ask the user to "
            "search any title for their country on glassdoor.com in their own browser and "
            "paste the address of the results page; pass it with --search-url (it is saved, "
            "so this is asked once).", country=code)
    return item


# ── parsing ───────────────────────────────────────────────────────────────

def _title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.S | re.I)
    return " ".join(match.group(1).split()) if match else ""


def site_total(page_title: str) -> int | None:
    """'152 data engineer Jobs in Peru, …' -> 152."""
    match = re.match(r"\s*([\d,.]+)\s", page_title or "")
    return int(re.sub(r"[,.]", "", match.group(1))) if match else None


SIMILAR_JOBS = 'data-test="related-jobs-list"'   # "Similar jobs": not results of the search
NO_RESULTS_NOTICE = 'id="lrp-zrp'                 # "had limited or no results, but similar jobs…"
LINK = re.compile(r'(?:https://www\.glassdoor\.[a-z.]+)?/job-listing/[^"\'\s<>]*?[?&](?:amp;)?jl='
                  r'(\d+)[^"\'\s<>]*')


def _before_similar(html: str) -> str:
    cut = (html or "").find(SIMILAR_JOBS)
    return html[:cut] if cut >= 0 else html or ""


def _absolute(link: str) -> str:
    link = link.replace("&amp;", "&").replace("\\u0026", "&")
    return clean_url(link if link.startswith("http") else SITE + link)


def parse_cards(html: str) -> list[dict]:
    """The search's own cards, in order: listing id and the posting's link. Cards in
    the "Similar jobs" section that follows a search with few results are left out."""
    cards, ids = [], set()
    for item in re.finditer(r'<li\b[^>]*data-jobid="(\d+)"[^>]*>(.*?)</li>',
                            _before_similar(html), re.S):
        job_id = item.group(1)
        link = re.search(r'href="(https://www\.glassdoor\.[^"]*/job-listing/[^"]+)"', item.group(2))
        if job_id in ids or not link:
            continue
        ids.add(job_id)
        cards.append({"external_id": job_id, "url": _absolute(link.group(1))})
    return cards


def _links(html: str) -> dict[str, str]:
    """Every link to a posting page in `html`, by listing id, in order of appearance."""
    found: dict[str, str] = {}
    for match in LINK.finditer(html or ""):
        found.setdefault(match.group(1), _absolute(match.group(0)))
    return found


def _flight(html: str) -> str:
    """The page's Next.js data: the `self.__next_f.push([1, "…"])` strings, decoded
    and joined."""
    parts = []
    for chunk in re.finditer(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', html or "",
                             re.S):
        try:
            parts.append(json.loads(f'"{chunk.group(1)}"'))
        except ValueError:
            continue
    return "".join(parts)


def page_listings(html: str) -> list[dict] | None:
    """The search's results in the page's own data (`searchResultsData.jobListings.
    jobListings`), as {external_id, age_days, url}; None when the page has no such data.
    An empty list is an answer: the site found nothing for the search."""
    data = _flight(html)
    decoder = json.JSONDecoder()
    for anchor in re.finditer(r'"searchResultsData"\s*:\s*\{', data):
        start = data.find('"jobListings":[', anchor.end())
        if start < 0:
            continue
        try:
            items, _ = decoder.raw_decode(data, start + len('"jobListings":'))
        except ValueError:
            continue
        if not isinstance(items, list):
            continue
        listings = []
        for item in items:
            view = (item or {}).get("jobview") or {} if isinstance(item, dict) else {}
            header, job = view.get("header") or {}, view.get("job") or {}
            job_id = str(job.get("listingId") or "")
            if not job_id.isdigit() or job_id == "0":
                continue
            link = header.get("seoJobLink") or job.get("jobLink") or ""
            listings.append({
                "external_id": job_id,
                "age_days": header.get("ageInDays") if isinstance(header.get("ageInDays"),
                                                                  int) else None,
                "url": _absolute(link) if isinstance(link, str) and "job-listing" in link
                else None,
            })
        return listings
    return None


def json_ld_listings(html: str) -> list[str] | None:
    """Listing ids of a JSON-LD `ItemList` of postings before "Similar jobs"; None
    without one."""
    for block in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                             _before_similar(html), re.S):
        try:
            data = json.loads(block.group(1))
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if not isinstance(item, dict) or item.get("@type") != "ItemList":
                continue
            ids = []
            for element in item.get("itemListElement") or []:
                if not isinstance(element, dict):
                    continue
                inner = element.get("item")
                url = element.get("url") or (inner.get("url") if isinstance(inner, dict)
                                             else inner)
                match = LINK.search(url if isinstance(url, str) else "")
                if match:
                    ids.append(match.group(1))
            if ids:
                return ids
    return None


@dataclass
class Results:
    cards: list[dict]          # {external_id, url}, in the site's order
    source: str | None         # page-data, json-ld, cards, links; None: nothing read
    empty: bool                # the page itself says the search found nothing
    ages: dict[str, int]       # listing id -> age in days, from the page's data
    unlinked: int = 0          # results with no posting link anywhere on the page


def parse_results(html: str) -> Results:
    """The search's own results: from the page's data, else its JSON-LD list, else the
    cards, else links to posting pages. "Similar jobs" are never results."""
    links = _links(html)
    ages: dict[str, int] = {}
    data = page_listings(html)
    ids: list[str] | None = None
    source = None
    if data is not None:
        source, ids = "page-data", []
        for item in data:
            ids.append(item["external_id"])
            if item["url"]:
                links.setdefault(item["external_id"], item["url"])
            if item["age_days"] is not None:
                ages[item["external_id"]] = item["age_days"]
    else:
        ids = json_ld_listings(html)
        source = "json-ld" if ids else None
    if ids is None or (not ids and source != "page-data"):
        cards = parse_cards(html)
        if cards:
            return Results(cards, "cards", False, ages)
        head = _links(_before_similar(html))
        if head:
            return Results([{"external_id": i, "url": u} for i, u in head.items()], "links",
                           False, ages)
        return Results([], None, NO_RESULTS_NOTICE in (html or ""), ages)
    # The page's data and JSON-LD hold the first results only; those that "Show more
    # jobs" added are cards after them.
    ids = ids + [card["external_id"] for card in parse_cards(html)]
    cards, seen, unlinked = [], set(), 0
    for job_id in ids:
        if job_id in seen:
            continue
        seen.add(job_id)
        if job_id in links:
            cards.append({"external_id": job_id, "url": links[job_id]})
        else:
            unlinked += 1
    empty = source == "page-data" and not ids
    return Results(cards, source, empty, ages, unlinked)


def clean_url(url: str) -> str:
    """The posting link without tracking parameters (keeps `jl`, the listing id)."""
    parts = urllib.parse.urlsplit(url)
    query = {k: v for k, v in urllib.parse.parse_qs(parts.query).items() if k == "jl"}
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query, doseq=True),
                                                  fragment=""))


def page_ages(html: str) -> dict[str, int]:
    """Posting ages (days) of the first results, from the page's embedded data, where
    each posting's `ageInDays` comes before its `listingId`."""
    ages: dict[str, int] = {}
    for found in re.finditer(r'\\"ageInDays\\":(\d+).{0,8000}?\\"listingId\\":(\d+)', html or "",
                             re.S):
        ages.setdefault(found.group(2), int(found.group(1)))
    return ages


def parse_more(bodies: list[str]) -> tuple[dict[str, dict], int | None, int]:
    """Card details from the "Show more" responses, by listing id, the site's total, and
    how many responses did not parse (their cards are still on the page)."""
    details: dict[str, dict] = {}
    total = None
    unreadable = 0
    for body in bodies:
        try:
            listings = json.loads(body)["data"]["jobListings"]
        except (ValueError, KeyError, TypeError):
            listings = None
        if not isinstance(listings, dict):
            unreadable += 1
            continue
        total = listings.get("totalJobsCount", total)
        for item in listings.get("jobListings") or []:
            view = item.get("jobview") or {}
            header, job = view.get("header") or {}, view.get("job") or {}
            job_id = str(job.get("listingId") or "")
            if job_id:
                attributes = (header.get("indeedJobAttribute") or {}).get(
                    "extractedJobAttributes") or []
                details[job_id] = {
                    "age_days": header.get("ageInDays"),
                    "attributes": [str(a.get("value")) for a in attributes if a.get("value")],
                }
    return details, total, unreadable


def _json_ld(html: str, kind: str) -> dict | None:
    for block in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                             html or "", re.S):
        try:
            data = json.loads(block.group(1))
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and item.get("@type") == kind:
                return item
    return None


class _Text(HTMLParser):
    BLOCKS = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr",
              "table", "section"}

    HIDDEN = {"script", "style", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.HIDDEN:
            self.hidden += 1
        if tag in self.BLOCKS:
            self.parts.append("\n")
        if tag == "li":
            self.parts.append("- ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.HIDDEN:
            self.hidden = max(0, self.hidden - 1)
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def plain_text(html_text: str) -> str:
    """HTML as plain text: blocks become lines, spaces collapsed, at most one blank line."""
    parser = _Text()
    parser.feed(html_text or "")
    lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _salary_hint(posting: dict) -> dict | None:
    salary = posting.get("baseSalary")
    if not isinstance(salary, dict):
        return None
    value = salary.get("value") if isinstance(salary.get("value"), dict) else {}
    return {"currency": salary.get("currency") or posting.get("salaryCurrency"),
            "min": value.get("minValue"), "max": value.get("maxValue"),
            "unit": value.get("unitText")}


def parse_posting(html: str) -> dict | None:
    """The fields of a posting page from its `JobPosting` data; None without it."""
    posting = _json_ld(html, "JobPosting")
    if posting is None:
        return None
    organization = posting.get("hiringOrganization") or {}
    places = posting.get("jobLocation") or []
    place = (places[0] if isinstance(places, list) and places else places) or {}
    address = place.get("address") or {} if isinstance(place, dict) else {}
    location = ", ".join(str(part) for part in (address.get("addressLocality"),
                                                address.get("addressRegion")) if part) or None
    posted = str(posting.get("datePosted") or "")[:10] or None
    employment = posting.get("employmentType")
    return {
        "title": " ".join(str(posting.get("title") or "").split()) or None,
        "company": " ".join(str(organization.get("name") or "").split()) or None
        if isinstance(organization, dict) else None,
        "location": location, "posted_at": posted,
        "description": plain_text(str(posting.get("description") or "")),
        "employment_type": employment if isinstance(employment, str) else (
            ", ".join(map(str, employment)) if isinstance(employment, list) else None),
        "salary": _salary_hint(posting),
    }


CONTRACT_TYPES = {"tiempo completo": "full-time", "full-time": "full-time",
                  "integral/full-time": "full-time", "período integral": "full-time",
                  "periodo integral": "full-time", "medio tiempo": "part-time",
                  "part-time": "part-time", "meio período": "part-time",
                  "contract": "contractor", "contractor": "contractor",
                  "freelance": "contractor"}


def contract(attributes: list[str]) -> str | None:
    """The contract type, only when the site's attributes say it plainly and agree."""
    found = {CONTRACT_TYPES[a.casefold()] for a in attributes if a.casefold() in CONTRACT_TYPES}
    return found.pop() if len(found) == 1 else None


def _draft(card: dict, posting: dict, extra: dict, ctx: common.Context) -> dict:
    return {
        "provider": PROVIDER, "external_id": card["external_id"], "url": card["url"],
        "title": posting["title"], "company": posting["company"],
        "location": posting["location"], "country": ctx.country,
        "posted_at": posting["posted_at"], "description": posting["description"],
        "seniority": None, "contract_type": contract(extra.get("attributes") or []),
        # What the site states (hints for the agent's reading, never imported as they are):
        "site_attributes": extra.get("attributes") or [],
        "site_employment_type": posting["employment_type"],
        "site_salary": posting["salary"],
        # The agent's reading (see providers/glassdoor.md):
        "work_mode": None, "work_mode_detail": None, "language": None, "flags": [],
        "published_salary": None,
    }


# ── salary page ───────────────────────────────────────────────────────────

PERIODS = {"P1M": "month", "P1Y": "year"}


def parse_salary(html: str, url: str, country: str, today: date) -> dict:
    """One salary evidence draft (or no data) from a salary page's structured data."""
    occupation = _json_ld(html, "Occupation")
    distributions = (occupation or {}).get("estimatedSalary") or []
    first = distributions[0] if isinstance(distributions, list) and distributions else None
    if not isinstance(first, dict) or first.get("@type") != "MonetaryAmountDistribution":
        return {"data": False, "reason": "the salary page has no salary distribution", "url": url}
    period = PERIODS.get(str(first.get("duration")))
    low, high = first.get("percentile25"), first.get("percentile75")
    if period is None or not isinstance(low, int | float) or not isinstance(high, int | float):
        return {"data": False, "url": url,
                "reason": f"unusable distribution (duration {first.get('duration')!r})"}
    text = plain_text(html)
    sample = re.search(r"\b([\d,]+)\s+salaries\b", text, re.I)
    dates = []
    for found in re.findall(r"submitted on ([A-Z][a-z]{2} \d{1,2}, \d{4})", text):
        try:
            dates.append(datetime.strptime(found, "%b %d, %Y").date())
        except ValueError:
            continue
    observed = max((d for d in dates if d <= today), default=today)
    pay = first.get("name") or "pay"
    return {
        "data": True,
        "evidence": {
            "source": "Glassdoor", "url": url,
            "amount_min": round(low), "amount_max": round(high),
            "currency": str(first.get("currency") or ""), "period": period,
            "sample_size": int(sample.group(1).replace(",", "")) if sample else None,
            "observed_on": observed.isoformat(), "country": country,
            "summary": (f"Glassdoor {pay} pay for '{(occupation or {}).get('name')}': most likely "
                        f"range (25th-75th percentile) {round(low)}-{round(high)}, median "
                        f"{first.get('median')}, 10th-90th {first.get('percentile10')}-"
                        f"{first.get('percentile90')} {first.get('currency')} per {period}"),
        },
        # The agent adds: basis, level, posting_id or research, and checks comparability.
    }


# ── the real fetcher ──────────────────────────────────────────────────────

class ScraplingFetcher:
    """A headless Scrapling stealth session with no cookies and no account."""

    MORE = "button[data-test='load-more']"
    CARDS = "li[data-test='jobListing']"
    CLOSE = "[data-test='auth-modal-close-button']"

    def __init__(self, locale: str, pause: float) -> None:
        try:
            from scrapling.fetchers import StealthySession
        except ImportError as error:
            raise JobTrackerError(
                "missing_dependency", "Glassdoor needs Scrapling: run jt providers install "
                "glassdoor") from error
        self._pause = pause
        self.last_headers: dict = {}
        import logging

        logging.getLogger("scrapling").setLevel(logging.WARNING)  # keep the CLI output clean
        try:
            self._session = StealthySession(headless=True, solve_cloudflare=True, locale=locale,
                                            retries=1,  # retries go through common.attempt
                                            timeout=90000, wait=3000)
            self._session.__enter__()
        except Exception as error:  # the browser itself is not installed
            raise JobTrackerError(
                "missing_dependency", f"Scrapling's browser is not ready ({error}); run: "
                "jt providers install glassdoor") from error

    def _dismiss(self, page) -> bool:
        """Close a sign-up prompt without choosing anything; False when it stays open."""
        if not page.locator("dialog[open]").count():
            return True
        page.keyboard.press("Escape")
        page.wait_for_timeout(1000)
        if page.locator("dialog[open]").count() and page.locator(self.CLOSE).count():
            page.locator(self.CLOSE).first.click()
            page.wait_for_timeout(1000)
        return not page.locator("dialog[open]").count()

    def search(self, url: str, max_cards: int) -> SearchPage:
        result = SearchPage(None, "", "")

        def keep(response) -> None:
            if "jobSearchResultsQuery" in response.url:
                try:
                    result.more.append(response.text())
                except Exception:  # noqa: BLE001  the body is gone; the cards still count
                    pass

        def more(page):
            page.on("response", keep)
            cards = page.locator(self.CARDS)
            while cards.count() < max_cards:
                page.wait_for_timeout(int(self._pause * 1000))
                if not self._dismiss(page):
                    result.wall = True
                    break
                button = page.locator(self.MORE)
                if not button.count():
                    break
                before = cards.count()
                button.first.scroll_into_view_if_needed()
                button.first.click()
                page.wait_for_timeout(6000)
                if not self._dismiss(page):
                    result.wall = True
                    break
                if cards.count() <= before:
                    break
            return page

        response = self._session.fetch(url, page_action=more)
        result.status, result.html = response.status, response.html_content
        result.title = _title(result.html)
        return result

    def page(self, url: str) -> tuple[int | None, str, str]:
        response = self._session.fetch(url)
        try:
            self.last_headers = dict(response.headers or {})
        except Exception:  # noqa: BLE001  headers are only used to honour Retry-After
            self.last_headers = {}
        return response.status, _title(response.html_content), response.html_content

    def close(self) -> None:
        self._session.__exit__(None, None, None)


# ── the reader ────────────────────────────────────────────────────────────

FetcherFactory = Callable[[str, float], Fetcher]


def _blocked(status: int | None, title: str, url: str,
             retry_after: float | None = None) -> None:
    """A hard block (403, a block page) stops Glassdoor for the run; a throttle (429, a
    security check that was not passed) is waited out (common.attempt)."""
    if status == 403 or any(marker in title for marker in BLOCK_MARKERS):
        raise common.Stop("blocked", f"{status} '{title}' on {url}")
    if common.soft_status(status, retry_after) or common.is_challenge(title):
        raise common.Throttle(f"{status} '{title}' on {url}", retry_after)


def read(paths: Paths, run_id: int, title: str, location: str | None = None, *,
         search_url_given: str | None = None, fetcher: FetcherFactory = ScraplingFetcher,
         clock: Callable[[], float] = time.time,
         sleep: Callable[[float], None] = time.sleep,
         rand: Callable[[], float] = random.random) -> dict:
    """Search one title and write the drafts of its new postings. Returns a summary.
    `location` is not used: Glassdoor is searched for the whole country."""
    title = " ".join((title or "").split())
    if not title:
        raise JobTrackerError("invalid_title", "give the title to search with --title")
    with db.session(paths) as conn:
        ctx = common.context(conn, paths, run_id, PROVIDER, LABEL, now=clock())
    country = resolve_country(paths, ctx.country, search_url_given)
    ctx.folder.mkdir(parents=True, exist_ok=True)
    lock = common.lock(ctx, LABEL, clock())
    try:
        if common.already_done(ctx, title):
            return common.done_summary(PROVIDER, title)
        return _read(paths, ctx, title, country, fetcher, clock, sleep, rand)
    finally:
        lock.unlink(missing_ok=True)


class TitleProblem(Exception):
    """End this title only: the provider goes on with the next title of the run."""

    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(detail)
        self.kind, self.detail = kind, detail


def _record_title(state: dict, summary: dict, title: str, problem: TitleProblem | None) -> None:
    """Remember how a title that read something ended, and flag a likely site change: this
    title and every earlier one that read something ended with the same problem (two at
    least). Titles with no results are neither evidence for nor against."""
    kind = problem.kind if problem else None
    outcomes = state.setdefault("title_outcomes", [])
    outcomes.append(kind)
    if problem:
        state.setdefault("title_problems", []).append(
            {"title": title, "kind": kind, "detail": problem.detail})
        summary["title_problem"] = {"kind": kind, "detail": problem.detail}
    summary["site_may_have_changed"] = bool(kind) and len(outcomes) >= 2 and all(
        outcome == kind for outcome in outcomes)


def _read(paths: Paths, ctx: common.Context, title: str, country: dict,
          fetcher_factory: FetcherFactory, clock: Callable[[], float],
          sleep: Callable[[float], None], rand: Callable[[], float]) -> dict:
    state = common.load_state(ctx)
    handled = set(state["job_ids"])
    summary: dict = {"provider": PROVIDER, "title": title, "requests": 0, "retries": 0,
                     "site_total": None, "listed": 0, "cards": 0, "outside_window": 0,
                     "duplicate_in_run": 0, "already_seen": 0, "new": 0, "unreadable": [],
                     "no_results": False, "title_problem": None,
                     "site_may_have_changed": False, "drafts_path": None, "stopped": None}
    drafts: list[dict] = []
    seen: list[dict] = []
    fetcher: Fetcher | None = None
    captures: list[str] = []

    def pace() -> None:
        wait = state["last_request_at"] + ctx.min_seconds - clock()
        if state["last_request_at"] and wait > 0:
            sleep(wait)
        state["requests"] += 1
        summary["requests"] += 1

    def done(capture: str, suffix: str) -> None:
        state["last_request_at"] = clock()
        name = f"{PROVIDER}-{state['requests']}.{suffix}"
        (ctx.folder / name).write_text(capture, encoding="utf-8")
        captures.append(name)
        common.save_state(ctx, state)

    def keep(job_id: str) -> None:
        handled.add(job_id)
        state["job_ids"].append(job_id)

    def retried(request: Callable[[], object]):
        return common.attempt(request, state, min_seconds=ctx.min_seconds, clock=clock,
                              sleep=sleep, rand=rand)

    def search_once(url: str) -> SearchPage:
        assert fetcher is not None
        pace()
        try:
            found = fetcher.search(url, ctx.max_results)
        except Exception as error:  # the session could not load the page
            raise common.Stop("error", f"the browser failed on {url}: {error}") from error
        finally:
            state["last_request_at"] = clock()
        done(found.html, "html")
        if found.more:
            (ctx.folder / f"{PROVIDER}-{state['requests']}-more.json").write_text(
                "\n".join(found.more), encoding="utf-8")
        _blocked(found.status, found.title, url)
        return found

    def page_once(url: str) -> tuple[int | None, str, str]:
        assert fetcher is not None
        pace()
        try:
            status, page_title, html = fetcher.page(url)
        except Exception as error:
            raise common.Stop("error", f"the browser failed opening {url}: "
                              f"{error}") from error
        finally:
            state["last_request_at"] = clock()
        done(html, "html")
        _blocked(status, page_title, url)
        return status, page_title, html

    def search(url: str) -> tuple[SearchPage, Results]:
        found = retried(lambda: search_once(url))
        if found.wall:
            raise common.Stop("blocked", f"a sign-in prompt that would not close on {url}")
        return found, parse_results(found.html)

    url = search_url(country["place"], country["id"], title, ctx.days)
    try:
        fetcher = fetcher_factory(LOCALES.get((ctx.country or "").upper(), "en-US"),
                                  float(ctx.min_seconds))
        found, results = search(url)
        if not results.cards and not results.empty and site_total(found.title) != 0:
            # Nothing readable and no sign of "no results": load the page once more.
            summary["retries"] += 1
            found, results = search(url)
        details, total, more_unreadable = parse_more(found.more)
        if more_unreadable:
            summary["show_more_unreadable"] = more_unreadable
        for job_id, age in {**page_ages(found.html), **results.ages}.items():
            details.setdefault(job_id, {}).setdefault("age_days", age)
        summary["site_total"] = total or site_total(found.title)
        cards = results.cards
        summary["listed"] = len(cards)
        summary["source"] = results.source
        if results.unlinked:
            summary["unlinked"] = results.unlinked
        if not cards:
            if results.empty or summary["site_total"] == 0:
                # Glassdoor's "limited or no results" page can say "1 job" in its title
                # while it lists none and shows only "Similar jobs".
                summary["no_results"] = True
                return common.finish(paths, ctx, state, summary, drafts, seen, title,
                                     now=clock())
            raise TitleProblem("no_results_read", f"no results could be read on {url} "
                               f"('{found.title}'), also after loading it again; the page is "
                               f"saved as {captures[-1]}")
        unreadable_row = 0
        for card in cards[:ctx.max_results]:
            summary["cards"] += 1
            job_id = card["external_id"]
            extra = details.get(job_id, {})
            age = extra.get("age_days")
            if isinstance(age, int) and (date.fromisoformat(ctx.since)
                                          > date.today() - timedelta(days=age)):
                summary["outside_window"] += 1
                continue
            if job_id in handled:
                summary["duplicate_in_run"] += 1
                continue
            if job_id in ctx.known:
                seen.append(card)
                keep(job_id)
                continue
            _, _, html = retried(lambda card=card: page_once(card["url"]))
            keep(job_id)   # only now: a throttled posting is opened after a cool-down
            posting = parse_posting(html)
            if posting is None or len(posting["description"]) < MIN_DESCRIPTION:
                summary["unreadable"].append(job_id)
                unreadable_row += 1
                if unreadable_row >= UNREADABLE_IN_A_ROW:
                    raise TitleProblem("no_description", f"{UNREADABLE_IN_A_ROW} postings in a "
                                       f"row without a readable description (last "
                                       f"{card['url']})")
                continue
            unreadable_row = 0
            if posting["posted_at"] and posting["posted_at"] < ctx.since:
                summary["outside_window"] += 1
                continue
            drafts.append(_draft(card, posting, extra, ctx))
        _record_title(state, summary, title, None)
    except TitleProblem as problem:
        _record_title(state, summary, title, problem)
    except common.Stop as stop:
        summary["stopped"] = common.stopped(stop)
    finally:
        if fetcher is not None:
            fetcher.close()
    return common.finish(paths, ctx, state, summary, drafts, seen, title, now=clock())


# ── salary pages: pacing and a cool-down across calls ────────────────────

def _header(headers: dict, name: str) -> str | None:
    return next((str(v) for k, v in (headers or {}).items() if str(k).lower() == name), None)


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat(timespec="seconds")


def _throttled(state: dict, now: float, url: str | None, blocked: bool = False) -> dict:
    left = max(0.0, state["cooldown_until"] - now)
    return {"data": False, "throttled": True, "blocked": blocked, "url": url,
            "reason": state.get("last_detail") or "Glassdoor refused a salary page",
            "resume_after": _iso(state["cooldown_until"]),
            "minutes_left": int(-(-round(left) // 60))}


def _titles(titles: str | list[str] | None) -> list[str]:
    given = [titles] if isinstance(titles, str) else list(titles or [])
    found: list[str] = []
    for title in given:
        title = " ".join((title or "").split())
        if title and title.casefold() not in {t.casefold() for t in found}:
            found.append(title)
    if not found:
        raise JobTrackerError("invalid_title", "give the title with --title")
    if len(found) > SALARY_MAX_TITLES:
        raise JobTrackerError("invalid_title", f"give at most {SALARY_MAX_TITLES} titles "
                              "(--title repeated)")
    return found


def salary(paths: Paths, titles: str | list[str], *, search_url_given: str | None = None,
           fetcher: FetcherFactory = ScraplingFetcher, today: date | None = None,
           clock: Callable[[], float] = time.time,
           sleep: Callable[[float], None] = time.sleep,
           rand: Callable[[], float] = random.random) -> dict:
    """The salary page for up to three titles (tried in order until one has data) in the
    profile's country, as one evidence draft. A throttle is waited out as for searches
    (common.attempt); a refusal that remains starts a salary cool-down, kept across calls,
    during which no salary page is opened. Salary pages are paced across calls."""
    titles = _titles(titles)
    with db.session(paths) as conn:
        active = profile_service.get_active(conn) or {}
    code = str(active.get("country") or "").upper() or None
    country = resolve_country(paths, code, search_url_given)
    state = {"last_request_at": 0.0, "cooldown_until": None, "throttles": 0,
             "last_detail": None, **(_settings(paths).get("salary") or {})}

    def save() -> None:
        data = _settings(paths)
        data["salary"] = state
        _write_settings(paths, data)

    if state["cooldown_until"] and clock() < state["cooldown_until"]:
        result = _throttled(state, clock(),
                            salary_url(country["place"], country["id"], titles[0]))
        result["tried"] = []
        return result
    session = fetcher(LOCALES.get(code or "", "en-US"), float(SALARY_MIN_SECONDS))
    retries: dict = {"retries": 0}
    tried: list[dict] = []
    result: dict = {}

    def once(url: str) -> str:
        wait = state["last_request_at"] + SALARY_MIN_SECONDS - clock()
        if state["last_request_at"] and wait > 0:
            sleep(wait)
        try:
            status, page_title, html = session.page(url)
        finally:
            state["last_request_at"] = clock()
            save()
        asked = common.parse_retry_after(
            _header(getattr(session, "last_headers", None) or {}, "retry-after"), clock())
        _blocked(status, page_title, url, asked)
        return html

    try:
        for title in titles:
            url = salary_url(country["place"], country["id"], title)
            try:
                html = common.attempt(lambda url=url: once(url), retries,
                                      min_seconds=SALARY_MIN_SECONDS, clock=clock,
                                      sleep=sleep, rand=rand)
            except common.Stop as stop:
                # Still throttled after waiting, or blocked: cool down; no further title.
                state["throttles"] = int(state.get("throttles") or 0) + 1
                step = SALARY_COOLDOWNS[min(state["throttles"], len(SALARY_COOLDOWNS)) - 1]
                state["cooldown_until"] = clock() + max(step, stop.retry_after or 0)
                state["last_detail"] = stop.detail
                save()
                result = _throttled(state, clock(), url, blocked=stop.reason != "throttled")
                tried.append({"title": title, "url": url, "data": False,
                              "reason": stop.detail})
                break
            state.update(throttles=0, cooldown_until=None, last_detail=None)
            save()
            result = parse_salary(html, url, code or "", today or date.today())
            tried.append({"title": title, "url": url, "data": result["data"],
                          "reason": result.get("reason")})
            if result["data"]:
                break
    finally:
        session.close()
    result["tried"] = tried
    return result
