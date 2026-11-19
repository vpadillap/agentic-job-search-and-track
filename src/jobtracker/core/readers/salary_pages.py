"""Salary pages read through a headless Scrapling session: the shared part of the salary
readers of Indeed and Computrabajo (Glassdoor keeps its own, older one).

One call reads up to three title variants, in order, until one page has data, in the
profile's country. Pages are paced across calls; a refusal that remains after waiting
(common.attempt) starts a cool-down, kept in `provider-settings/<provider>.json`,
during which no salary page of that provider is opened. A parser turns a page into one
evidence draft, or into `data: false` with the reason.
"""
from __future__ import annotations

import html as htmllib
import json
import random
import re
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Protocol

from .. import db
from .. import profile as profile_service
from ..errors import JobTrackerError
from ..paths import Paths
from . import common

MIN_SECONDS = 20
COOLDOWNS = (15 * 60, 30 * 60, 60 * 60)   # after the 1st, 2nd, 3rd+ refusal in a row
MAX_TITLES = 3
PERIODS = {"P1M": "month", "P1Y": "year", "MONTH": "month", "YEAR": "year"}
BLOCK_MARKERS = ("Attention Required", "Access denied", "Blocked")
LOCALES = {"PE": "es-PE", "MX": "es-MX", "CO": "es-CO", "CL": "es-CL", "AR": "es-AR",
           "EC": "es-EC", "ES": "es-ES", "US": "en-US", "GB": "en-GB", "CA": "en-CA",
           "BR": "pt-BR", "PT": "pt-PT"}

Parser = Callable[[str, str, str, date], dict]


class Fetcher(Protocol):
    def page(self, url: str) -> tuple[int | None, str, str]:
        """Load one page: (HTTP status, page title, page HTML)."""

    def close(self) -> None: ...


class ScraplingPages:
    """A headless Scrapling stealth session with no cookies and no account."""

    def __init__(self, locale: str, provider: str) -> None:
        try:
            from scrapling.fetchers import StealthySession
        except ImportError as error:
            raise JobTrackerError("missing_dependency", f"{provider} salary pages need "
                                  f"Scrapling: run jt providers install {provider}") from error
        import logging

        logging.getLogger("scrapling").setLevel(logging.WARNING)
        try:
            self._session = StealthySession(headless=True, solve_cloudflare=True, locale=locale,
                                            retries=1, timeout=90000, wait=2000)
            self._session.__enter__()
        except Exception as error:  # the browser itself is not installed
            raise JobTrackerError("missing_dependency", f"Scrapling's browser is not ready "
                                  f"({error}); run: jt providers install {provider}") from error

    def page(self, url: str) -> tuple[int | None, str, str]:
        response = self._session.fetch(url, network_idle=True)
        html = str(getattr(response, "html_content", None) or response.body or "")
        title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        return (getattr(response, "status", None),
                htmllib.unescape(title.group(1)).strip() if title else "", html)

    def close(self) -> None:
        self._session.__exit__(None, None, None)


# ── helpers for parsers ───────────────────────────────────────────────────

def plain_text(html: str) -> str:
    html = re.sub(r"<style.*?</style>|<script.*?</script>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", html))).strip()


def json_ld(html: str, kind: str) -> dict | None:
    """The first structured-data item of type `kind`."""
    for block in re.findall(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", html,
                            re.S | re.I):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            item = stack.pop(0)
            if isinstance(item, dict):
                if item.get("@type") == kind:
                    return item
                stack.extend(v for v in item.values() if isinstance(v, dict | list))
            elif isinstance(item, list):
                stack.extend(item)
    return None


def number(text: str) -> int | None:
    """A whole amount written with any thousands separator: "2.121", "2,418,280"."""
    digits = re.sub(r"[^\d.,]", "", text or "")
    if not digits:
        return None
    # A final group of exactly two digits after a separator is cents.
    cents = re.search(r"[.,]\d{2}$", digits)
    if cents and not re.search(r"[.,]\d{3}$", digits):
        digits = digits[: cents.start()]
    whole = re.sub(r"[.,]", "", digits)
    return int(whole) if whole else None


# ── the call ──────────────────────────────────────────────────────────────

def titles_given(titles: str | list[str] | None) -> list[str]:
    given = [titles] if isinstance(titles, str) else list(titles or [])
    found: list[str] = []
    for title in given:
        title = " ".join((title or "").split())
        if title and title.casefold() not in {t.casefold() for t in found}:
            found.append(title)
    if not found:
        raise JobTrackerError("invalid_title", "give the title with --title")
    if len(found) > MAX_TITLES:
        raise JobTrackerError("invalid_title", f"give at most {MAX_TITLES} titles "
                              "(--title repeated)")
    return found


def _settings_path(paths: Paths, provider: str):
    return paths.home / "provider-settings" / f"{provider}.json"


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat(timespec="seconds")


def _check(status: int | None, title: str, url: str) -> None:
    if status == 403 or any(marker in title for marker in BLOCK_MARKERS):
        raise common.Stop("blocked", f"{status} '{title}' on {url}")
    if common.soft_status(status) or common.is_challenge(title):
        raise common.Throttle(f"{status} '{title}' on {url}", None)


def read(paths: Paths, provider: str, titles: str | list[str],
         url_for: Callable[[str, str], str | None], parse: Parser, *,
         fetcher: Callable[[str, str], Fetcher] = ScraplingPages, today: date | None = None,
         clock: Callable[[], float] = time.time, sleep: Callable[[float], None] = time.sleep,
         rand: Callable[[], float] = random.random) -> dict:
    """Read a provider's salary page for up to three titles in the profile's country."""
    titles = titles_given(titles)
    with db.session(paths) as conn:
        active = profile_service.get_active(conn) or {}
    country = str(active.get("country") or "").upper()
    if not country:
        raise JobTrackerError("no_country", "the profile has no country; set it in /setup")
    if url_for(titles[0], country) is None:
        return {"data": False, "url": None, "tried": [],
                "reason": f"{provider} has no salary pages for {country}"}
    path = _settings_path(paths, provider)
    settings = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    state = {"last_request_at": 0.0, "cooldown_until": None, "throttles": 0,
             "last_detail": None, **(settings.get("salary") or {})}

    def save() -> None:
        settings["salary"] = state
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, ensure_ascii=False, indent=1), encoding="utf-8")

    def throttled(url: str | None, blocked: bool = False) -> dict:
        left = max(0.0, state["cooldown_until"] - clock())
        return {"data": False, "throttled": True, "blocked": blocked, "url": url,
                "reason": state.get("last_detail") or f"{provider} refused a salary page",
                "resume_after": _iso(state["cooldown_until"]),
                "minutes_left": int(-(-round(left) // 60))}

    if state["cooldown_until"] and clock() < state["cooldown_until"]:
        return {**throttled(url_for(titles[0], country)), "tried": []}
    session = fetcher(LOCALES.get(country, "en-US"), provider)
    retries: dict = {"retries": 0}
    tried: list[dict] = []
    result: dict = {}

    def once(url: str) -> str:
        wait = state["last_request_at"] + MIN_SECONDS - clock()
        if state["last_request_at"] and wait > 0:
            sleep(wait)
        try:
            status, page_title, html = session.page(url)
        finally:
            state["last_request_at"] = clock()
            save()
        _check(status, page_title, url)
        return html

    try:
        for title in titles:
            url = url_for(title, country)
            assert url is not None
            try:
                html = common.attempt(lambda url=url: once(url), retries,
                                      min_seconds=MIN_SECONDS, clock=clock, sleep=sleep,
                                      rand=rand)
            except common.Stop as stop:
                state["throttles"] = int(state.get("throttles") or 0) + 1
                step = COOLDOWNS[min(state["throttles"], len(COOLDOWNS)) - 1]
                state["cooldown_until"] = clock() + max(step, stop.retry_after or 0)
                state["last_detail"] = stop.detail
                save()
                result = throttled(url, blocked=stop.reason != "throttled")
                tried.append({"title": title, "url": url, "data": False,
                              "reason": stop.detail})
                break
            state.update(throttles=0, cooldown_until=None, last_detail=None)
            save()
            result = parse(html, url, country, today or date.today())
            tried.append({"title": title, "url": url, "data": result["data"],
                          "reason": result.get("reason")})
            if result["data"]:
                break
    finally:
        session.close()
    result["tried"] = tried
    return result
