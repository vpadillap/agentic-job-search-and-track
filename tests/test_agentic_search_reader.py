"""provider-agentic-search: the reader against a fake web of fictional pages. No test
reaches the network or a real company."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import pytest

from jobtracker.core import readers
from jobtracker.core.errors import JobTrackerError
from jobtracker.core.readers import agentic_search as reader

PERSONA = json.loads((Path(__file__).parent / "fixtures" / "persona.json").read_text(
    encoding="utf-8"))
TITLE = "Senior Data Engineer"
TODAY = date.today()
DESCRIPTION = ("<p>Andes Datos Ficticios busca un <b>Data Engineer</b>.</p>"
               "<ul><li>Python y SQL</li><li>Modalidad híbrida en Lima</li></ul>"
               "<p>Ofrecemos línea de carrera.</p>")
FILLER = "<p>" + "Texto de la página de empleos de una empresa ficticia. " * 20 + "</p>"


def posting_page(title="Data Engineer", company="Andes Datos Ficticios", country="PE",
                 days_ago=1, valid_through=None, extra_html="", url=None) -> str:
    data = {"@context": "https://schema.org", "@type": "JobPosting", "title": title,
            "hiringOrganization": {"@type": "Organization", "name": company},
            "jobLocation": {"@type": "Place", "address": {
                "addressLocality": "Lima", "addressCountry": country}},
            "datePosted": (TODAY - timedelta(days=days_ago)).isoformat(),
            "employmentType": "FULL_TIME", "description": DESCRIPTION}
    if valid_through:
        data["validThrough"] = valid_through
    if url:
        data["url"] = url
    return (f'<html><head><script type="application/ld+json">{json.dumps(data)}</script>'
            f"</head><body><nav>Inicio</nav><h1>{title}</h1>{FILLER}{extra_html}</body></html>")


PLAIN_PAGE = ("<html><body><nav>Inicio | Nosotros | Empleos</nav>"
              "<h1>Ingeniero de Datos Senior</h1><p>Empresa: Andes Datos Ficticios</p>"
              "<p>Buscamos un ingeniero de datos con experiencia en Python.</p>"
              "<ul><li>Python</li><li>Airflow</li></ul>" + FILLER +
              "<footer>Política de privacidad</footer></body></html>")


class FakeWeb:
    """Pages by URL (robots.txt answers 404 unless set); records requests and time."""

    def __init__(self) -> None:
        self.pages: dict[str, tuple[int, str]] = {}
        self.rendered: dict[str, str] = {}
        self.urls: list[str] = []
        self.renders: list[str] = []
        self.times: dict[str, list[float]] = {}
        self.now = 1_000.0

    def __call__(self, url: str) -> tuple[int, str, str]:
        self.urls.append(url)
        self.times.setdefault(reader.host_of(url), []).append(self.now)
        status, body = self.pages.get(url, (404, "not found"))
        return status, body, url

    def render(self, url: str) -> tuple[int, str]:
        self.renders.append(url)
        self.times.setdefault(reader.host_of(url), []).append(self.now)
        return 200, self.rendered[url]

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def page_requests(self) -> list[str]:
        return [u for u in self.urls if not u.endswith("/robots.txt")]


@pytest.fixture
def web() -> FakeWeb:
    return FakeWeb()


@pytest.fixture
def run(workspace, cli):
    needs = dict(PERSONA["job_needs"])
    needs["titles"] = PERSONA["target_titles"]
    path = workspace.home / "profile-input.json"
    path.write_text(json.dumps(needs), encoding="utf-8")
    assert cli("profile", "set", str(path))[0] == 0
    path.unlink()
    assert cli("providers", "enable", "agentic-search")[0] == 0
    code, run, _ = cli("run", "start", "--days", "7")
    assert code == 0 and "agentic-search" in run["to_search"], run
    return run


def read(workspace, run, web, tmp_path, *items, title=TITLE, renderer=None, **kwargs):
    path = tmp_path / f"found-{len(web.urls)}.json"
    path.write_text(json.dumps(list(items)), encoding="utf-8")
    return reader.read(workspace, run["run_id"], title, found=str(path), get=web,
                       renderer=renderer, clock=web.clock, sleep=web.sleep, **kwargs)


def drafts_of(summary) -> list[dict]:
    if not summary["drafts_path"]:
        return []
    return json.loads(Path(summary["drafts_path"]).read_text(encoding="utf-8"))


# ── pure parts ────────────────────────────────────────────────────────────

def test_canonical_links_lose_tracking_and_fragment():
    assert reader.canonical("https://Careers.Andes.example/jobs/7?utm_source=x&gh_src=1"
                            "&lever-source=y&id=7#apply") == \
        "https://careers.andes.example/jobs/7?id=7"


@pytest.mark.parametrize("url,why", [
    ("https://pe.indeed.com/viewjob?jk=1", "provider_domain"),
    ("https://www.bumeran.com.pe/empleos/1.html", "provider_domain"),
    ("https://job-boards.greenhouse.io/andes/jobs/1", "provider_domain"),
    ("ftp://andes.example/jobs", "not_a_web_page"),
    ("https://andes.example/login?next=/jobs", "sign_in_or_apply_page"),
    ("https://andes.example/jobs/7/apply", "sign_in_or_apply_page"),
    ("https://careers.andes.example/jobs/7", None),
])
def test_links_refused_before_any_request(url, why):
    assert reader.refusal(url) == why


def test_found_items_are_checked():
    with pytest.raises(JobTrackerError):
        reader.parse_found({"url": "https://a.example"})
    with pytest.raises(JobTrackerError):
        reader.parse_found([{"url": "https://a.example", "lines": [9, 3]}])
    assert reader.parse_found(["https://A.example/x?utm_medium=y"]) == [
        {"url": "https://a.example/x"}]
    lever = "https://jobs.lever.co/andes/11111111-1111-1111-1111-111111111111"
    assert reader.parse_found([lever + "/apply"]) == [{"url": lever}]


def test_numbered_text_cuts_back_to_the_same_lines():
    text = reader.numbered("https://a.example/1", "uno\ndos\n\ntres\ncuatro")
    assert text.splitlines()[0] == "https://a.example/1"
    assert reader.cut_lines(text, 2, 4) == "dos\n\ntres"


def test_only_the_options_of_this_reader_are_taken(workspace):
    with pytest.raises(JobTrackerError) as error:
        readers.read("agentic-search", workspace, 1, TITLE, place_words="Peru")
    assert error.value.code == "invalid_option"


# ── reading pages ─────────────────────────────────────────────────────────

def test_a_posting_with_structured_data_is_drafted_verbatim(workspace, run, web, tmp_path):
    url = "https://careers.andes.example/jobs/7"
    web.pages[url] = (200, posting_page())
    summary = read(workspace, run, web, tmp_path, url + "?utm_source=search")
    (draft,) = drafts_of(summary)
    assert draft["external_id"] == draft["url"] == url
    assert draft["source_site"] == "careers.andes.example"
    assert (draft["title"], draft["company"], draft["country"]) == (
        "Data Engineer", "Andes Datos Ficticios", "PE")
    assert draft["posted_at"] == (TODAY - timedelta(days=1)).isoformat()
    assert draft["contract_type"] == "full-time"
    assert draft["description"].splitlines() == [
        "Andes Datos Ficticios busca un Data Engineer.", "", "- Python y SQL", "",
        "- Modalidad híbrida en Lima", "", "Ofrecemos línea de carrera."]
    folder = Path(summary["drafts_path"]).parent
    assert (folder / "agentic-search-1.txt").read_text(encoding="utf-8").startswith(url)
    assert (folder / "agentic-search-1.html").is_file()


def test_provider_sites_get_no_request(workspace, run, web, tmp_path):
    summary = read(workspace, run, web, tmp_path, "https://pe.indeed.com/viewjob?jk=1",
                   "https://www.linkedin.com/jobs/view/1")
    assert web.urls == []
    assert {r["reason"] for r in summary["refused"]} == {"provider_domain"}


def test_robots_txt_is_obeyed(workspace, run, web, tmp_path):
    web.pages["https://andes.example/robots.txt"] = (
        200, "User-agent: *\nDisallow: /empleos/\n")
    summary = read(workspace, run, web, tmp_path, "https://andes.example/empleos/7")
    assert web.page_requests() == []
    assert summary["refused"] == [{"url": "https://andes.example/empleos/7",
                                   "reason": "robots"}]


def test_pages_on_one_host_are_paced_across_calls(workspace, run, web, tmp_path):
    for n in (1, 2):
        web.pages[f"https://careers.andes.example/jobs/{n}"] = (200, posting_page(
            title=f"Data Engineer {n}"))
    read(workspace, run, web, tmp_path, "https://careers.andes.example/jobs/1")
    read(workspace, run, web, tmp_path, "https://careers.andes.example/jobs/2")
    times = web.times["careers.andes.example"]
    assert len(times) == 3                                    # robots.txt once, two pages
    assert all(b - a >= 5 for a, b in zip(times, times[1:], strict=False))


def test_a_refusal_ends_the_host_without_a_browser(workspace, run, web, tmp_path):
    web.pages["https://pe.bolsa.example/oferta/1"] = (403, "Forbidden")
    web.pages["https://pe.bolsa.example/oferta/2"] = (200, posting_page())
    summary = read(workspace, run, web, tmp_path, "https://pe.bolsa.example/oferta/1",
                   "https://pe.bolsa.example/oferta/2", renderer=web.render)
    assert web.page_requests() == ["https://pe.bolsa.example/oferta/1"]
    assert web.renders == []
    assert summary["refused_hosts"] == {"pe.bolsa.example": "site_refused"}
    assert summary["suggest_provider"] == ["pe.bolsa.example"]
    again = read(workspace, run, web, tmp_path, "https://pe.bolsa.example/oferta/3")
    assert web.page_requests() == ["https://pe.bolsa.example/oferta/1"]
    assert again["refused"][0]["reason"] == "site_refused"


def test_a_challenge_page_is_a_refusal(workspace, run, web, tmp_path):
    web.pages["https://andes.example/jobs/1"] = (
        200, "<html><title>Attention Required!</title><div id='cf-challenge'></div></html>")
    summary = read(workspace, run, web, tmp_path, "https://andes.example/jobs/1")
    assert summary["refused_hosts"] == {"andes.example": "site_refused"}


def test_a_javascript_page_is_rendered_once(workspace, run, web, tmp_path):
    url = "https://careers.andes.example/jobs/9"
    web.pages[url] = (200, '<html><body><div id="root"></div></body></html>')
    web.rendered[url] = posting_page()
    summary = read(workspace, run, web, tmp_path, url, renderer=web.render)
    assert web.renders == [url] and summary["rendered"] == 1
    assert len(drafts_of(summary)) == 1


def test_without_a_browser_the_page_is_reported(workspace, run, web, tmp_path):
    url = "https://careers.andes.example/jobs/9"
    web.pages[url] = (200, '<html><body><div id="root"></div></body></html>')
    summary = read(workspace, run, web, tmp_path, url)
    assert summary["needs_browser"] == [url]
    assert "jt providers install agentic-search" in summary["browser"]


def test_closed_postings_are_left_out(workspace, run, web, tmp_path):
    web.pages["https://andes.example/jobs/1"] = (200, posting_page(
        valid_through=(TODAY - timedelta(days=2)).isoformat()))
    web.pages["https://andes.example/jobs/2"] = (200, posting_page(
        title="Data Engineer II", extra_html="<p>Esta oferta ya no está disponible.</p>"))
    summary = read(workspace, run, web, tmp_path, "https://andes.example/jobs/1",
                   "https://andes.example/jobs/2")
    assert summary["closed"] == ["https://andes.example/jobs/1", "https://andes.example/jobs/2"]
    assert drafts_of(summary) == []


# ── pages without structured data ─────────────────────────────────────────

def test_a_plain_page_is_cut_by_lines_without_a_new_request(workspace, run, web, tmp_path):
    url = "https://andes.example/empleos/ingeniero-datos"
    web.pages[url] = (200, PLAIN_PAGE)
    summary = read(workspace, run, web, tmp_path, url)
    (plain,) = summary["no_structured_data"]
    text = Path(plain["text_file"]).read_text(encoding="utf-8").splitlines()
    first = next(n for n, line in enumerate(text) if "Buscamos" in line)
    last = next(n for n, line in enumerate(text) if "Airflow" in line)
    requests = len(web.urls)
    summary = read(workspace, run, web, tmp_path, {
        "url": url, "lines": [first, last], "synonym": True,
        "title": "Ingeniero de Datos Senior",
        "company": "Andes Datos Ficticios", "location": "Lima, Peru"}, location="Peru; Lima")
    assert len(web.urls) == requests
    (draft,) = drafts_of(summary)
    assert draft["description"] == ("Buscamos un ingeniero de datos con experiencia en "
                                    "Python.\n\n- Python\n\n- Airflow")
    assert draft["country"] == "PE" and draft["posted_at"] is None


def test_lines_need_what_the_page_shows(workspace, run, web, tmp_path):
    url = "https://andes.example/empleos/ingeniero-datos"
    web.pages[url] = (200, PLAIN_PAGE)
    read(workspace, run, web, tmp_path, url)
    with pytest.raises(JobTrackerError, match="not on the captured page"):
        read(workspace, run, web, tmp_path, {"url": url, "lines": [2, 3],
                                            "title": "Gerente General",
                                            "company": "Andes Datos Ficticios"})
    with pytest.raises(JobTrackerError, match="not read in this run"):
        read(workspace, run, web, tmp_path, {"url": "https://andes.example/otra",
                                            "lines": [1, 2], "title": "x", "company": "y"})


def test_a_synonym_is_drafted_from_the_capture(workspace, run, web, tmp_path):
    url = "https://andes.example/empleos/3"
    web.pages[url] = (200, posting_page(title="Ingeniero de Datos"))
    summary = read(workspace, run, web, tmp_path, url)
    assert summary["other_title"] == [{"url": url, "title": "Ingeniero de Datos"}]
    requests = len(web.urls)
    summary = read(workspace, run, web, tmp_path, {"url": url, "synonym": True})
    assert len(web.urls) == requests
    assert [d["title"] for d in drafts_of(summary)] == ["Ingeniero de Datos"]


# ── careers listings ──────────────────────────────────────────────────────

def lever_job(job_id, title, country, location, created_days_ago=1):
    created = datetime.combine(TODAY - timedelta(days=created_days_ago), time(12),
                               tzinfo=UTC)
    return {"id": job_id, "text": title, "country": country,
            "categories": {"location": location, "commitment": "Full-time"},
            "createdAt": int(created.timestamp() * 1000),
            "hostedUrl": f"https://jobs.lever.co/andes-ficticia/{job_id}",
            "descriptionPlain": "Somos una empresa ficticia.",
            "lists": [{"text": "Requisitos", "content": "<li>Python</li><li>SQL</li>"}],
            "additionalPlain": "Beneficios ficticios.", "workplaceType": "hybrid"}


def test_a_lever_board_is_read_through_its_api(workspace, run, web, tmp_path):
    ids = ["11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222",
           "33333333-3333-3333-3333-333333333333"]
    web.pages["https://api.lever.co/v0/postings/andes-ficticia?mode=json"] = (200, json.dumps([
        lever_job(ids[0], "Senior Data Engineer", "PE", "Lima"),
        lever_job(ids[1], "Senior Data Engineer", "CO", "Bogotá"),
        lever_job(ids[2], "Product Designer", "PE", "Lima")]))
    summary = read(workspace, run, web, tmp_path, "https://jobs.lever.co/andes-ficticia")
    (draft,) = drafts_of(summary)
    assert draft["url"] == f"https://jobs.lever.co/andes-ficticia/{ids[0]}"
    assert draft["country"] == "PE" and draft["contract_type"] == "full-time"
    assert draft["description"] == ("Somos una empresa ficticia.\n\nRequisitos\n- Python\n\n"
                                    "- SQL\n\nBeneficios ficticios.")
    assert summary["other_title"] == [{"url": f"https://jobs.lever.co/andes-ficticia/{ids[2]}",
                                       "title": "Product Designer"}]
    assert not any(u.endswith("robots.txt") for u in web.urls)


def test_an_ashby_board_is_read_through_its_api(workspace, run, web, tmp_path):
    job_id = "44444444-4444-4444-4444-444444444444"
    web.pages["https://api.ashbyhq.com/posting-api/job-board/andes?includeCompensation=true"] = (
        200, json.dumps({"jobs": [
            {"id": job_id, "title": "Data Engineer", "location": "Lima, Peru",
             "isRemote": False, "isListed": True,
             "publishedAt": f"{TODAY.isoformat()}T09:00:00Z",
             "jobUrl": f"https://jobs.ashbyhq.com/andes/{job_id}",
             "descriptionPlain": "Descripción ficticia completa.",
             "employmentType": "FullTime"},
            {"id": "x", "title": "Data Engineer", "location": "Madrid", "isRemote": False}]}))
    summary = read(workspace, run, web, tmp_path, "https://jobs.ashbyhq.com/andes",
                   location="Peru; Lima")
    (draft,) = drafts_of(summary)
    assert (draft["url"], draft["country"], draft["description"]) == (
        f"https://jobs.ashbyhq.com/andes/{job_id}", "PE", "Descripción ficticia completa.")


def test_a_careers_page_returns_matching_links(workspace, run, web, tmp_path):
    url = "https://andes.example/careers"
    web.pages[url] = (200, "<html><body><h1>Trabaja con nosotros</h1>"
                      '<a href="/careers/data-engineer-1">Senior Data Engineer</a>'
                      '<a href="/careers/data-engineer-2">Data Engineer (Lima)</a>'
                      '<a href="/careers/designer">Product Designer</a>'
                      '<a href="https://pe.indeed.com/x">Data Engineer en Indeed</a>'
                      + FILLER + "</body></html>")
    summary = read(workspace, run, web, tmp_path, url)
    assert summary["candidate_links"] == [{"page": url, "links": [
        "https://andes.example/careers/data-engineer-1",
        "https://andes.example/careers/data-engineer-2"]}]
    assert drafts_of(summary) == []


# ── originals and copies ──────────────────────────────────────────────────

def test_a_copy_leads_to_the_original(workspace, run, web, tmp_path):
    job_id = "55555555-5555-5555-5555-555555555555"
    copy = "https://empleos-copia.example/aviso/99"
    web.pages[copy] = (200, "<html><body><h1>Data Engineer</h1>" + FILLER +
                       f'<a href="https://jobs.lever.co/andes-ficticia/{job_id}">'
                       "Postular en el sitio de la empresa</a></body></html>")
    web.pages[f"https://api.lever.co/v0/postings/andes-ficticia/{job_id}"] = (
        200, json.dumps(lever_job(job_id, "Data Engineer", "PE", "Lima")))
    summary = read(workspace, run, web, tmp_path, copy)
    (draft,) = drafts_of(summary)
    assert draft["source_site"] == "jobs.lever.co"
    assert summary["copies"] == [{"url": copy, "kept": draft["url"]}]


def test_the_same_posting_twice_keeps_the_company_page(workspace, run, web, tmp_path):
    own = "https://andes.example/jobs/1"
    other = "https://portal-ficticio.example/oferta/1"
    web.pages[other] = (200, posting_page())
    web.pages[own] = (200, posting_page())
    summary = read(workspace, run, web, tmp_path, other, own)
    assert [d["url"] for d in drafts_of(summary)] == [own]
    assert summary["copies"] == [{"url": other, "kept": own}]
    # Found again in a later call of the run: not drafted twice.
    third = "https://otro-portal.example/oferta/1"
    web.pages[third] = (200, posting_page())
    again = read(workspace, run, web, tmp_path, third)
    assert drafts_of(again) == [] and again["copies"] == [{"url": third, "kept": own}]


def test_a_posting_stored_earlier_is_seen_not_drafted(workspace, run, web, tmp_path, cli):
    url = "https://andes.example/jobs/1"
    web.pages[url] = (200, posting_page())
    summary = read(workspace, run, web, tmp_path, url)
    readings = tmp_path / "readings.json"
    readings.write_text(json.dumps([{"external_id": url, "work_mode": "hybrid",
                                     "language": "es", "flags": []}]), encoding="utf-8")
    code, out, _ = cli("postings", "import", str(run["run_id"]), summary["drafts_path"],
                       "--readings", str(readings))
    assert code == 0, out
    again = read(workspace, run, web, tmp_path, url)
    assert again["new"] == 0 and again["already_seen"] == 1


def test_a_call_reads_at_most_the_page_limit(workspace, run, web, tmp_path, monkeypatch):
    real = reader.common.context

    def small(*args, **kwargs):
        ctx = real(*args, **kwargs)
        ctx.max_results = 2
        return ctx

    monkeypatch.setattr(reader.common, "context", small)
    links = [f"https://andes.example/jobs/{n}" for n in range(1, 5)]
    for n, link in enumerate(links, 1):
        web.pages[link] = (200, posting_page(title=f"Data Engineer {n}"))
    summary = read(workspace, run, web, tmp_path, *links)
    assert web.page_requests() == links[:2]
    assert summary["capped"] is True and len(drafts_of(summary)) == 2


def test_a_site_refusing_its_robots_txt_is_offered_as_a_provider(workspace, run, web, tmp_path):
    web.pages["https://pe.bolsa.example/robots.txt"] = (403, "Forbidden")
    summary = read(workspace, run, web, tmp_path, "https://pe.bolsa.example/oferta/1")
    assert web.page_requests() == []
    assert summary["refused"] == [{"url": "https://pe.bolsa.example/oferta/1",
                                   "reason": "site_refused"}]
    assert summary["suggest_provider"] == ["pe.bolsa.example"]


def test_a_lever_synonym_is_read_again_from_the_api(workspace, run, web, tmp_path):
    job_id = "66666666-6666-6666-6666-666666666666"
    web.pages["https://api.lever.co/v0/postings/andes-ficticia?mode=json"] = (200, json.dumps([
        lever_job(job_id, "Ingeniero de Datos", "PE", "Lima")]))
    web.pages[f"https://api.lever.co/v0/postings/andes-ficticia/{job_id}"] = (
        200, json.dumps(lever_job(job_id, "Ingeniero de Datos", "PE", "Lima")))
    first = read(workspace, run, web, tmp_path, "https://jobs.lever.co/andes-ficticia")
    (other,) = first["other_title"]
    summary = read(workspace, run, web, tmp_path, {"url": other["url"], "synonym": True})
    assert [d["title"] for d in drafts_of(summary)] == ["Ingeniero de Datos"]
