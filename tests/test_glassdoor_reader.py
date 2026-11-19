"""provider-glassdoor: the Glassdoor reader against a fake fetcher and fictional pages.
No test opens a browser or reaches Glassdoor."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from jobtracker.core import db
from jobtracker.core.errors import JobTrackerError
from jobtracker.core.readers import glassdoor

PERSONA = json.loads((Path(__file__).parent / "fixtures" / "persona.json").read_text(
    encoding="utf-8"))
TITLE = "Data Engineer"
SEARCH = ("https://www.glassdoor.com/Job/peru-data-engineer-jobs-SRCH_IL.0,4_IN189_KO5,18.htm"
          "?fromAge=7")
DESCRIPTION_HTML = ("<p>Somos una empresa <b>ficticia</b> de datos.</p><ul><li>Python y SQL</li>"
                    "<li>Modalidad híbrida: 2 días en oficina</li></ul><p>Contrato "
                    "indefinido y buen ambiente para crecer con nosotros.</p>")


def posting_url(job_id: str) -> str:
    return f"https://www.glassdoor.com/job-listing/ingeniero-de-datos-{job_id}-JV_KO0,18.htm?jl={job_id}"


def search_page(*ids: str, total: int | None = None, status: int = 200,
                title: str | None = None, more: list[str] | None = None,
                wall: bool = False) -> glassdoor.SearchPage:
    count = total if total is not None else len(ids)
    title = title or f"{count} data engineer Jobs in Peru | Glassdoor"
    cards = "".join(
        f'<li class="JobsList_item" data-jobid="{i}" data-test="jobListing"><div>'
        f'<a class="JobCard_jobTitle__x" href="{posting_url(i)}&amp;pos=10{n}&amp;guid=abc">'
        f"Ingeniero {i}</a></div></li>" for n, i in enumerate(ids))
    html = f"<html><head><title>{title}</title></head><body><ul>{cards}</ul></body></html>"
    return glassdoor.SearchPage(status, title, html, more or [], wall)


def more_body(*items: tuple[str, int, list[str]], total: int = 40) -> str:
    listings = [{"jobview": {
        "header": {"ageInDays": age, "indeedJobAttribute": {
            "extractedJobAttributes": [{"key": "k", "value": v} for v in attributes]}},
        "job": {"listingId": int(job_id)}}} for job_id, age, attributes in items]
    return json.dumps({"data": {"jobListings": {"totalJobsCount": total,
                                                "jobListings": listings}}})


def posting_page(job_id: str, days_ago: int = 1, description: str = DESCRIPTION_HTML,
                 **extra) -> tuple:
    data = {"@context": "https://schema.org/", "@type": "JobPosting",
            "title": f"Ingeniero de Datos {job_id}",
            "datePosted": f"{(date.today() - timedelta(days=days_ago)).isoformat()}T00:00:00",
            "hiringOrganization": {"@type": "Organization", "name": "Andes Datos Ficticios"},
            "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress",
                                                          "addressLocality": "Lima",
                                                          "addressCountry": "PE"}},
            "description": description, **extra}
    html = (f'<html><head><title>Andes Datos Ficticios hiring {job_id}</title>'
            f'<script type="application/ld+json">{json.dumps(data)}</script></head>'
            "<body></body></html>")
    return 200, f"Andes Datos Ficticios hiring {job_id}", html


class FakeFetcher:
    """Search results and posting pages by URL; records actions and the clock."""

    def __init__(self) -> None:
        self.search_result = search_page()
        self.pages: dict[str, tuple] = {}
        self.headers: dict[str, dict] = {}            # response headers by URL
        self.last_headers: dict = {}
        self.actions: list[str] = []
        self.times: list[float] = []
        self.max_cards: list[int] = []
        self.locales: list[str] = []
        self.now = 1_000.0
        self.closed = 0

    def __call__(self, locale: str, pause: float) -> FakeFetcher:
        self.locales.append(locale)
        return self

    def search(self, url: str, max_cards: int) -> glassdoor.SearchPage:
        self.actions.append(url)
        self.times.append(self.now)
        self.max_cards.append(max_cards)
        return self._next(self.search_result)

    def page(self, url: str) -> tuple:
        self.actions.append(url)
        self.times.append(self.now)
        job_id = url.rsplit("jl=", 1)[-1]
        self.last_headers = self.headers.get(url, {})
        return self._next(self.pages.get(url, posting_page(job_id)))

    @staticmethod
    def _next(answer):
        """A list of answers is given out in order; its last one is repeated."""
        if isinstance(answer, list):
            return answer.pop(0) if len(answer) > 1 else answer[0]
        return answer

    def close(self) -> None:
        self.closed += 1

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def opened(self) -> list[str]:
        return [a.rsplit("jl=", 1)[-1] for a in self.actions if "job-listing" in a]


@pytest.fixture
def fake() -> FakeFetcher:
    return FakeFetcher()


def set_profile(workspace, cli, **changes) -> None:
    needs = dict(PERSONA["job_needs"])
    needs["titles"] = PERSONA["target_titles"]
    needs.update(changes)
    path = workspace.home / "profile-input.json"
    path.write_text(json.dumps(needs), encoding="utf-8")
    assert cli("profile", "set", str(path))[0] == 0
    path.unlink()


@pytest.fixture
def run(workspace, cli):
    set_profile(workspace, cli)
    assert cli("providers", "enable", "glassdoor")[0] == 0
    code, run, _ = cli("run", "start", "--days", "7")
    assert code == 0 and run["to_search"] == ["glassdoor"], run
    return run


def read(workspace, run, fake, title=TITLE, **kwargs):
    return glassdoor.read(workspace, run["run_id"], title, fetcher=fake, clock=fake.clock,
                          sleep=fake.sleep, **kwargs)


def drafts_of(summary) -> list[dict]:
    return json.loads(Path(summary["drafts_path"]).read_text(encoding="utf-8"))


# ── URLs and countries ────────────────────────────────────────────────────

@pytest.mark.parametrize("days,expected", [(1, 1), (2, 3), (7, 7), (10, 14), (30, 30),
                                           (31, None)])
def test_posting_age(days, expected):
    assert glassdoor.from_age(days) == expected


def test_search_and_salary_urls():
    assert glassdoor.search_url("peru", 189, "Data Engineer", 7) == SEARCH
    assert glassdoor.search_url("peru", 189, "Ingeniería de Datos", 60) == (
        "https://www.glassdoor.com/Job/peru-ingenieria-de-datos-jobs-"
        "SRCH_IL.0,4_IN189_KO5,24.htm")
    assert glassdoor.salary_url("peru", 189, "Data Engineer") == (
        "https://www.glassdoor.com/Salaries/peru-data-engineer-salary-"
        "SRCH_IL.0,4_IN189_KO5,18.htm")


def test_a_pasted_search_url_gives_the_country_id():
    pasted = ("https://www.glassdoor.com/Job/chile-analista-jobs-SRCH_IL.0,5_IN48_KO6,14.htm"
              "?fromAge=3")
    assert glassdoor.parse_search_url(pasted) == {"id": 48, "place": "chile",
                                                  "from_url": pasted}
    for bad in ("https://www.glassdoor.com/Salaries/x.htm", "https://example.com/Job/a-SRCH_IL.0,1_IN1",
                "not a url", ""):
        with pytest.raises(JobTrackerError) as error:
            glassdoor.parse_search_url(bad)
        assert error.value.code == "invalid_search_url"


def test_search_uses_the_country_table_and_the_window(workspace, run, fake):
    read(workspace, run, fake)
    assert fake.actions == [SEARCH] and fake.max_cards == [150]
    assert fake.locales == ["es-PE"] and fake.closed == 1


def test_unknown_country_needs_one_pasted_url_then_remembers_it(workspace, cli, fake):
    set_profile(workspace, cli, country="CL")
    assert cli("providers", "enable", "glassdoor")[0] == 0
    _, run, _ = cli("run", "start", "--days", "7")
    with pytest.raises(JobTrackerError) as error:
        read(workspace, run, fake)
    assert error.value.code == "missing_country" and "--search-url" in error.value.message
    pasted = "https://www.glassdoor.com/Job/chile-data-engineer-jobs-SRCH_IL.0,5_IN48_KO6,19.htm"
    read(workspace, run, fake, search_url_given=pasted)
    read(workspace, run, fake, title="Analytics Engineer")       # no URL this time
    assert fake.actions[0].startswith("https://www.glassdoor.com/Job/chile-data-engineer-jobs-"
                                      "SRCH_IL.0,5_IN48_KO6,19.htm")
    assert "chile-analytics-engineer-jobs-SRCH_IL.0,5_IN48_" in fake.actions[1]
    saved = json.loads(glassdoor.settings_path(workspace).read_text(encoding="utf-8"))
    assert saved["countries"]["CL"]["id"] == 48


# ── drafts ────────────────────────────────────────────────────────────────

def test_one_title_read_into_drafts(workspace, run, fake):
    fake.search_result = search_page(
        "101", "102", "103", total=3,
        more=[more_body(("102", 2, ["Permanente", "Tiempo completo"]), ("103", 12, []),
                        total=3)])
    summary = read(workspace, run, fake)
    assert {k: summary[k] for k in ("site_total", "listed", "cards", "outside_window", "new",
                                    "stopped")} == {
        "site_total": 3, "listed": 3, "cards": 3, "outside_window": 1, "new": 2,
        "stopped": None}
    assert fake.opened() == ["101", "102"]            # 103 is outside the window: never opened
    first, second = drafts_of(summary)
    assert first["url"] == posting_url("101")          # tracking parameters removed
    assert (first["title"], first["company"], first["location"], first["country"]) == (
        "Ingeniero de Datos 101", "Andes Datos Ficticios", "Lima", "PE")
    assert first["posted_at"] == (date.today() - timedelta(days=1)).isoformat()
    assert first["description"] == (
        "Somos una empresa ficticia de datos.\n\n- Python y SQL\n\n- Modalidad híbrida: 2 días "
        "en oficina\n\nContrato indefinido y buen ambiente para crecer con nosotros.")
    assert first["work_mode"] is None and first["language"] is None   # the agent's reading
    assert second["contract_type"] == "full-time"
    assert second["site_attributes"] == ["Permanente", "Tiempo completo"]
    folder = Path(run["capture_folder"])
    assert len(list(folder.glob("glassdoor-*-more.json"))) == 1
    assert len(list(folder.glob("glassdoor-[0-9]*.html"))) == 3


def test_similar_jobs_are_not_results(workspace, run, fake):
    result = search_page("111", total=1)
    similar = search_page("112", "113").html.split("<ul>", 1)[1].split("</ul>", 1)[0]
    result.html = result.html.replace(
        "</body>", f'<section data-test="related-jobs-list"><h3>Similar jobs</h3><ul>{similar}'
        "</ul></section></body>")
    fake.search_result = result
    summary = read(workspace, run, fake)
    assert (summary["site_total"], summary["listed"], summary["new"]) == (1, 1, 1)
    assert fake.opened() == ["111"]


def test_ages_in_the_page_data_keep_old_postings_closed(workspace, run, fake):
    result = search_page("121", "122")
    flight = ('self.__next_f.push([1,"{\\"jobview\\":{\\"header\\":{\\"ageInDays\\":2},'
              '\\"job\\":{\\"listingId\\":121}}},{\\"jobview\\":{\\"header\\":{\\"ageInDays\\":40},'
              '\\"job\\":{\\"listingId\\":122}}}"])')
    result.html = result.html.replace("</body>", f"<script>{flight}</script></body>")
    fake.search_result = result
    summary = read(workspace, run, fake)
    assert (summary["outside_window"], summary["new"]) == (1, 1)
    assert fake.opened() == ["121"]


def test_salary_stated_by_the_posting_is_a_hint(workspace, run, fake):
    fake.search_result = search_page("201")
    fake.pages[posting_url("201")] = posting_page("201", baseSalary={
        "@type": "MonetaryAmount", "currency": "PEN",
        "value": {"@type": "QuantitativeValue", "minValue": 4000, "maxValue": 6000,
                  "unitText": "MONTH"}}, employmentType="FULL_TIME")
    draft = drafts_of(read(workspace, run, fake))[0]
    assert draft["site_salary"] == {"currency": "PEN", "min": 4000, "max": 6000,
                                    "unit": "MONTH"}
    assert draft["site_employment_type"] == "FULL_TIME"
    assert draft["published_salary"] is None          # the agent decides


def test_readings_import_the_drafts(workspace, run, fake, cli, tmp_path):
    fake.search_result = search_page("301")
    summary = read(workspace, run, fake)
    readings = tmp_path / "r.json"
    readings.write_text(json.dumps([{"external_id": "301", "work_mode": "hybrid",
                                     "work_mode_detail": "Modalidad híbrida: 2 días en oficina",
                                     "language": "es"}]), encoding="utf-8")
    code, report, _ = cli("postings", "import", str(run["run_id"]), summary["drafts_path"],
                          "--readings", str(readings))
    assert code == 0 and report["new"] == 1, report


def test_a_posting_older_than_the_window_by_its_own_date_is_dropped(workspace, run, fake):
    fake.search_result = search_page("401")           # no age from "Show more"
    fake.pages[posting_url("401")] = posting_page("401", days_ago=20)
    summary = read(workspace, run, fake)
    assert (summary["outside_window"], summary["new"]) == (1, 0)


def test_no_results(workspace, run, fake):
    fake.search_result = search_page(total=0)
    summary = read(workspace, run, fake)
    assert (summary["listed"], summary["new"], summary["stopped"]) == (0, 0, None)


def test_an_unreadable_search_page_is_loaded_again_then_ends_only_that_title(
        workspace, run, fake):
    fake.search_result = search_page(title="Glassdoor")    # no cards, no total
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None and summary["retries"] == 1
    assert summary["title_problem"]["kind"] == "no_results_read"
    assert "glassdoor-2.html" in summary["title_problem"]["detail"]
    assert fake.actions == [SEARCH, SEARCH] and fake.times[1] - fake.times[0] >= 5
    fake.search_result = search_page("931")
    summary = read(workspace, run, fake, title="Analytics Engineer")     # not refused
    assert summary["new"] == 1 and summary["title_problem"] is None


def test_a_search_page_that_reads_on_the_second_load_goes_on(workspace, run, fake):
    fake.search_result = [search_page(title="Glassdoor"), search_page("932")]
    summary = read(workspace, run, fake)
    assert (summary["retries"], summary["new"], summary["title_problem"]) == (1, 1, None)


def test_every_title_is_tried_and_a_likely_site_change_is_reported(workspace, run, fake):
    fake.search_result = search_page(title="Glassdoor")
    first = read(workspace, run, fake)
    assert first["site_may_have_changed"] is False      # one title is not evidence
    fake.search_result = search_page(total=0)            # no results: neither for nor against
    assert read(workspace, run, fake, title="Data Analyst")["no_results"] is True
    fake.search_result = search_page(title="Glassdoor")
    third = read(workspace, run, fake, title="Analytics Engineer")
    assert third["stopped"] is None and third["site_may_have_changed"] is True
    fake.search_result = search_page("941")
    fourth = read(workspace, run, fake, title="BI Engineer")        # still tried
    assert fourth["new"] == 1 and fourth["site_may_have_changed"] is False
    with db.session(workspace) as conn:
        row = conn.execute("SELECT providers FROM search_runs WHERE id = ?",
                           (run["run_id"],)).fetchone()
    item = next(p for p in json.loads(row["providers"]) if p["id"] == "glassdoor")
    assert item["status"] != "failed"


# ── stored, duplicates, unreadable, pacing ───────────────────────────────

def test_stored_and_repeated_postings_are_not_opened(workspace, run, fake, cli, tmp_path):
    fake.search_result = search_page("501")
    summary = read(workspace, run, fake)
    readings = tmp_path / "r.json"
    readings.write_text(json.dumps([{"external_id": "501", "language": "es"}]), encoding="utf-8")
    cli("postings", "import", str(run["run_id"]), summary["drafts_path"], "--readings",
        str(readings))
    again = read(workspace, run, fake, title="Analytics Engineer")    # same posting, same run
    assert again["duplicate_in_run"] == 1 and fake.opened() == ["501"]
    cli("run", "finish", str(run["run_id"]))
    _, second_run, _ = cli("run", "start", "--days", "7")
    later = read(workspace, second_run, fake)
    assert later["already_seen"] == 1 and fake.opened() == ["501"]     # never opened again


def test_an_unreadable_posting_is_skipped(workspace, run, fake):
    fake.search_result = search_page("601", "602")
    fake.pages[posting_url("601")] = posting_page("601", description="<p>Ver más</p>")
    summary = read(workspace, run, fake)
    assert summary["unreadable"] == ["601"] and summary["new"] == 1
    assert summary["stopped"] is None


def test_two_unreadable_postings_in_a_row_end_only_that_title(workspace, run, fake):
    fake.search_result = search_page("700", "701", "702", "703")
    for job_id in ("701", "702"):
        fake.pages[posting_url(job_id)] = (200, "x", "<html><title>x</title></html>")
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None and summary["new"] == 1       # 700 is kept
    assert summary["title_problem"]["kind"] == "no_description"
    assert fake.opened() == ["700", "701", "702"]
    fake.search_result = search_page("704")
    assert read(workspace, run, fake, title="Analytics Engineer")["new"] == 1


def test_pacing_within_and_across_calls(workspace, run, fake):
    fake.search_result = search_page("801", "802")
    read(workspace, run, fake)
    fake.search_result = search_page("803")
    read(workspace, run, fake, title="Analytics Engineer")
    gaps = [b - a for a, b in zip(fake.times, fake.times[1:], strict=False)]
    assert len(fake.times) == 5 and all(gap >= 5 for gap in gaps), gaps


# ── stops ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("result", [
    search_page(status=403, title="Security | Glassdoor"),
    search_page(title="Attention Required! | Cloudflare"),
    search_page("901", wall=True),
])
def test_blocked_stops_glassdoor_for_the_run(workspace, run, fake, result):
    fake.search_result = result
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "blocked" and fake.opened() == []
    with pytest.raises(JobTrackerError) as error:
        read(workspace, run, fake, title="Analytics Engineer")
    assert error.value.code == "provider_stopped"
    with db.session(workspace) as conn:
        row = conn.execute("SELECT providers FROM search_runs WHERE id = ?",
                           (run["run_id"],)).fetchone()
    item = next(p for p in json.loads(row["providers"]) if p["id"] == "glassdoor")
    assert (item["status"], item["reason"]) == ("failed", "blocked")


def test_a_blocked_posting_page_stops_and_keeps_what_was_read(workspace, run, fake):
    fake.search_result = search_page("911", "912", "913")
    fake.pages[posting_url("912")] = (403, "Un momento…", "<html></html>")
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "blocked" and summary["new"] == 1
    assert fake.opened() == ["911", "912"]


# ── soft blocks (provider-throttling) ────────────────────────────────────

CHALLENGE = search_page(title="Un momento…")


def test_a_security_check_that_clears_is_waited_out(workspace, run, fake):
    fake.search_result = [CHALLENGE, search_page("931")]
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None and summary["new"] == 1
    assert 10 <= fake.times[1] - fake.times[0] <= 20


def test_a_security_check_that_stays_is_a_cool_down(workspace, run, fake):
    fake.search_result = CHALLENGE
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "throttled" and fake.opened() == []
    assert len(fake.actions) == 3
    with pytest.raises(JobTrackerError) as error:
        read(workspace, run, fake, title="Analytics Engineer")
    assert error.value.code == "provider_cooling"


def test_a_throttled_posting_is_opened_after_the_cool_down(workspace, run, fake):
    fake.search_result = search_page("941", "942", "943")
    fake.pages[posting_url("942")] = [(429, "", "")] * 3 + [posting_page("942")]
    first = read(workspace, run, fake)
    assert first["stopped"]["reason"] == "throttled" and first["new"] == 1
    fake.now += 15 * 60
    before = len(fake.opened())
    second = read(workspace, run, fake)
    assert second["stopped"] is None and second["new"] == 2
    assert fake.opened()[before:] == ["942", "943"]                # 941 not reopened


def test_throttled_salary_page(workspace, cli, fake):
    set_profile(workspace, cli)
    url = "https://www.glassdoor.com/Salaries/peru-data-engineer-salary-SRCH_IL.0,4_IN189_KO5,18.htm"
    fake.pages[url] = (429, "", "<html></html>")
    result = glassdoor.salary(workspace, TITLE, fetcher=fake, clock=fake.clock,
                              sleep=fake.sleep)
    assert result["data"] is False and result["throttled"] is True and result["resume_after"]
    assert len(fake.actions) == 3


def test_show_more_that_does_not_parse_keeps_the_cards(workspace, run, fake):
    fake.search_result = search_page("921", more=["<html>not json</html>"])
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None and summary["show_more_unreadable"] == 1
    assert summary["new"] == 1


# ── salary ────────────────────────────────────────────────────────────────

def salary_page(duration: str = "P1M", with_data: bool = True) -> tuple:
    occupation = {"@context": "https://schema.org/", "@type": "Occupation",
                  "name": "Data Engineer", "estimatedSalary": [{
                      "@type": "MonetaryAmountDistribution", "name": "base", "currency": "PEN",
                      "duration": duration, "percentile10": 3000, "percentile25": 4200,
                      "median": 6100, "percentile75": 7500, "percentile90": 10300}]
                  if with_data else []}
    body = ("<h2>Recent salaries shared by Data Engineer</h2><p>48 salaries</p>"
            "<p>submitted on Nov 10, 2026</p><p>submitted on Nov 12, 2026</p>"
            "<script>var x = '999 salaries';</script>"
            "<p>The average salary is PEN 6,100 per year</p>")
    html = (f'<html><head><title>Data Engineer Salaries | Glassdoor</title>'
            f'<script type="application/ld+json">{json.dumps(occupation)}</script></head>'
            f"<body>{body}</body></html>")
    return 200, "Data Engineer Salaries | Glassdoor", html


def test_salary_page_becomes_an_evidence_draft(workspace, cli, fake):
    set_profile(workspace, cli)
    url = "https://www.glassdoor.com/Salaries/peru-data-engineer-salary-SRCH_IL.0,4_IN189_KO5,18.htm"
    fake.pages[url] = salary_page()
    result = glassdoor.salary(workspace, TITLE, fetcher=fake, today=date(2026, 11, 18))
    assert fake.actions == [url] and fake.closed == 1
    assert result["data"] is True
    evidence = result["evidence"]
    assert {k: evidence[k] for k in ("source", "url", "amount_min", "amount_max", "currency",
                                     "period", "sample_size", "observed_on", "country")} == {
        "source": "Glassdoor", "url": url, "amount_min": 4200, "amount_max": 7500,
        "currency": "PEN", "period": "month", "sample_size": 48,
        "observed_on": "2026-11-12", "country": "PE"}
    assert "median 6100" in evidence["summary"]


def test_salary_evidence_is_accepted_by_the_salary_store(workspace, cli, fake, tmp_path):
    set_profile(workspace, cli)
    url = "https://www.glassdoor.com/Salaries/peru-data-engineer-salary-SRCH_IL.0,4_IN189_KO5,18.htm"
    fake.pages[url] = salary_page()
    evidence = glassdoor.salary(workspace, TITLE, fetcher=fake, today=date.today())["evidence"]
    record = {**evidence, "basis": "gross", "level": "Mid",
              "research": {"company": "Andes Datos Ficticios", "role": TITLE, "location": "Lima"}}
    path = tmp_path / "e.json"
    path.write_text(json.dumps([record]), encoding="utf-8")
    code, out, _ = cli("salary", "evidence", "add", str(path))
    assert code == 0, out


@pytest.mark.parametrize("page,reason", [
    (salary_page(with_data=False), "no salary distribution"),
    (salary_page(duration="PT1H"), "unusable distribution"),
])
def test_salary_page_without_usable_data(workspace, cli, fake, page, reason):
    set_profile(workspace, cli)
    url = "https://www.glassdoor.com/Salaries/peru-data-engineer-salary-SRCH_IL.0,4_IN189_KO5,18.htm"
    fake.pages[url] = page
    result = glassdoor.salary(workspace, TITLE, fetcher=fake)
    assert result["data"] is False and reason in result["reason"]


def test_yearly_salary_period(workspace, cli, fake):
    set_profile(workspace, cli)
    url = "https://www.glassdoor.com/Salaries/peru-data-engineer-salary-SRCH_IL.0,4_IN189_KO5,18.htm"
    fake.pages[url] = salary_page(duration="P1Y")
    assert glassdoor.salary(workspace, TITLE, fetcher=fake)["evidence"]["period"] == "year"


def test_blocked_salary_page(workspace, cli, fake):
    set_profile(workspace, cli)
    url = "https://www.glassdoor.com/Salaries/peru-data-engineer-salary-SRCH_IL.0,4_IN189_KO5,18.htm"
    fake.pages[url] = (403, "Un momento…", "<html></html>")
    result = glassdoor.salary(workspace, TITLE, fetcher=fake)
    assert result["data"] is False and result["blocked"] is True


def test_provider_file():
    from jobtracker.core import providers

    listed = {p["id"]: p for p in providers.list_providers()}
    item = listed["glassdoor"]
    assert item["valid"], item["problems"]
    assert (item["kind"], item["coverage"], item["access"], item["dependencies"],
            item["max_results_per_query"], item["requires_login"]) == (
        "both", "global", "scrapling", ["scrapling"], 150, False)
    text = (Path(__file__).resolve().parents[1] / "providers" / "glassdoor.md").read_text(
        encoding="utf-8")
    assert "| PE | 189 | peru |" in text
    for required in ("jt providers read glassdoor <run_id> --title", "--readings",
                     "jt providers salary glassdoor", "--search-url", "Terms of use"):
        assert required in text


# ── saved pages: where the results come from ─────────────────────────────

FIXTURES = Path(__file__).parent / "fixtures" / "glassdoor"
SALARY = "https://www.glassdoor.com/Salaries/peru-data-engineer-salary-SRCH_IL.0,4_IN189_KO5,18.htm"


def saved(name: str, status: int = 200) -> glassdoor.SearchPage:
    html = (FIXTURES / name).read_text(encoding="utf-8")
    return glassdoor.SearchPage(status, glassdoor._title(html), html)


def test_results_from_the_page_data_with_ages_and_show_more_cards():
    results = glassdoor.parse_results(saved("search-results.html").html)
    assert results.source == "page-data" and not results.empty
    assert [c["external_id"] for c in results.cards] == ["701", "702", "703"]
    assert results.cards[0]["url"].endswith("-JV_IC2.htm?jl=701")     # no tracking
    assert results.ages == {"701": 1, "702": 25}


def test_renamed_cards_are_read_from_the_page_data(workspace, run, fake):
    fake.search_result = saved("search-renamed-cards.html")
    summary = read(workspace, run, fake)
    assert (summary["source"], summary["listed"], summary["new"]) == ("page-data", 3, 3)
    assert fake.opened() == ["711", "712", "713"]


def test_json_ld_list_when_there_is_no_page_data():
    results = glassdoor.parse_results(saved("search-json-ld.html").html)
    assert results.source == "json-ld"
    assert [c["external_id"] for c in results.cards] == ["721", "722"]   # 796 is similar


def test_links_when_nothing_else_answers():
    html = ('<html><body><div><a href="/job-listing/analista-JV_IC2.htm?jl=731">x</a></div>'
            '<section data-test="related-jobs-list"><a href="/job-listing/o-JV.htm?jl=732">y'
            "</a></section></body></html>")
    results = glassdoor.parse_results(html)
    assert results.source == "links" and [c["external_id"] for c in results.cards] == ["731"]
    assert results.cards[0]["url"] == ("https://www.glassdoor.com/job-listing/"
                                       "analista-JV_IC2.htm?jl=731")


def test_only_similar_jobs_is_no_results(workspace, run, fake):
    """Glassdoor's "limited or no results" page: the title says 1, the page lists none."""
    fake.search_result = saved("search-only-similar.html")
    summary = read(workspace, run, fake)
    assert summary["site_total"] == 1 and summary["no_results"] is True
    assert (summary["listed"], summary["stopped"]) == (0, None) and fake.opened() == []
    fake.search_result = search_page("741")
    assert read(workspace, run, fake, title="Analytics Engineer")["new"] == 1


def test_no_results_notice_without_page_data():
    html = saved("search-only-similar.html").html.split("<script>self.__next_f")[0]
    results = glassdoor.parse_results(html)
    assert results.cards == [] and results.empty is True


def test_saved_unreadable_page_is_a_title_problem(workspace, run, fake):
    fake.search_result = saved("search-unreadable.html")
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None and summary["title_problem"]["kind"] == "no_results_read"


# ── salary: variants, pacing, refusals ───────────────────────────────────

def salary_call(workspace, fake, titles, **kwargs):
    return glassdoor.salary(workspace, titles, fetcher=fake, today=date(2026, 11, 18),
                            clock=fake.clock, sleep=fake.sleep, **kwargs)


def refused(retry_after: str | None = None):
    html = (FIXTURES / "salary-429.html").read_text(encoding="utf-8")
    return (429, glassdoor._title(html), html), ({"Retry-After": retry_after}
                                                  if retry_after else {})


def test_salary_variants_tried_in_order_until_one_has_data(workspace, cli, fake):
    set_profile(workspace, cli)
    spanish = glassdoor.salary_url("peru", 189, "Jefe de Marca")
    english = glassdoor.salary_url("peru", 189, "Brand Manager")
    fake.pages[spanish] = salary_page(with_data=False)
    fake.pages[english] = salary_page()
    result = salary_call(workspace, fake, ["Jefe de Marca", "Brand Manager", "Marketing"])
    assert result["data"] is True and result["evidence"]["url"] == english
    assert fake.actions == [spanish, english]                # the third is not needed
    assert [t["title"] for t in result["tried"]] == ["Jefe de Marca", "Brand Manager"]
    assert fake.times[1] - fake.times[0] >= glassdoor.SALARY_MIN_SECONDS


def test_salary_titles_are_limited(workspace, cli, fake):
    set_profile(workspace, cli)
    with pytest.raises(JobTrackerError):
        salary_call(workspace, fake, ["a", "b", "c", "d"])


def test_salary_pages_are_paced_across_calls(workspace, cli, fake):
    set_profile(workspace, cli)
    fake.pages[SALARY] = salary_page()
    salary_call(workspace, fake, TITLE)
    salary_call(workspace, fake, TITLE)
    assert fake.times[1] - fake.times[0] >= glassdoor.SALARY_MIN_SECONDS


def test_a_429_with_retry_after_starts_a_cool_down(workspace, cli, fake):
    set_profile(workspace, cli)
    fake.pages[SALARY], fake.headers[SALARY] = refused("1800")
    result = salary_call(workspace, fake, [TITLE, "Analytics Engineer"])
    assert result["data"] is False and result["throttled"] is True
    assert result["minutes_left"] == 30 and "Security | Glassdoor" in result["reason"]
    assert fake.actions == [SALARY]                          # no further title tried
    before = len(fake.actions)
    fake.now += 29 * 60
    again = salary_call(workspace, fake, TITLE)              # still cooling: no page
    assert again["throttled"] is True and again["minutes_left"] == 1
    assert len(fake.actions) == before and again["tried"] == []
    fake.now += 61
    fake.pages[SALARY], fake.headers[SALARY] = salary_page(), {}
    assert salary_call(workspace, fake, TITLE)["data"] is True


def test_cool_downs_grow_and_reset_after_a_page_that_loads(workspace, cli, fake):
    set_profile(workspace, cli)
    fake.pages[SALARY], _ = refused()
    assert salary_call(workspace, fake, TITLE)["minutes_left"] == 15
    fake.now += 15 * 60
    assert salary_call(workspace, fake, TITLE)["minutes_left"] == 30
    fake.now += 30 * 60
    assert salary_call(workspace, fake, TITLE)["minutes_left"] == 60
    fake.now += 60 * 60
    assert salary_call(workspace, fake, TITLE)["minutes_left"] == 60     # capped
    fake.now += 60 * 60
    fake.pages[SALARY] = salary_page()
    assert salary_call(workspace, fake, TITLE)["data"] is True
    fake.pages[SALARY], _ = refused()
    fake.now += 60
    assert salary_call(workspace, fake, TITLE)["minutes_left"] == 15


def test_retry_after_longer_than_the_step_is_honoured(workspace, cli, fake):
    set_profile(workspace, cli)
    fake.pages[SALARY], fake.headers[SALARY] = refused("7200")
    assert salary_call(workspace, fake, TITLE)["minutes_left"] == 120


def test_salary_cli_takes_repeated_titles(workspace, cli, monkeypatch):
    set_profile(workspace, cli)
    seen = {}

    def fake_salary(paths, titles, **kwargs):
        seen["titles"] = titles
        return {"data": False, "tried": []}

    monkeypatch.setattr(glassdoor, "salary", fake_salary)
    code, out, _ = cli("providers", "salary", "glassdoor", "--title", "Jefe de Marca",
                       "--title", "Brand Manager")
    assert code == 0 and seen["titles"] == ["Jefe de Marca", "Brand Manager"], out
