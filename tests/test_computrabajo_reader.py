"""provider-computrabajo: the reader against a fake HTTP getter and fictional pages.
No test reaches Computrabajo."""
from __future__ import annotations

import json
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

import pytest

from jobtracker.core.readers import computrabajo

PERSONA = json.loads((Path(__file__).parent / "fixtures" / "persona.json").read_text(
    encoding="utf-8"))
TITLE = "Analista de datos"
TODAY = date.today()


def card(job_id: str, title="Analista de Datos", company="Cóndor Datos S.A.C.",
         when="Hace 2 horas", mode="Presencial y remoto", salary=None) -> str:
    salary_html = (f'<span class="dIB mr10"><span class="icon i_salary"></span>{salary}</span>'
                   if salary else "")
    mode_html = (f'<span class="dIB mr10"><span class="icon i_home_office"></span>{mode}</span>'
                 if mode else "")
    return (f"<article class=\"box_offer\" data-id='{job_id}' id=\"{job_id}\">"
            f'<h2><a class="js-o-link fc_base" href="/ofertas-de-trabajo/oferta-de-trabajo-de-'
            f'analista-{job_id}#lc=ListOffers-Score4-0"> {title} </a></h2>'
            f'<p class="dFlex vm_fx fs16 fc_base mt5"><a class="fc_base t_ellipsis" href="#" '
            f"offer-grid-article-company-url> {company} </a></p>"
            f'<p class="fs16 fc_base mt5"><span class="mr10"> Miraflores, Lima </span></p>'
            f'<div class="fs13 mt15">{salary_html}{mode_html}</div>'
            f'<p class="fs13 fc_aux mt15"> {when} </p></article>')


def posting(title="Analista de Datos", posted=None, salary=0, employment="FULL_TIME") -> str:
    data = {"@context": "https://schema.org/", "@graph": [{"@type": "WebPage"}, {
        "@type": "JobPosting", "title": title, "industry": "Banca / Financiera",
        "datePosted": (posted or TODAY).isoformat(), "employmentType": employment,
        "description": "<p>Analizar datos de ventas.</p><ul><li>SQL</li><li>Python</li></ul>",
        "hiringOrganization": {"@type": "Organization", "name": "Cóndor Datos S.A.C."},
        "baseSalary": {"@type": "MonetaryAmount", "currency": "PEN",
                       "value": {"@type": "QuantitativeValue", "value": salary,
                                 "unitText": "MONTH"}}}]}
    return f'<script type="application/ld+json">{json.dumps(data)}</script><h1>{title}</h1>'


class FakeGet:
    """Serves search pages in order and posting pages by id; records every address."""

    def __init__(self):
        self.pages: list[list[str]] = []
        self.postings: dict[str, str] = {}
        self.urls: list[str] = []
        self.now = 1000.0

    def __call__(self, url: str):
        self.urls.append(url)
        if "/trabajo-de-" in url:
            cards = self.pages.pop(0) if self.pages else []
            return 200, ("<html>" + "".join(cards) + "</html>").encode(), url, None
        job_id = url.rsplit("-", 1)[-1]
        if job_id not in self.postings:
            return 404, b"", url, None
        return 200, self.postings[job_id].encode(), url, None

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def fake():
    return FakeGet()


@pytest.fixture
def run(workspace, cli):
    needs = dict(PERSONA["job_needs"], titles=PERSONA["target_titles"], country="PE")
    path = workspace.home / "profile-input.json"
    path.write_text(json.dumps(needs), encoding="utf-8")
    assert cli("profile", "set", str(path))[0] == 0
    assert cli("providers", "enable", "computrabajo")[0] == 0
    code, out, _ = cli("run", "start", "--days", "7")
    assert code == 0 and "computrabajo" in out["to_search"], out
    return out


def read(workspace, run, fake, title=TITLE):
    return computrabajo.read(workspace, run["run_id"], title, fetch=fake, clock=fake.clock,
                             sleep=fake.sleep)


def drafts_of(summary):
    return json.loads(Path(summary["drafts_path"]).read_text(encoding="utf-8"))


def test_search_address_window_and_order():
    url = computrabajo.search_url("PE", "Analista de Datos", 7, 2)
    parts = urllib.parse.urlsplit(url)
    assert parts.netloc == "pe.computrabajo.com" and parts.path == "/trabajo-de-analista-de-datos"
    assert urllib.parse.parse_qs(parts.query) == {"by": ["publicationtime"], "pubdate": ["7"],
                                                  "p": ["2"]}
    assert computrabajo.pubdate(2) == 3 and computrabajo.pubdate(45) is None


def test_card_dates():
    today = date(2026, 11, 19)
    assert computrabajo.card_date("Hace 30 minutos", today) == "2026-11-19"
    assert computrabajo.card_date("Ayer", today) == "2026-11-18"
    assert computrabajo.card_date("Hace 3 días", today) == "2026-11-16"
    assert computrabajo.card_date("Publicado hace mucho", today) is None


def test_a_draft_with_its_hints(workspace, run, fake):
    fake.pages = [[card("A1B2C3D4E5F60718A1B2C3D4E5F60718", salary="S/ 3.500,00 (Mensual)")]]
    fake.postings["A1B2C3D4E5F60718A1B2C3D4E5F60718"] = posting(salary=3500)
    (draft,) = drafts_of(read(workspace, run, fake))
    assert (draft["title"], draft["company"], draft["location"], draft["country"]) == (
        "Analista de Datos", "Cóndor Datos S.A.C.", "Miraflores, Lima", "PE")
    assert draft["contract_type"] == "full-time" and draft["posted_at"] == TODAY.isoformat()
    assert "Analizar datos de ventas." in draft["description"] and "SQL" in draft["description"]
    assert draft["site_salary"] == {"currency": "PEN", "min": 3500, "max": 3500, "unit": "MONTH"}
    assert draft["site_work_mode"] == "Presencial y remoto"
    assert draft["site_category"] == "Banca / Financiera"
    assert draft["site_first_posted_at"] is None
    assert draft["published_salary"] is None and draft["work_mode"] is None  # the agent's reading


def test_a_republished_posting_counts_with_its_first_date(workspace, run, fake):
    fake.pages = [[card("AAAA000000000000AAAA000000000000", when="Hace 2 horas")]]
    first = TODAY - timedelta(days=40)
    fake.postings["AAAA000000000000AAAA000000000000"] = posting(posted=first)
    summary = read(workspace, run, fake)
    (draft,) = drafts_of(summary)
    assert draft["posted_at"] == TODAY.isoformat()              # inside the 7-day window
    assert draft["site_first_posted_at"] == first.isoformat()
    assert summary["republished"] == 1


def test_a_salary_to_be_agreed_is_left_out(workspace, run, fake):
    fake.pages = [[card("BBBB000000000000BBBB000000000000")]]
    fake.postings["BBBB000000000000BBBB000000000000"] = posting(salary=0)
    (draft,) = drafts_of(read(workspace, run, fake))
    assert draft["site_salary"] is None


def test_paging_window_and_removed_postings(workspace, run, fake):
    full = [card(f"C{i:031d}") for i in range(20)]
    fake.pages = [full, [card("D" + "0" * 31), card("E" + "0" * 31, when="Hace 12 días")]]
    for i in range(20):
        fake.postings[f"C{i:031d}"] = posting()
    summary = read(workspace, run, fake)
    assert summary["pages"] == 2 and summary["new"] == 20
    assert summary["outside_window"] == 1                      # 12 days, window 7
    assert [u["reason"] for u in summary["unreadable"]] == ["HTTP 404"]   # D was removed
    assert "p=2" in [u for u in fake.urls if "/trabajo-de-" in u][1]
    assert len(fake.urls) == summary["requests"]


def test_pacing(workspace, run, fake):
    fake.pages = [[card("F" + "0" * 31), card("F" + "1" * 31)]]
    fake.postings.update({"F" + "0" * 31: posting(), "F" + "1" * 31: posting()})
    start = fake.now
    read(workspace, run, fake)
    assert fake.now - start >= 2 * 5                           # 3 requests, 5 s apart


def test_another_country_is_refused(workspace, cli, fake, run):
    path = workspace.home / "p.json"
    path.write_text(json.dumps({"country": "US"}), encoding="utf-8")
    cli("profile", "set", str(path))
    with pytest.raises(Exception) as error:
        read(workspace, run, fake)
    assert "PE, MX, CO, CL, AR, EC" in str(error.value)


def confidential_page() -> str:
    return ('<h1 class="fwB">Analista de datos y BI</h1><div class="mb40 pb40 bb1" '
            'div-link="oferta"><h2 class="fwB fs18 mb20">Descripción de la oferta</h2>'
            '<div class="mbB"><span class="tag base mb10">$ 3.000.000,00 (Mensual)</span>'
            '<span class="tag base mb10">Tiempo Completo</span></div>'
            '<p class="mbB">Buscamos analista.<br>Manejo de SQL.</p>'
            '<p class="fwB fs18 mtB mb10">Requerimientos</p><ul class="disc mbB">'
            "<li class='mb10'>3 años de experiencia</li></ul>"
            '<p class="fc_aux fs13 mbB mtB">Palabras clave: data</p></div>')


def test_a_confidential_posting_is_read_from_its_page(workspace, run, fake):
    fake.pages = [[card("ABCD000000000000ABCD000000000000",
                        company="Importante empresa del sector")]]
    fake.postings["ABCD000000000000ABCD000000000000"] = confidential_page()
    (draft,) = drafts_of(read(workspace, run, fake))
    assert draft["company"] == "Importante empresa del sector"
    assert draft["title"] == "Analista de datos y BI"
    assert "Buscamos analista." in draft["description"] and "SQL" in draft["description"]
    assert "3 años de experiencia" in draft["description"] and "<" not in draft["description"]
    assert draft["site_salary"] == {"text": "$ 3.000.000,00 (Mensual)"}
    assert draft["site_tags"] == ["$ 3.000.000,00 (Mensual)", "Tiempo Completo"]


def test_an_escaped_description_becomes_text():
    page = posting().replace("<p>Analizar datos de ventas.</p>",
                             "&lt;p&gt;Analizar datos de ventas.&lt;br/&gt;Y más.&lt;/p&gt;")
    text = computrabajo.parse_posting(page)["description"]
    assert "Analizar datos de ventas." in text and "<" not in text and "&lt;" not in text


def test_a_posting_no_longer_available(workspace, run, fake):
    fake.pages = [[card("EEEE000000000000EEEE000000000000")]]
    fake.postings["EEEE000000000000EEEE000000000000"] = (
        "<title>Esta oferta ya no est&#xE1; disponible | Bolsa de Computrabajo</title>")
    summary = read(workspace, run, fake)
    assert summary["new"] == 0 and summary["title_problem"] is None
    assert [u["reason"] for u in summary["unreadable"]] == ["no longer available"]
