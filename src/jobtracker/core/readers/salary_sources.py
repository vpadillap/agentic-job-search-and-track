"""Salary readers of Indeed and Computrabajo: page addresses and parsers.

Both are read through `salary_pages.read` (a Scrapling session, paced, with a cool-down
across calls). Each parser returns one evidence draft for the agent to complete and
check, or `data: false` with the reason. Figures come from the page's own data only.
"""
from __future__ import annotations

import re
from datetime import date

from ..paths import Paths, slugify
from . import salary_pages
from .indeed import site as indeed_site

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12, "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12, "janeiro": 1, "fevereiro": 2, "março": 3, "maio": 5, "junho": 6,
    "julho": 7, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}


def page_date(text: str, today: date) -> date | None:
    """"6 de noviembre de 2026", "November 6, 2026", "6 de novembro de 2026"."""
    for match in re.finditer(r"(\d{1,2}) de ([a-zç]+) de (\d{4})|([A-Z][a-z]+) (\d{1,2}), (\d{4})",
                             text):
        day, month, year = ((match.group(1), match.group(2), match.group(3)) if match.group(1)
                            else (match.group(5), match.group(4), match.group(6)))
        number = MONTHS.get(month.casefold())
        if number:
            try:
                found = date(int(year), number, int(day))
            except ValueError:
                continue
            if found <= today:
                return found
    return None


# ── Indeed ───────────────────────────────────────────────────────────────

def indeed_url(title: str, country: str) -> str:
    return f"https://{indeed_site(country)}/career/{slugify(title, max_length=80)}/salaries"


def parse_indeed(html: str, url: str, country: str, today: date) -> dict:
    """Indeed's salary page: the period and amounts come from its structured data, never
    from its text (the Spanish text says "por mes" for yearly figures)."""
    occupation = salary_pages.json_ld(html, "Occupation")
    distributions = (occupation or {}).get("estimatedSalary") or []
    distributions = distributions if isinstance(distributions, list) else [distributions]
    first = next((d for d in distributions if isinstance(d, dict)), None)
    if first is None:
        return {"data": False, "url": url, "reason": "the page has no salary distribution "
                "(Indeed may have no page for this title in this country)"}
    period = salary_pages.PERIODS.get(str(first.get("duration") or "").upper())
    low, high, median = (first.get("percentile10"), first.get("percentile90"),
                         first.get("median"))
    if period is None or not all(isinstance(v, int | float) for v in (low, high, median)):
        return {"data": False, "url": url,
                "reason": f"unusable distribution (duration {first.get('duration')!r})"}
    text = salary_pages.plain_text(html)
    sample = re.search(r"(\d[\d.,]*)\s+(?:sueldos|salarios|salaries|salários)", text, re.I)
    updated = re.search(r"(?:Actualizado el|Updated|Atualizado em)\s+([^.|]{6,40})", text)
    observed = page_date(updated.group(1), today) if updated else None
    return {
        "data": True,
        "evidence": {
            "source": "Indeed", "url": url, "scope": "market",
            "amount_min": round(low), "amount_max": round(high),
            "currency": str(first.get("currency") or ""), "period": period,
            "sample_size": salary_pages.number(sample.group(1)) if sample else None,
            "observed_on": (observed or today).isoformat(), "country": country,
            "summary": (f"Indeed salaries for '{(occupation or {}).get('name')}' (all levels, "
                        f"from postings): median {round(median)}, 10th-90th percentile "
                        f"{round(low)}-{round(high)} {first.get('currency')} per {period}"),
        },
        "updated_on": observed.isoformat() if observed else None,
        # The agent adds: basis, level, posting_id or research, and checks that the
        # figures are plausible (a small or old sample is weak evidence).
    }


def indeed(paths: Paths, titles: str | list[str], *, search_url_given: str | None = None,
           **options) -> dict:
    return salary_pages.read(paths, "indeed", titles, indeed_url, parse_indeed, **options)


# ── Computrabajo ─────────────────────────────────────────────────────────

# Countries studied on 2026-11-19, with the currency of their figures.
COMPUTRABAJO = {"PE": "PEN", "MX": "MXN", "CO": "COP", "CL": "CLP", "AR": "ARS", "EC": "USD"}


def computrabajo_url(title: str, country: str) -> str | None:
    if country not in COMPUTRABAJO:
        return None
    return (f"https://{country.lower()}.computrabajo.com/salarios/"
            f"{slugify(title, max_length=80)}")


AMOUNT = r"((?:S/\.?|\$|US\$|USD)\s?[\d.,]+)"


def parse_computrabajo(html: str, url: str, country: str, today: date) -> dict:
    """Computrabajo's salary page: the monthly median for the title in the country, how
    many salaries it rests on, its low and high, and the median at each company listed."""
    text = salary_pages.plain_text(html)
    if re.search(r"No hay suficientes datos para mostrar salarios", text) and not re.search(
            r"es de " + AMOUNT + r" al mes", text):
        return {"data": False, "url": url, "reason": "Computrabajo has not enough salaries "
                "for this title in this country"}
    main = re.search(r"es de " + AMOUNT + r" al mes", text)
    block = re.search(r"Media salarial " + AMOUNT + r" /mes ([\d.,]+) salarios.*?Media salarial "
                      + AMOUNT + " " + AMOUNT, text)
    if not main or not block:
        return {"data": False, "url": url, "reason": "the page shows no salary figure"}
    median = salary_pages.number(main.group(1))
    sample = salary_pages.number(block.group(2))
    low, high = salary_pages.number(block.group(3)), salary_pages.number(block.group(4))
    updated = re.search(r"actualizaci[oó]n\s+\w+,\s+(\d{1,2} de [a-z]+ de \d{4})", text, re.I)
    observed = page_date(updated.group(1), today) if updated else None
    companies = []
    popular = text.split("Empresas populares", 1)
    if len(popular) == 2:
        for item in re.finditer(r"Media salarial (.+?) Empleos Evaluaciones Salarios " + AMOUNT
                                + r" /mes ([\d.,]+) salarios", popular[1]):
            name = re.sub(r"^(?:(?:" + AMOUNT + r"|Media salarial)\s*)+", "", item.group(1)).strip()
            companies.append({"company": name,
                              "median": salary_pages.number(item.group(2)),
                              "sample_size": salary_pages.number(item.group(3))})
    if not all(isinstance(v, int) and v > 0 for v in (median, low, high)):
        return {"data": False, "url": url, "reason": "unreadable salary figures"}
    currency = COMPUTRABAJO[country]
    return {
        "data": True,
        "evidence": {
            "source": "Computrabajo", "url": url, "scope": "market",
            "amount_min": median, "amount_max": median, "currency": currency,
            "period": "month", "sample_size": sample,
            "observed_on": (observed or today).isoformat(), "country": country,
            "summary": (f"Computrabajo: median {median} {currency} a month from {sample} "
                        f"salaries (all levels); lowest {low}, highest {high}"),
        },
        "low": low, "high": high,
        # Salaries for this title at companies the page lists: a company reference
        # (scope company) when one of them is the posting's company.
        "companies": companies,
        "updated_on": observed.isoformat() if observed else None,
    }


def computrabajo(paths: Paths, titles: str | list[str], *, search_url_given: str | None = None,
                 **options) -> dict:
    return salary_pages.read(paths, "computrabajo", titles, computrabajo_url,
                             parse_computrabajo, **options)
