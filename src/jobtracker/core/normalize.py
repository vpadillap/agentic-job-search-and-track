"""Normalizing what job sites show: work modes, contracts, dates, and identity keys."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta

from .errors import JobTrackerError

_WORK_MODES = {
    "remote": "remote", "remoto": "remote", "remota": "remote", "teletrabajo": "remote",
    "work from home": "remote", "100% remoto": "remote", "home office": "remote",
    "hybrid": "hybrid", "hibrido": "hybrid", "hibrida": "hybrid", "mixto": "hybrid",
    "onsite": "onsite", "on-site": "onsite", "on site": "onsite", "in office": "onsite",
    "in-office": "onsite", "presencial": "onsite", "en oficina": "onsite",
}
_CONTRACTS = {
    "full-time": "full-time", "full time": "full-time", "fulltime": "full-time",
    "tiempo completo": "full-time", "jornada completa": "full-time", "permanent": "full-time",
    "planilla": "full-time", "indefinido": "full-time",
    "part-time": "part-time", "part time": "part-time", "medio tiempo": "part-time",
    "tiempo parcial": "part-time", "media jornada": "part-time",
    "contractor": "contractor", "contract": "contractor", "contrato": "contractor",
    "freelance": "contractor", "temporary": "contractor", "temporal": "contractor",
    "por proyecto": "contractor", "recibo por honorarios": "contractor",
}
_LEGAL_SUFFIXES = {
    "sa", "sac", "saa", "srl", "eirl", "sas", "inc", "llc", "ltd", "ltda", "corp", "co",
    "gmbh", "plc", "spa", "cia",
}
_UNITS = {
    "minute": 0, "minuto": 0, "min": 0, "hour": 0, "hora": 0, "h": 0, "hr": 0,
    "day": 1, "dia": 1, "d": 1, "week": 7, "semana": 7, "sem": 7, "w": 7, "wk": 7,
    "month": 30, "mes": 30, "mo": 30,
}


def ascii_fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _plain(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9%+]+", " ", ascii_fold(text).lower()).split())


def clean_text(text: str) -> str:
    """Collapse whitespace in short fields (titles, companies). Never used on descriptions."""
    return " ".join(text.split())


def work_mode(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    plain = _plain(str(value))
    if plain in _WORK_MODES:
        return _WORK_MODES[plain]
    # "Hybrid (2 days remote)" is hybrid: check the most specific mode first.
    for wanted in ("hybrid", "remote", "onsite"):
        for word, mode in _WORK_MODES.items():
            if mode == wanted and re.search(rf"\b{re.escape(word)}\b", plain):
                return mode
    raise JobTrackerError(
        "invalid_posting", f"work_mode '{value}' is not remote, hybrid, or onsite",
        field="work_mode",
    )


def contract_type(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    plain = _plain(str(value))
    if plain in _CONTRACTS:
        return _CONTRACTS[plain]
    for word, kind in _CONTRACTS.items():
        if word in plain:
            return kind
    raise JobTrackerError(
        "invalid_posting",
        f"contract_type '{value}' is not full-time, part-time, or contractor",
        field="contract_type",
    )


def parse_date(value: str) -> date:
    """An absolute date: YYYY-MM-DD or an ISO 8601 timestamp."""
    text = str(value).strip()
    try:
        if len(text) == 10:
            return date.fromisoformat(text)
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError as error:
        raise JobTrackerError(
            "invalid_date", f"'{value}' is not a date like 2026-11-15"
        ) from error


def relative_date(text: str, reference: date) -> date:
    """Turn what a site shows ('2 days ago', 'hace 3 días', 'yesterday') into a date."""
    plain = _plain(text)
    if plain in ("today", "hoy", "just now", "just posted", "ahora", "recien publicado",
                 "new", "nuevo"):
        return reference
    if plain in ("yesterday", "ayer"):
        return reference - timedelta(days=1)
    if plain in ("anteayer", "antier"):
        return reference - timedelta(days=2)
    match = re.search(r"(\d+)\s*\+?\s*([a-z]+)", plain)
    if not match:
        if re.search(r"\b(an?|un|una)\s+(day|dia)\b", plain):
            return reference - timedelta(days=1)
        if re.search(r"\b(an?|un|una)\s+(week|semana)\b", plain):
            return reference - timedelta(days=7)
        if re.search(r"\b(an?|un|una)\s+(hour|hora|minute|minuto)\b", plain):
            return reference
        raise JobTrackerError(
            "invalid_date", f"Cannot read '{text}' as a date. Send posted_at as YYYY-MM-DD."
        )
    amount = int(match.group(1))
    unit = match.group(2)
    for name, days in _UNITS.items():
        if unit == name or unit == name + "s" or unit == name + "es" or (
            len(name) > 2 and unit.startswith(name)
        ):
            return reference - timedelta(days=amount * days)
    raise JobTrackerError(
        "invalid_date", f"Cannot read '{text}' as a date. Send posted_at as YYYY-MM-DD."
    )


def company_key(company: str) -> str:
    words = _plain(company).replace("%", " ").split()
    while words and words[-1] in _LEGAL_SUFFIXES:
        words.pop()
    # "s a c" from "S.A.C." collapses to single letters; drop trailing initials too.
    while len(words) > 1 and len(words[-1]) == 1:
        words.pop()
    return " ".join(words)


def title_key(title: str) -> str:
    return " ".join(_plain(title).replace("%", " ").split())


def location_key(location: str | None) -> str:
    return " ".join(_plain(location or "").replace("%", " ").split())


def match_key(company: str, title: str) -> str:
    """Company and title, for the 'possible duplicate' hint only. Postings are never merged."""
    return f"{company_key(company)}|{title_key(title)}"


def url_key(url: str) -> str:
    """The identity of a posting's URL: scheme and host lowercased, no fragment or trailing /."""
    match = re.match(r"^(https?)://([^/?#]+)([^#]*)", url.strip(), re.I)
    if not match:
        return url.strip()
    scheme, host, rest = match.group(1).lower(), match.group(2).lower(), match.group(3)
    path, _, query = rest.partition("?")
    path = path.rstrip("/")
    return f"{scheme}://{host}{path}" + (f"?{query}" if query else "")


def safe_url(value: object, field: str = "url") -> str:
    if not isinstance(value, str) or not re.match(r"^https?://[^\s]+$", value.strip()):
        raise JobTrackerError(
            "invalid_url", f"{field} must be an http(s) link", field=field,
        )
    return value.strip()
