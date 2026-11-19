"""Computrabajo job search, as `providers/computrabajo.md` describes it.

Plain HTTP, logged out, no cookies: the country's search page
(`<cc>.computrabajo.com/trabajo-de-<title>?pubdate=<N>&by=publicationtime&p=<page>`), 20
cards a page, then each new posting's page for its `JobPosting` structured data (the
complete description, the publication date, the stated salary). A republished posting
counts: the card's date (its latest publication) decides the window, and the first
publication date is kept as a hint.
"""
from __future__ import annotations

import html as htmllib
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import date, timedelta

from .. import db
from ..errors import JobTrackerError
from ..paths import Paths, slugify
from . import common
from .glassdoor import plain_text as _html_text


def plain_text(fragment: str) -> str:
    """HTML (also when it comes escaped, as `&lt;br/&gt;`) as plain text with lines."""
    if "&lt;" in fragment:
        fragment = htmllib.unescape(fragment)
    return _html_text(fragment)

PROVIDER = "computrabajo"
LABEL = "Computrabajo"
COUNTRIES = ("PE", "MX", "CO", "CL", "AR", "EC")
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/131.0 Safari/537.36")
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "es-419,es;q=0.9"}
TIMEOUT_SECONDS = 30
PAGE_SIZE = 20
PUBDATES = (1, 3, 7, 15, 30)       # posting ages the search offers, in days
UNREADABLE = (404, 410)            # a posting removed since it was listed
REMOVED = re.compile(r"oferta ya no est(?:á|&#xE1;|&aacute;) disponible", re.I)
CONTRACTS = {"FULL_TIME": "full-time", "PART_TIME": "part-time", "CONTRACTOR": "contractor"}

Fetch = Callable[[str], tuple]
_Stop = common.Stop


def fetch(url: str) -> tuple[int, bytes, str | None, str | None]:
    """GET without cookies: (status, body, final address, Retry-After)."""
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, response.read(), response.geturl(), None
    except urllib.error.HTTPError as error:
        return error.code, error.read(), None, error.headers.get("Retry-After")


def site(country: str) -> str:
    return f"https://{country.lower()}.computrabajo.com"


def pubdate(days: int) -> int | None:
    """The smallest posting age the search offers that covers `days`; None beyond 30."""
    return next((value for value in PUBDATES if days <= value), None)


def search_url(country: str, title: str, days: int, page: int) -> str:
    query = {"by": "publicationtime"}
    age = pubdate(days)
    if age:
        query["pubdate"] = str(age)
    if page > 1:
        query["p"] = str(page)
    return (f"{site(country)}/trabajo-de-{slugify(title, max_length=80)}?"
            + urllib.parse.urlencode(query))


# ── search page ───────────────────────────────────────────────────────────

def _text(fragment: str) -> str:
    return " ".join(htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def card_date(text: str, today: date) -> str | None:
    """"Hace 2 horas", "Hace 30 minutos", "Ayer", "Hace 3 días" → a calendar date."""
    lowered = text.casefold()
    if re.search(r"hace\s+\d+\s+(minuto|hora)", lowered) or lowered.startswith("hoy"):
        return today.isoformat()
    if lowered.startswith("ayer"):
        return (today - timedelta(days=1)).isoformat()
    days = re.search(r"hace\s+(\d+)\s+d[ií]a", lowered)
    if days:
        return (today - timedelta(days=int(days.group(1)))).isoformat()
    return None


def parse_search(page: str, country: str, today: date) -> list[dict]:
    """The cards of a search page: id, link, title, company, place, work mode text, date
    of the latest publication, and the salary the card states."""
    cards = []
    for article in re.findall(r"<article\b.*?</article>", page, re.S):
        found = re.search(r"data-id=['\"]([0-9A-F]{16,})['\"]", article)
        link = re.search(r'<a[^>]*class="[^"]*js-o-link[^"]*"[^>]*href="([^"#]+)[^"]*"[^>]*>'
                         r"(.*?)</a>", article, re.S)
        if not found or not link:
            continue
        company = re.search(r'offer-grid-article-company-url[^>]*>(.*?)</a>', article, re.S) \
            or re.search(r'<p class="dFlex[^"]*"[^>]*>(.*?)</p>', article, re.S)
        place = re.search(r'<p class="fs16[^"]*">\s*<span class="mr10">(.*?)</span>', article,
                          re.S)
        mode = re.search(r'i_home_office"></span>(.*?)</span>', article, re.S)
        when = re.search(r'<p class="fs13 fc_aux[^"]*">(.*?)</p>', article, re.S)
        salary = re.search(r'i_salary"></span>(.*?)</span>', article, re.S)
        cards.append({
            "external_id": found.group(1),
            "url": urllib.parse.urljoin(site(country), link.group(1)),
            "title": _text(link.group(2)) or None,
            "company": re.sub(r"^\d+,\d\s+", "", _text(company.group(1))) if company else None,
            "location": _text(place.group(1)) if place else None,
            "work_mode_text": _text(mode.group(1)) if mode else None,
            "date_text": _text(when.group(1)) if when else None,
            "posted_at": card_date(_text(when.group(1)), today) if when else None,
            "salary_text": _text(salary.group(1)) if salary else None,
        })
    return cards


# ── posting page ──────────────────────────────────────────────────────────

def _job_posting(page: str) -> dict | None:
    for block in re.findall(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", page, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            item = stack.pop(0)
            if isinstance(item, dict):
                if item.get("@type") == "JobPosting":
                    return item
                stack.extend(v for v in item.values() if isinstance(v, dict | list))
            elif isinstance(item, list):
                stack.extend(item)
    return None


def _page_posting(page: str) -> dict | None:
    """A posting without `JobPosting` data (a confidential company's): its description
    block (`div-link="oferta"`): the tags, then the description and requirements."""
    block = re.search(r'div-link="oferta"[^>]*>(.*?)(?:<p class="fc_aux fs13 mbB|'
                      r'<div class="posSticky_m)', page, re.S)
    if not block:
        return None
    body = block.group(1)
    tags = [_text(t) for t in re.findall(r'<span class="tag base[^"]*">(.*?)</span>', body,
                                         re.S)]
    text = re.sub(r'<h2[^>]*>.*?</h2>|<div class="mbB">.*?</div>', "", body, count=2,
                  flags=re.S)
    title = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    salary = next((t for t in tags if re.search(r"\d", t) and re.search(r"\$|S/", t)), None)
    return {
        "title": _text(title.group(1)) if title else None, "company": None,
        "date_posted": None, "employment_type": None, "category": None,
        "description": plain_text(text), "salary": {"text": salary} if salary else None,
        "tags": tags,
    }


def parse_posting(page: str) -> dict | None:
    """A posting's fields from its `JobPosting`, else from its description block; None
    without either."""
    job = _job_posting(page)
    if job is None:
        return _page_posting(page)
    pay = job.get("baseSalary") if isinstance(job.get("baseSalary"), dict) else {}
    value = pay.get("value") if isinstance(pay.get("value"), dict) else {}
    amount = value.get("value")
    salary = None
    if isinstance(amount, int | float) and amount > 0:   # 0 is "A convenir"
        salary = {"currency": pay.get("currency") or job.get("salaryCurrency"),
                  "min": amount, "max": amount, "unit": value.get("unitText")}
    organization = job.get("hiringOrganization") or {}
    return {
        "title": " ".join(str(job.get("title") or "").split()) or None,
        "company": " ".join(str(organization.get("name") or "").split()) or None
        if isinstance(organization, dict) else None,
        "date_posted": str(job.get("datePosted") or "")[:10] or None,
        "employment_type": job.get("employmentType"),
        "category": job.get("industry"),
        "description": plain_text(str(job.get("description") or "")),
        "salary": salary, "tags": [],
    }


def _draft(card: dict, posting: dict, ctx: common.Context) -> dict:
    first = posting["date_posted"]
    latest = max(filter(None, (card.get("posted_at"), first)), default=None)
    return {
        "provider": PROVIDER, "external_id": card["external_id"], "url": card["url"],
        "title": posting["title"] or card["title"], "company": posting["company"]
        or card["company"], "location": card["location"], "country": ctx.country,
        "posted_at": latest, "description": posting["description"],
        "seniority": None, "contract_type": CONTRACTS.get(str(posting["employment_type"])),
        # What the site states (hints for the agent's reading, never imported as they are):
        "site_first_posted_at": first if first and latest and first < latest else None,
        "site_date_text": card.get("date_text"),
        "site_work_mode": card.get("work_mode_text"),
        "site_category": posting["category"],
        "site_tags": posting["tags"],
        "site_salary": posting["salary"] or (
            {"text": card["salary_text"]} if card.get("salary_text") else None),
        # The agent's reading (see providers/computrabajo.md):
        "work_mode": None, "work_mode_detail": None, "language": None, "flags": [],
        "published_salary": None,
    }


# ── the call ──────────────────────────────────────────────────────────────

def _check(status: int, url: str, retry_after: float | None = None) -> None:
    if common.soft_status(status, retry_after):
        raise common.Throttle(f"{status} {url}", retry_after)
    if status == 403:
        raise _Stop("blocked", f"403 on {url}")
    if status != 200:
        raise _Stop("error", f"{status} {url}")


def read(paths: Paths, run_id: int, title: str, location: str | None = None, *,
         fetch: Fetch = fetch, today: date | None = None,
         clock: Callable[[], float] = time.time, sleep: Callable[[float], None] = time.sleep,
         rand: Callable[[], float] = random.random) -> dict:
    """Search one title in the profile's country and write the drafts of its new
    postings. `location` is not used: Computrabajo is searched for the whole country."""
    title = " ".join((title or "").split())
    if not title:
        raise JobTrackerError("invalid_title", "give the title to search with --title")
    with db.session(paths) as conn:
        ctx = common.context(conn, paths, run_id, PROVIDER, LABEL, now=clock())
    if (ctx.country or "") not in COUNTRIES:
        raise JobTrackerError("other_country", f"Computrabajo is read only in "
                              f"{', '.join(COUNTRIES)}; the profile's country is {ctx.country}")
    ctx.folder.mkdir(parents=True, exist_ok=True)
    lock = common.lock(ctx, LABEL, clock())
    try:
        if common.already_done(ctx, common.title_key(title, None)):
            return common.done_summary(PROVIDER, title)
        return _read(paths, ctx, title, fetch, today or date.today(), clock, sleep, rand)
    finally:
        lock.unlink(missing_ok=True)


def _read(paths: Paths, ctx: common.Context, title: str, fetch: Fetch, today: date,
          clock: Callable[[], float], sleep: Callable[[float], None],
          rand: Callable[[], float]) -> dict:
    state = common.load_state(ctx)
    key = common.title_key(title, None)
    done_pages = common.progress(state, key)["pages"]
    handled = set(state["job_ids"])
    summary: dict = {"provider": PROVIDER, "title": title, "requests": 0, "pages": 0,
                     "cards": 0, "outside_window": 0, "duplicate_in_run": 0, "already_seen": 0,
                     "new": 0, "republished": 0, "unreadable": [], "drafts_path": None,
                     "stopped": None, "title_problem": None, "title_retries": 0}
    drafts: list[dict] = []
    seen: list[dict] = []
    max_pages = max(1, -(-ctx.max_results // PAGE_SIZE))

    def get(url: str) -> tuple[int, str, float | None]:
        wait = state["last_request_at"] + ctx.min_seconds - clock()
        if state["last_request_at"] and wait > 0:
            sleep(wait)
        state["requests"] += 1
        summary["requests"] += 1
        try:
            status, body, _, *rest = fetch(url)
        except (urllib.error.URLError, OSError) as error:
            raise _Stop("error", f"network error ({error}) on {url}") from error
        finally:
            state["last_request_at"] = clock()
            common.save_state(ctx, state)
        (ctx.folder / f"{PROVIDER}-{state['requests']}.html").write_bytes(body)
        return (status, body.decode("utf-8", "replace"),
                common.parse_retry_after(rest[0] if rest else None, clock()))

    def checked(url: str, passing: tuple[int, ...] = ()) -> tuple[int, str]:
        def once() -> tuple[int, str]:
            status, text, retry_after = get(url)
            if status not in passing:
                _check(status, url, retry_after)
            return status, text
        return common.attempt(once, state, min_seconds=ctx.min_seconds, clock=clock,
                              sleep=sleep, rand=rand)

    def keep(job_id: str) -> None:
        handled.add(job_id)
        state["job_ids"].append(job_id)

    def search_page(url: str) -> list[dict]:
        _, text = checked(url)
        summary["pages"] += 1
        cards = parse_search(text, str(ctx.country), today)
        if not cards and re.search(r"<article\b[^>]*data-id=", text):
            raise common.TitleProblem("cards_without_data", f"result cards without their "
                                      f"link or id on {url}: the page layout may have changed")
        return cards

    missing = 0
    collected = 0
    try:
        for page in range(done_pages + 1, max_pages + 1):
            url = search_url(str(ctx.country), title, ctx.days, page)
            cards = common.retry_title(lambda url=url: search_page(url), summary)
            if not cards:
                break
            for card in cards:
                if collected >= ctx.max_results:
                    break
                collected += 1
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
                    status, text = checked(card["url"], UNREADABLE)
                    keep(job_id)
                    if status in UNREADABLE:
                        summary["unreadable"].append({"external_id": job_id, "url": card["url"],
                                                      "reason": f"HTTP {status}"})
                        continue
                    if REMOVED.search(text):   # answered with 200, not 404
                        summary["unreadable"].append({"external_id": job_id, "url": card["url"],
                                                      "reason": "no longer available"})
                        continue
                    posting = parse_posting(text)
                    if posting is None or not posting["description"]:
                        summary["unreadable"].append({"external_id": job_id, "url": card["url"],
                                                      "reason": "no JobPosting description"})
                        missing += 1
                        if missing >= common.POSTING_PROBLEMS_IN_A_ROW:
                            raise common.TitleProblem(
                                "no_description", f"{missing} postings in a row without a "
                                f"JobPosting description (last {card['url']}): the posting page "
                                "may have changed")
                        continue
                    missing = 0
                    draft = _draft(card, posting, ctx)
                    if draft["site_first_posted_at"]:
                        summary["republished"] += 1
                    drafts.append(draft)
            common.progress(state, key)["pages"] = page
            if len(cards) < PAGE_SIZE or collected >= ctx.max_results:
                break
    except common.TitleProblem as problem:
        common.title_problem(summary, problem)
    except _Stop as stop:
        summary["stopped"] = common.stopped(stop)
    return common.finish(paths, ctx, state, summary, drafts, seen, key, now=clock())
