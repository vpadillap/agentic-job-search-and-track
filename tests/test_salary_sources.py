"""Salary readers of Indeed and Computrabajo (rework-salary-research), on fictional pages:
parsing, the period from structured data, title variants, pacing, and the cool-down."""
from __future__ import annotations

import json
from datetime import date

import pytest

from jobtracker.core import readers
from jobtracker.core.readers import salary_pages, salary_sources

TODAY = date(2026, 11, 19)


def indeed_page(duration="P1Y", currency="PEN", median=61000, p10=40000, p90=93000,
                sample="50", updated="6 de noviembre de 2026") -> str:
    data = {"@context": "https://schema.org", "@type": "Occupation", "name": "Data engineer/a",
            "estimatedSalary": [{"@type": "MonetaryAmountDistribution", "currency": currency,
                                 "duration": duration, "median": median,
                                 "percentile10": p10, "percentile90": p90}]}
    return (f'<html><script type="application/ld+json">{json.dumps(data)}</script>'
            f"<p>El sueldo promedio es de S/ {median} por mes. Esta cifra se basa en {sample} "
            f"sueldos tomados de publicaciones.</p><p>Actualizado el {updated}.</p></html>")


def ct_page(country_word="Perú", median="S/. 2.121", sample="451", low="S/. 500",
            high="S/. 4.000", companies=True) -> str:
    rows = ("<h2>Empresas populares</h2><p>Media salarial</p><p>Cóndor Datos S.A.C.</p>"
            "<p>Empleos</p><p>Evaluaciones</p><p>Salarios</p><p>S/. 2.500</p><p>/mes</p>"
            "<p>12 salarios</p><p>Media salarial</p><p>S/. 2.000</p><p>S/. 3.000</p>"
            "<p>Ficticia Retail</p><p>Empleos</p><p>Evaluaciones</p>"
            "<p>Salarios</p><p>S/. 1.900</p><p>/mes</p><p>7 salarios</p>") if companies else ""
    return (f"<html><p>El sueldo medio para el puesto de Analista de datos en {country_word} es de "
            f"{median} al mes</p><p>La información es una estimación a partir de 1.508.419 "
            f"fuentes</p><p>Media salarial</p><p>{median}</p><p>/mes</p><p>{sample} salarios</p>"
            f"<p>200 salarios</p><p>Media salarial</p><p>{low}</p><p>{high}</p>{rows}"
            "<p>Última actualización jueves, 12 de noviembre de 2026</p></html>")


# ── parsers ───────────────────────────────────────────────────────────────

def test_indeed_takes_the_period_from_structured_data_not_the_text():
    result = salary_sources.parse_indeed(indeed_page(), "https://pe.indeed.com/x", "PE", TODAY)
    evidence = result["evidence"]
    assert result["data"] and evidence["period"] == "year"           # the text says "por mes"
    assert (evidence["amount_min"], evidence["amount_max"]) == (40000, 93000)
    assert evidence["currency"] == "PEN" and evidence["sample_size"] == 50
    assert evidence["observed_on"] == "2026-11-06" and "median 61000" in evidence["summary"]


def test_indeed_monthly_and_english_date():
    page = indeed_page(duration="P1M", currency="GBP", updated="November 6, 2026",
                       sample="1,240")
    evidence = salary_sources.parse_indeed(page, "u", "GB", TODAY)["evidence"]
    assert evidence["period"] == "month" and evidence["observed_on"] == "2026-11-06"


def test_indeed_page_without_distribution():
    result = salary_sources.parse_indeed("<html>No salary</html>", "u", "PE", TODAY)
    assert result["data"] is False and "distribution" in result["reason"]


def test_computrabajo_median_sample_range_and_companies():
    result = salary_sources.parse_computrabajo(ct_page(), "https://pe.computrabajo.com/x",
                                               "PE", TODAY)
    evidence = result["evidence"]
    assert (evidence["amount_min"], evidence["amount_max"], evidence["currency"]) == (
        2121, 2121, "PEN")
    assert evidence["sample_size"] == 451 and evidence["observed_on"] == "2026-11-12"
    assert (result["low"], result["high"]) == (500, 4000)
    assert result["companies"] == [
        {"company": "Cóndor Datos S.A.C.", "median": 2500, "sample_size": 12},
        {"company": "Ficticia Retail", "median": 1900, "sample_size": 7}]


def test_computrabajo_colombian_amounts():
    page = ct_page("Colombia", "$ 2.418.280", "7.172", "$ 1.000.000", "$ 8.000.000",
                   companies=False)
    evidence = salary_sources.parse_computrabajo(page, "u", "CO", TODAY)["evidence"]
    assert (evidence["amount_min"], evidence["currency"], evidence["sample_size"]) == (
        2418280, "COP", 7172)


def test_computrabajo_without_enough_data():
    page = ("<p>El sueldo medio para el puesto de ingeniero-de-datos en Perú es de al mes</p>"
            "<p>No hay suficientes datos para mostrar salarios para este puesto</p>")
    result = salary_sources.parse_computrabajo(page, "u", "PE", TODAY)
    assert result["data"] is False and "not enough" in result["reason"]


def test_computrabajo_countries_and_urls():
    assert salary_sources.computrabajo_url("Analista de Datos", "PE") == (
        "https://pe.computrabajo.com/salarios/analista-de-datos")
    assert salary_sources.computrabajo_url("Analista de datos", "US") is None
    assert salary_sources.indeed_url("Data Engineer", "US") == (
        "https://www.indeed.com/career/data-engineer/salaries")
    assert salary_sources.indeed_url("Data Engineer", "MX").startswith("https://mx.indeed.com/")


def test_both_are_registered_salary_readers():
    assert {"indeed", "computrabajo", "glassdoor"} <= set(readers.SALARY_READERS)


# ── the shared reader: variants, pacing, cool-down ───────────────────────

class FakePages:
    def __init__(self, answers):
        self.answers = list(answers)
        self.opened = []

    def __call__(self, locale, provider):
        return self

    def page(self, url):
        self.opened.append(url)
        return self.answers.pop(0)

    def close(self):
        pass


@pytest.fixture
def peru(workspace, cli, tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"country": "PE"}), encoding="utf-8")
    cli("profile", "set", str(path))
    return workspace


def _read(paths, pages, titles, clock):
    return salary_pages.read(paths, "computrabajo", titles, salary_sources.computrabajo_url,
                             salary_sources.parse_computrabajo, fetcher=pages, today=TODAY,
                             clock=lambda: clock[0], sleep=lambda s: clock.__setitem__(
                                 0, clock[0] + s), rand=lambda: 0.5)


def test_variants_are_tried_in_order_until_one_has_data(peru):
    empty = (200, "Salarios", "<p>No hay suficientes datos para mostrar salarios</p>")
    pages = FakePages([empty, (200, "Salarios", ct_page())])
    clock = [1000.0]
    result = _read(peru, pages, ["ingeniero de datos", "analista de datos"], clock)
    assert result["data"] and [t["data"] for t in result["tried"]] == [False, True]
    assert pages.opened[1].endswith("/salarios/analista-de-datos")
    assert clock[0] >= 1000.0 + salary_pages.MIN_SECONDS          # paced between pages


def test_a_refusal_starts_a_cool_down_kept_across_calls(peru):
    pages = FakePages([(403, "Access denied", "")])
    clock = [1000.0]
    result = _read(peru, pages, ["analista de datos"], clock)
    assert result["throttled"] and result["blocked"] and result["minutes_left"] == 15
    later = FakePages([])
    result = _read(peru, later, ["analista de datos"], clock)
    assert result["throttled"] and later.opened == []             # nothing opened meanwhile
    settings = json.loads((peru.home / "provider-settings" / "computrabajo.json")
                          .read_text(encoding="utf-8"))
    assert settings["salary"]["throttles"] == 1


def test_a_country_without_pages(workspace, cli, tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"country": "US"}), encoding="utf-8")
    cli("profile", "set", str(path))
    result = _read(workspace, FakePages([]), ["data analyst"], [0.0])
    assert result["data"] is False and "no salary pages for US" in result["reason"]
