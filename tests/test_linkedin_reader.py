"""provider-linkedin (reader) and job-search (readings): the LinkedIn reader against a
fake network built from fictional pages. No test sends a real request."""
from __future__ import annotations

import json
import re
import time
import urllib.parse
from datetime import date, timedelta
from pathlib import Path
from string import Template

import pytest

from jobtracker.core import db, search
from jobtracker.core.errors import JobTrackerError
from jobtracker.core.readers import linkedin

FIXTURES = Path(__file__).parent / "fixtures" / "linkedin"
PERSONA = json.loads((Path(__file__).parent / "fixtures" / "persona.json").read_text(
    encoding="utf-8"))
TITLE = "Senior Data Engineer"
DESCRIPTION = (
    "Andes Datos Ficticios is a fictional company & this posting is made up for tests.\n\n"
    "Modalidad híbrida en Lima: 2 días por semana en la oficina.\n\n"
    "Requisitos:\n\n"
    "• 5 años con Python y SQL\n"
    "• Experiencia con Airflow\n"
    "• Inglés intermedio\n\n"
    "Línea uno\nLínea dos")


def card(job_id: int, days_ago: int = 1, title: str = TITLE, salary: str = "") -> str:
    return Template((FIXTURES / "card.html").read_text(encoding="utf-8")).substitute(
        job_id=job_id, title=title, company="Andes Datos Ficticios", location="Lima, Peru",
        date=(date.today() - timedelta(days=days_ago)).isoformat(),
        salary=f'<span class="job-search-card__salary-info">{salary}</span>' if salary else "")


def page(*cards: str) -> tuple[int, bytes, None]:
    return 200, "\n".join(cards).encode("utf-8"), None


def posting(seniority: str = "Mid-Senior level", employment: str = "Full-time"):
    text = Template((FIXTURES / "posting.html").read_text(encoding="utf-8")).substitute(
        seniority=seniority, employment=employment)
    return 200, text.encode("utf-8"), None


class FakeLinkedIn:
    """Answers by URL; records each request and the clock at that moment."""

    def __init__(self) -> None:
        self.searches: dict[tuple[str, int], tuple] = {}
        self.postings: dict[str, tuple] = {}
        self.requests: list[str] = []
        self.times: list[float] = []
        self.waits: list[float] = []
        self.now = 1_000.0

    def fetch(self, url: str):
        self.requests.append(url)
        self.times.append(self.now)
        if "seeMoreJobPostings" in url:
            query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            return self._next(self.searches, (query["keywords"][0], int(query["start"][0])),
                              (200, b"", None))
        job_id = re.search(r"/jobs/view/(\d+)/$", url).group(1)
        return self._next(self.postings, job_id, None) or posting()

    @staticmethod
    def _next(answers: dict, key, default):
        """A list of answers is given out in order; its last one is repeated."""
        value = answers.get(key, default)
        if isinstance(value, list):
            return value.pop(0) if len(value) > 1 else value[0]
        return value

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.now += seconds

    def search_requests(self) -> list[str]:
        return [u for u in self.requests if "seeMoreJobPostings" in u]

    def posting_requests(self) -> list[str]:
        return [u for u in self.requests if "/jobs/view/" in u]


@pytest.fixture
def fake() -> FakeLinkedIn:
    return FakeLinkedIn()


def start_run(cli) -> dict:
    code, run, _ = cli("run", "start", "--days", "7")
    assert code == 0 and run["to_search"] == ["linkedin"], run
    return run


@pytest.fixture
def run(workspace, cli):
    """A run with LinkedIn (the repository's provider file) switched on."""
    needs = dict(PERSONA["job_needs"])
    needs["titles"] = PERSONA["target_titles"]
    path = workspace.home / "profile-input.json"
    path.write_text(json.dumps(needs), encoding="utf-8")
    assert cli("profile", "set", str(path))[0] == 0
    path.unlink()
    assert cli("providers", "enable", "linkedin")[0] == 0
    return start_run(cli)


def read(workspace, run, fake, title=TITLE, location="Peru"):
    return linkedin.read(workspace, run["run_id"], title, location, fetch=fake.fetch,
                         clock=fake.clock, sleep=fake.sleep)


def drafts_of(summary) -> list[dict]:
    return json.loads(Path(summary["drafts_path"]).read_text(encoding="utf-8"))


def run_provider(workspace, run_id) -> dict:
    with db.session(workspace) as conn:
        providers = search.summary(conn, run_id)["providers"]
    return next(p for p in providers if p["id"] == "linkedin")


# ── drafts ────────────────────────────────────────────────────────────────

def test_one_title_read_into_drafts(workspace, run, fake):
    fake.searches[(TITLE, 0)] = page(card(101), card(102, salary="S/ 12,000/month"),
                                     card(103, days_ago=10))
    fake.postings["102"] = posting(seniority="Not Applicable", employment="Temporary")
    summary = read(workspace, run, fake)
    assert {k: summary[k] for k in ("requests", "pages", "cards", "outside_window", "new",
                                    "already_seen", "duplicate_in_run", "stopped")} == {
        "requests": 3, "pages": 1, "cards": 3, "outside_window": 1, "new": 2,
        "already_seen": 0, "duplicate_in_run": 0, "stopped": None}
    first, second = drafts_of(summary)
    assert first["url"] == "https://www.linkedin.com/jobs/view/101/"
    assert (first["external_id"], first["title"], first["company"], first["location"],
            first["country"]) == ("101", TITLE, "Andes Datos Ficticios", "Lima, Peru", "PE")
    assert first["posted_at"] == (date.today() - timedelta(days=1)).isoformat()
    assert first["description"] == DESCRIPTION
    assert (first["seniority"], first["contract_type"]) == ("Mid-Senior level", "full-time")
    assert {k: first[k] for k in ("work_mode", "work_mode_detail", "language", "flags",
                                  "published_salary")} == {
        "work_mode": None, "work_mode_detail": None, "language": None, "flags": [],
        "published_salary": None}                              # left for the agent's reading
    assert (second["seniority"], second["contract_type"], second["employment_type"]) == (
        None, None, "Temporary")
    assert second["salary_shown"] == "S/ 12,000/month"
    folder = Path(run["capture_folder"])
    assert sorted(p.name for p in folder.glob("linkedin-*.html")) == [
        "linkedin-1.html", "linkedin-2.html", "linkedin-3.html"]


def test_only_the_parameters_linkedin_offers_visitors(workspace, run, fake):
    read(workspace, run, fake)
    read(workspace, run, fake, title="Data Engineer", location=None)
    with_location, without = (urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
                              for u in fake.search_requests())
    assert with_location == {"keywords": [TITLE], "location": ["Peru"], "f_TPR": ["r604800"],
                             "start": ["0"]}
    assert "location" not in without
    assert "%20" in fake.search_requests()[0]


@pytest.mark.parametrize("days,expected", [(1, "r86400"), (3, "r604800"), (7, "r604800"),
                                           (8, "r2592000"), (90, "r2592000")])
def test_posting_age_window(days, expected):
    assert linkedin.window(days) == expected


def test_paging_stops_at_three_pages(workspace, run, fake):
    for start in (0, 10, 20, 30):
        fake.searches[(TITLE, start)] = page(*(card(1000 + start + i) for i in range(10)))
    summary = read(workspace, run, fake)
    assert summary["pages"] == 3 and len(fake.search_requests()) == 3
    assert summary["new"] == 30 and len(fake.posting_requests()) == 30


def test_a_short_page_is_the_last(workspace, run, fake):
    fake.searches[(TITLE, 0)] = page(card(1), card(2))
    read(workspace, run, fake)
    assert len(fake.search_requests()) == 1


def test_no_results(workspace, run, fake):
    summary = read(workspace, run, fake)
    assert (summary["pages"], summary["cards"], summary["stopped"], summary["drafts_path"]) == (
        1, 0, None, None)


# ── pacing, duplicates, postings already stored ───────────────────────────

def test_pacing_holds_within_and_across_calls(workspace, run, fake):
    fake.searches[(TITLE, 0)] = page(card(1), card(2))
    fake.searches[("Data Engineer", 0)] = page(card(3))
    read(workspace, run, fake)
    read(workspace, run, fake, title="Data Engineer")
    gaps = [b - a for a, b in zip(fake.times, fake.times[1:], strict=False)]
    assert len(fake.times) == 5 and all(gap >= 5 for gap in gaps), gaps


def test_a_job_id_is_opened_once_per_run(workspace, run, fake):
    fake.searches[(TITLE, 0)] = page(card(201))
    fake.searches[("Data Engineer", 0)] = page(card(201), card(202))
    read(workspace, run, fake)
    summary = read(workspace, run, fake, title="Data Engineer")
    assert (summary["duplicate_in_run"], summary["new"]) == (1, 1)
    assert [u.rsplit("/", 2)[-2] for u in fake.posting_requests()] == ["201", "202"]


def test_a_posting_stored_by_an_earlier_run_is_not_opened_again(workspace, run, fake, cli,
                                                                 tmp_path):
    fake.searches[(TITLE, 0)] = page(card(301))
    summary = read(workspace, run, fake)
    readings = tmp_path / "readings.json"
    readings.write_text(json.dumps([{"external_id": "301", "work_mode": "hybrid",
                                     "language": "es"}]), encoding="utf-8")
    assert cli("postings", "import", str(run["run_id"]), summary["drafts_path"],
               "--readings", str(readings))[0] == 0
    cli("run", "finish", str(run["run_id"]))

    later = start_run(cli)
    fake.searches[(TITLE, 0)] = page(card(301), card(302))
    summary = read(workspace, later, fake)
    assert (summary["already_seen"], summary["new"]) == (1, 1)
    assert [u.rsplit("/", 2)[-2] for u in fake.posting_requests()] == ["301", "302"]
    with db.session(workspace) as conn:
        outcomes = {r["external_id"]: r["outcome"] for r in conn.execute(
            "SELECT p.external_id, r.outcome FROM run_results r JOIN postings p"
            " ON p.id = r.posting_id WHERE r.run_id = ?", (later["run_id"],))}
    assert outcomes == {"301": "seen"}                   # 302 waits for the agent's reading


# ── stop conditions ───────────────────────────────────────────────────────

def test_a_redirect_blocks_linkedin_for_the_run(workspace, run, fake):
    fake.searches[(TITLE, 0)] = (302, b"", "https://www.linkedin.com/authwall?trk=x")
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "blocked" and "authwall" in summary["stopped"][
        "detail"]
    assert len(fake.requests) == 1                                  # a hard block: no retry
    provider = run_provider(workspace, run["run_id"])
    assert (provider["status"], provider["reason"]) == ("failed", "blocked")
    before = len(fake.requests)
    with pytest.raises(JobTrackerError) as refused:
        read(workspace, run, fake, title="Data Engineer")
    assert refused.value.code == "provider_stopped" and len(fake.requests) == before


def test_sign_in_page_instead_of_results_is_a_block(workspace, run, fake):
    fake.searches[(TITLE, 0)] = (200, (FIXTURES / "signin.html").read_bytes(), None)
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "blocked"


# ── soft blocks: retries and cool-downs (provider-throttling) ────────────

THROTTLED = (429, b"", None)


def test_a_throttle_that_clears_is_waited_out(workspace, run, fake):
    fake.searches[(TITLE, 0)] = [THROTTLED, page(card(801))]
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None and summary["new"] == 1
    gap = fake.times[1] - fake.times[0]
    assert 10 <= gap <= 20                               # backoff with jitter, first retry
    assert "cooldown_until" not in run_provider(workspace, run["run_id"])


def test_retry_after_is_honoured(workspace, run, fake):
    fake.searches[(TITLE, 0)] = [(429, b"", None, "40"), page(card(802))]
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None
    assert fake.times[1] - fake.times[0] == pytest.approx(40)


@pytest.mark.parametrize("status", [429, 999])
def test_a_throttle_that_stays_is_a_cool_down_not_a_stop(workspace, run, fake, status):
    fake.searches[(TITLE, 0)] = (status, b"", None)
    summary = read(workspace, run, fake)
    stop = summary["stopped"]
    assert stop["reason"] == "throttled" and str(status) in stop["detail"]
    assert stop["minutes"] == 15 and stop["resume_after"]
    assert len(fake.requests) == 3                                  # three attempts
    provider = run_provider(workspace, run["run_id"])
    assert provider["status"] == "pending" and provider["cooldown_until"] == stop["resume_after"]
    before = len(fake.requests)
    with pytest.raises(JobTrackerError) as refused:
        read(workspace, run, fake, title="Data Engineer")
    assert refused.value.code == "provider_cooling" and len(fake.requests) == before


def test_a_long_retry_after_cools_down_at_once(workspace, run, fake):
    fake.searches[(TITLE, 0)] = (429, b"", None, "3600")
    summary = read(workspace, run, fake)
    assert len(fake.requests) == 1                     # no retry inside the call
    assert summary["stopped"]["minutes"] == 60         # the site asked for an hour


def test_the_same_run_resumes_after_the_cool_down(workspace, run, fake):
    fake.searches[(TITLE, 0)] = page(*[card(900 + n) for n in range(10)])
    fake.searches[(TITLE, 10)] = page(card(910), card(911))
    fake.postings["911"] = [THROTTLED, THROTTLED, THROTTLED, posting()]
    first = read(workspace, run, fake)
    assert first["stopped"]["reason"] == "throttled"
    assert len(drafts_of(first)) == 11
    fake.now += 15 * 60
    opened = list(fake.posting_requests())
    second = read(workspace, run, fake)
    assert second["stopped"] is None and [d["external_id"] for d in drafts_of(second)] == [
        "911"]
    searched = [u for u in fake.search_requests()]
    assert "start=0" not in searched[-1] and searched.count(searched[-1]) == 2  # page 2 again
    reopened = fake.posting_requests()[len(opened):]
    assert [u.rsplit("/", 2)[-2] for u in reopened] == ["911"]   # nothing else reopened
    third = read(workspace, run, fake)
    assert third["already_done"] is True and third["requests"] == 0


def test_a_third_throttle_stops_the_provider(workspace, run, fake):
    fake.searches[(TITLE, 0)] = (429, b"", None, "1")
    for _ in range(2):
        assert read(workspace, run, fake)["stopped"]["reason"] == "throttled"
        fake.now += 31 * 60
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "blocked"
    assert "after 2 cool-downs" in summary["stopped"]["detail"]
    provider = run_provider(workspace, run["run_id"])
    assert (provider["status"], provider["reason"]) == ("failed", "blocked")
    with pytest.raises(JobTrackerError) as refused:
        read(workspace, run, fake)
    assert refused.value.code == "provider_stopped"


def test_the_run_retry_budget(workspace, run, fake):
    cards = [card(950 + n) for n in range(4)]
    fake.searches[(TITLE, 0)] = page(*cards)
    for n in range(4):
        fake.postings[str(950 + n)] = [THROTTLED, THROTTLED, posting()]  # two retries each
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "throttled"           # the 7th retry is refused
    assert len(drafts_of(summary)) == 3


def test_finishing_a_run_during_a_cool_down(workspace, run, fake, cli):
    fake.now = time.time()
    fake.searches[(TITLE, 0)] = THROTTLED
    read(workspace, run, fake)
    code, out, _ = cli("run", "finish", str(run["run_id"]))
    provider = next(p for p in out["run"]["providers"] if p["id"] == "linkedin")
    assert (provider["status"], provider["reason"]) == ("failed", "throttled")
    assert "cooling down until" in provider["detail"]


def test_a_new_run_inherits_a_cool_down(workspace, run, fake, cli):
    fake.now = time.time()
    fake.searches[(TITLE, 0)] = THROTTLED
    until = read(workspace, run, fake)["stopped"]["resume_after"]
    cli("run", "finish", str(run["run_id"]))
    later = start_run(cli)
    with pytest.raises(JobTrackerError) as refused:
        read(workspace, later, fake)
    assert refused.value.code == "provider_cooling"
    assert run_provider(workspace, later["run_id"])["cooldown_until"] == until


def test_a_hard_block_keeps_what_was_read(workspace, run, fake):
    fake.searches[(TITLE, 0)] = page(card(401), card(402), card(403))
    fake.postings["402"] = (302, b"", "https://www.linkedin.com/login")
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "blocked"
    assert [d["external_id"] for d in drafts_of(summary)] == ["401"]
    assert len(fake.posting_requests()) == 2                       # 403 never requested


NO_DESCRIPTION = (200, b"<html><body><p>Nothing here</p></body></html>", None)
CHANGED_SEARCH = (200, b'<div data-entity-urn="urn:li:jobPosting:7">x</div>', None)


def test_one_posting_without_a_description_is_unreadable(workspace, run, fake):
    fake.searches[(TITLE, 0)] = page(card(501), card(502))
    fake.postings["501"] = NO_DESCRIPTION
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None and summary["title_problem"] is None
    assert [u["external_id"] for u in summary["unreadable"]] == ["501"]
    assert [d["external_id"] for d in drafts_of(summary)] == ["502"]


def test_two_postings_without_a_description_end_only_the_title(workspace, run, fake):
    fake.searches[(TITLE, 0)] = page(card(501), card(502), card(503))
    fake.postings["501"] = NO_DESCRIPTION
    fake.postings["502"] = NO_DESCRIPTION
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None
    assert summary["title_problem"]["kind"] == "no_description"
    assert not any("/503/" in url for url in fake.requests)
    assert run_provider(workspace, run["run_id"])["status"] == "pending"
    fake.searches[("Data Engineer", 0)] = page(card(504))
    assert read(workspace, run, fake, title="Data Engineer")["new"] == 1


def test_a_changed_search_page_is_retried_once(workspace, run, fake):
    fake.searches[(TITLE, 0)] = [CHANGED_SEARCH, page(card(7))]
    summary = read(workspace, run, fake)
    assert summary["title_retries"] == 1 and summary["title_problem"] is None
    assert summary["new"] == 1


def test_a_changed_search_page_ends_only_the_title(workspace, run, fake):
    fake.searches[(TITLE, 0)] = CHANGED_SEARCH
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None and summary["title_retries"] == 1
    assert summary["title_problem"]["kind"] == "cards_without_data"
    assert summary["site_may_have_changed"] is False
    assert run_provider(workspace, run["run_id"])["status"] == "pending"


def test_every_title_is_tried_and_a_change_is_reported(workspace, run, fake):
    titles = ["Senior Data Engineer", "Data Engineer", "Analytics Engineer"]
    for title in titles:
        fake.searches[(title, 0)] = CHANGED_SEARCH
    summaries = [read(workspace, run, fake, title=t) for t in titles]
    assert [s["stopped"] for s in summaries] == [None, None, None]
    assert [s["site_may_have_changed"] for s in summaries] == [False, True, True]


def test_titles_with_no_results_are_not_problems(workspace, run, fake):
    titles = ["Senior Data Engineer", "Data Engineer", "Analytics Engineer"]
    summaries = [read(workspace, run, fake, title=t) for t in titles]   # empty pages
    assert all(s["title_problem"] is None and s["title_retries"] == 0 for s in summaries)
    assert len(fake.requests) == 3
    fake.searches[("Data Scientist", 0)] = CHANGED_SEARCH
    later = read(workspace, run, fake, title="Data Scientist")
    assert later["title_problem"] and later["site_may_have_changed"] is False


def test_a_removed_posting_is_listed_not_imported(workspace, run, fake):
    fake.searches[(TITLE, 0)] = page(card(601), card(602))
    fake.postings["601"] = (404, b"", None)
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None
    assert summary["unreadable"] == [{"external_id": "601", "url":
                                      "https://www.linkedin.com/jobs/view/601/",
                                      "reason": "HTTP 404"}]
    assert [d["external_id"] for d in drafts_of(summary)] == ["602"]


def test_a_network_error_stops_with_an_error(workspace, run, fake):
    def broken(url):
        raise OSError("connection reset")

    summary = linkedin.read(workspace, run["run_id"], TITLE, None, fetch=broken,
                            clock=fake.clock, sleep=fake.sleep)
    assert summary["stopped"]["reason"] == "error"


def test_a_site_without_a_reader_is_refused(workspace, run, cli):
    code, out, _ = cli("providers", "read", "nosuchsite", str(run["run_id"]), "--title", TITLE)
    assert code == 1 and out["error"]["code"] == "no_reader"


# ── import with readings ──────────────────────────────────────────────────

@pytest.fixture
def drafts(workspace, run, fake) -> str:
    fake.searches[(TITLE, 0)] = page(card(701), card(702))
    return read(workspace, run, fake)["drafts_path"]


def import_with(cli, run, drafts, readings, tmp_path):
    path = tmp_path / "readings.json"
    path.write_text(json.dumps(readings, ensure_ascii=False), encoding="utf-8")
    return cli("postings", "import", str(run["run_id"]), drafts, "--readings", str(path))


def stored(workspace) -> dict:
    with db.session(workspace) as conn:
        return {r["external_id"]: r for r in conn.execute(
            "SELECT * FROM postings WHERE provider = 'linkedin'")}


def test_readings_are_merged_into_the_drafts(workspace, run, drafts, cli, tmp_path):
    code, report, _ = import_with(cli, run, drafts, [
        {"external_id": "701", "work_mode": "hybrid",
         "work_mode_detail": "Híbrido: 2 días por semana en la oficina", "language": "es"},
        {"external_id": "702", "work_mode": None, "language": "es",
         "flags": ["Work mode not stated", "Employment type: Temporary"]},
    ], tmp_path)
    assert code == 0, report
    assert report["new"] == 2
    rows = stored(workspace)
    assert rows["701"]["description"] == DESCRIPTION                 # never retyped
    assert (rows["701"]["work_mode"], rows["701"]["work_mode_detail"], rows["701"]["language"]
            ) == ("hybrid", "Híbrido: 2 días por semana en la oficina", "es")
    assert rows["702"]["work_mode"] is None
    # the work-mode chip already says it is not stated: that flag is not stored
    assert json.loads(rows["702"]["flags"]) == ["Employment type: Temporary"]


def test_every_draft_needs_a_reading(workspace, run, drafts, cli, tmp_path):
    code, out, _ = import_with(cli, run, drafts, [
        {"external_id": "701", "work_mode": "remote", "language": "es"}], tmp_path)
    assert code == 1 and out["error"]["code"] == "invalid_posting"
    assert "702" in out["error"]["message"]
    assert stored(workspace) == {}


def test_a_reading_for_another_posting_is_refused(workspace, run, drafts, cli, tmp_path):
    code, out, _ = import_with(cli, run, drafts, [
        {"external_id": i, "work_mode": "remote", "language": "es"}
        for i in ("701", "702", "999")], tmp_path)
    assert code == 1 and "999" in out["error"]["message"]
    assert stored(workspace) == {}


@pytest.mark.parametrize("field", ["description", "title", "posted_at"])
def test_a_reading_cannot_change_captured_text(workspace, run, drafts, cli, tmp_path, field):
    code, out, _ = import_with(cli, run, drafts, [
        {"external_id": "701", "language": "es", field: "changed"},
        {"external_id": "702", "language": "es"}], tmp_path)
    assert code == 1 and out["error"]["details"]["field"] == field
    assert stored(workspace) == {}


# ── one call at a time ────────────────────────────────────────────────────

def test_a_second_call_while_one_runs_is_refused(workspace, run, fake):
    fake.searches[(TITLE, 0)] = page(card(801))
    outcome: dict = {}

    def fetch(url):
        if not outcome:  # another call starts while this one is waiting on LinkedIn
            try:
                read(workspace, run, fake, title="Data Engineer")
            except JobTrackerError as error:
                outcome["code"] = error.code
        return fake.fetch(url)

    linkedin.read(workspace, run["run_id"], TITLE, None, fetch=fetch, clock=fake.clock,
                  sleep=fake.sleep)
    assert outcome == {"code": "reader_busy"}
    assert len(fake.search_requests()) == 1               # the second call sent nothing
    read(workspace, run, fake, title="Data Engineer")     # free again once the first ended
    assert len(fake.search_requests()) == 2


def test_a_stale_lock_does_not_block_forever(workspace, run, fake):
    lock = Path(run["capture_folder"]) / linkedin.LOCK_FILE
    lock.write_text(str(fake.now - linkedin.STALE_LOCK_SECONDS - 1), encoding="utf-8")
    assert read(workspace, run, fake)["stopped"] is None
    assert not lock.exists()
    lock.write_text(str(fake.now - 60), encoding="utf-8")   # a call a minute ago: still running
    with pytest.raises(JobTrackerError) as busy:
        read(workspace, run, fake)
    assert busy.value.code == "reader_busy"
