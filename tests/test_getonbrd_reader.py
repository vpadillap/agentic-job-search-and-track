"""provider-getonbrd: the Get on Board reader against a fake HTTP getter and fictional
API answers. No test reaches Get on Board."""
from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from jobtracker.core.errors import JobTrackerError
from jobtracker.core.readers import getonbrd

PERSONA = json.loads((Path(__file__).parent / "fixtures" / "persona.json").read_text(
    encoding="utf-8"))
TITLE = "Senior Data Engineer"


def job(slug: str, title: str = "Data Engineer", days_ago: int = 1, remote: str = "hybrid",
        countries=("Peru",), salary=(3000, 4000), company: str = "Andes Datos Ficticios") -> dict:
    published = int((datetime.now() - timedelta(days=days_ago)).timestamp())
    return {"id": slug, "type": "job", "links": {"public_url":
                                                  f"https://www.getonbrd.com/jobs/{slug}"},
            "attributes": {
                "title": title, "description_headline": "Requisitos",
                "description": "<ul><li>Python y SQL</li><li>3 años</li></ul>",
                "projects": "<p>Proyecto <b>ficticio</b> de datos.</p>",
                "functions_headline": "Funciones", "functions": "<p>Construir pipelines.</p>",
                "desirable_headline": None, "desirable": "",
                "benefits_headline": "Beneficios", "benefits": "<p>Horario flexible.</p>",
                "remote": remote != "no_remote", "remote_modality": remote,
                "countries": list(countries), "min_salary": salary[0] if salary else None,
                "max_salary": salary[1] if salary else None, "published_at": published,
                "perks": ["flexible_hours"], "category_name": "Data Science / Analytics",
                "company": {"data": {"id": "andes", "type": "company",
                                     "attributes": {"name": company}}},
                "seniority": {"data": {"id": "4", "type": "seniority",
                                       "attributes": {"name": "Senior"}}},
                "modality": {"data": {"id": "1", "type": "modality",
                                      "attributes": {"name": "Full time"}}}}}


class FakeGet:
    """Answers by search kind (country / remote) and page; records requests and clock."""

    def __init__(self) -> None:
        self.country: list[list[dict]] = [[]]
        self.remote: list[list[dict]] = [[]]
        self.overrides: list[tuple[int, str]] = []
        self.urls: list[str] = []
        self.times: list[float] = []
        self.now = 1_000.0

    def __call__(self, url: str) -> tuple[int, str]:
        self.urls.append(url)
        self.times.append(self.now)
        if self.overrides:
            return self.overrides.pop(0)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        pages = self.remote if "remote" in query else self.country
        page = int(query["page"][0])
        data = pages[page - 1] if page <= len(pages) else []
        return 200, json.dumps({"data": data, "meta": {"page": page, "per_page": 120,
                                                       "total_pages": len(pages)}})

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def queries(self) -> list[dict]:
        return [{k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
                 .items()} for u in self.urls]


@pytest.fixture
def fake() -> FakeGet:
    return FakeGet()


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
    assert cli("providers", "enable", "getonbrd")[0] == 0
    code, run, _ = cli("run", "start", "--days", "7")
    assert code == 0 and run["to_search"] == ["getonbrd"], run
    return run


def read(workspace, run, fake, title=TITLE):
    return getonbrd.read(workspace, run["run_id"], title, get=fake, clock=fake.clock,
                         sleep=fake.sleep)


def drafts_of(summary) -> list[dict]:
    return json.loads(Path(summary["drafts_path"]).read_text(encoding="utf-8"))


def test_two_searches_country_and_remote_from_anywhere(workspace, run, fake):
    fake.country = [[job("a1"), job("a2", title="Senior .NET Engineer"),
                     job("a3", days_ago=20), job("a4", remote="remote_local",
                                                 countries=["Remote"])]]
    fake.remote = [[job("r1", remote="fully_remote", countries=["Remote"]), job("a4")]]
    summary = read(workspace, run, fake)
    first, second = fake.queries()
    assert (first["country_code"], first["query"], first["per_page"]) == ("pe", TITLE, "120")
    assert first["expand"] == '["company","seniority","modality"]'
    assert second["remote"] == "true" and "country_code" not in second
    assert {k: summary[k] for k in ("other_title", "outside_window", "duplicate_in_run",
                                    "new", "stopped")} == {
        "other_title": 1, "outside_window": 1, "duplicate_in_run": 1, "new": 3,
        "stopped": None}
    assert summary["searches"] == [{"search": "country", "new": 2},
                                   {"search": "remote", "new": 1}]
    assert [d["external_id"] for d in drafts_of(summary)] == ["a1", "a4", "r1"]


def test_a_draft(workspace, run, fake):
    fake.country = [[job("b1")]]
    draft = drafts_of(read(workspace, run, fake))[0]
    assert (draft["url"], draft["title"], draft["company"], draft["location"],
            draft["country"]) == ("https://www.getonbrd.com/jobs/b1", "Data Engineer",
                                  "Andes Datos Ficticios", "Peru", "PE")
    assert draft["posted_at"] == (datetime.now() - timedelta(days=1)).date().isoformat()
    assert draft["description"] == (
        "Requisitos\n- Python y SQL\n\n- 3 años\n\nProyecto ficticio de datos.\n\n"
        "Funciones\nConstruir pipelines.\n\nBeneficios\nHorario flexible.")
    assert draft["site_salary"]["min"] == 3000 and draft["site_salary"]["currency"] is None
    assert (draft["site_remote"], draft["site_seniority"], draft["site_modality"]) == (
        "hybrid", "Senior", "Full time")
    assert draft["published_salary"] is None and draft["work_mode"] is None


def test_readings_import_the_drafts(workspace, run, fake, cli, tmp_path):
    fake.country = [[job("c1")]]
    summary = read(workspace, run, fake)
    readings = tmp_path / "r.json"
    readings.write_text(json.dumps([{"external_id": "c1", "language": "es",
                                     "work_mode": "hybrid"}]), encoding="utf-8")
    code, report, _ = cli("postings", "import", str(run["run_id"]), summary["drafts_path"],
                          "--readings", str(readings))
    assert code == 0 and report["new"] == 1, report


def test_paging(workspace, run, fake):
    fake.country = [[job(f"p{i}") for i in range(3)], [job(f"q{i}") for i in range(3)]]
    summary = read(workspace, run, fake)
    assert summary["new"] == 6 and [q["page"] for q in fake.queries()] == ["1", "2", "1"]


def test_the_cap(workspace, run, fake, monkeypatch):
    fake.country = [[job(f"p{i}") for i in range(5)]]
    original = getonbrd.common.context

    def capped(*args, **kwargs):
        ctx = original(*args, **kwargs)
        ctx.max_results = 2
        return ctx

    monkeypatch.setattr(getonbrd.common, "context", capped)
    summary = read(workspace, run, fake)
    assert summary["capped"] is True and summary["new"] == 2
    assert len(fake.urls) == 1                     # the remote search is not run


def test_a_stored_posting_is_seen(workspace, run, fake, cli, tmp_path):
    fake.country = [[job("d1")]]
    summary = read(workspace, run, fake)
    readings = tmp_path / "r.json"
    readings.write_text(json.dumps([{"external_id": "d1"}]), encoding="utf-8")
    cli("postings", "import", str(run["run_id"]), summary["drafts_path"], "--readings",
        str(readings))
    cli("run", "finish", str(run["run_id"]))
    _, second, _ = cli("run", "start", "--days", "7")
    later = read(workspace, second, fake)
    assert later["already_seen"] == 1 and later["new"] == 0


def test_without_a_country_only_remote_from_anywhere(workspace, cli, fake):
    set_profile(workspace, cli, country=None)
    cli("providers", "enable", "getonbrd")
    _, run, _ = cli("run", "start", "--days", "7")
    fake.remote = [[job("e1", remote="fully_remote", countries=["Remote"])]]
    summary = read(workspace, run, fake)
    assert len(fake.urls) == 1 and fake.queries()[0]["remote"] == "true"
    assert summary["new"] == 1 and "no country" in summary["note"]


def test_pacing(workspace, run, fake):
    fake.country = [[job("f1")]]
    read(workspace, run, fake)
    read(workspace, run, fake, title="Data Platform Engineer")
    gaps = [b - a for a, b in zip(fake.times, fake.times[1:], strict=False)]
    assert len(fake.times) == 4 and all(gap >= 5 for gap in gaps), gaps


def test_refused_requests_stop_get_on_board(workspace, run, fake):
    fake.overrides = [(403, "refused")]
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "blocked"
    with pytest.raises(JobTrackerError) as error:
        read(workspace, run, fake, title="Data Platform Engineer")
    assert error.value.code == "provider_stopped"


def test_a_throttle_that_clears_goes_on(workspace, run, fake):
    fake.overrides = [(429, "slow down")]
    fake.country = [[job("g9")]]
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None and summary["new"] == 1
    assert 10 <= fake.times[1] - fake.times[0] <= 20     # backoff with jitter


def test_a_completed_title_is_not_searched_again(workspace, run, fake):
    read(workspace, run, fake)
    before = len(fake.urls)
    again = read(workspace, run, fake)
    assert again["already_done"] is True and len(fake.urls) == before


MAINTENANCE = (200, "<html>maintenance</html>")


def test_an_unreadable_answer_is_retried_once(workspace, run, fake):
    fake.overrides = [MAINTENANCE]
    fake.country = [[job("g0")]]
    summary = read(workspace, run, fake)
    assert summary["title_retries"] == 1 and summary["title_problem"] is None
    assert summary["new"] == 1


def test_an_unreadable_answer_ends_that_search_only(workspace, run, fake):
    fake.overrides = [MAINTENANCE, MAINTENANCE]
    fake.remote = [[job("g1", remote="fully_remote", countries=["Remote"])]]
    summary = read(workspace, run, fake)            # the country search fails, remote works
    assert summary["stopped"] is None and summary["new"] == 1
    assert summary["title_problem"] is None


def test_three_unreadable_answers_end_only_the_title(workspace, run, fake, monkeypatch):
    monkeypatch.setattr(getonbrd, "FAILURES_IN_A_ROW", 2)   # two searches per title
    fake.overrides = [MAINTENANCE] * 4
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None
    assert summary["title_problem"]["kind"] == "unreadable_answers"
    second = read(workspace, run, fake, title="Analytics Engineer")
    assert second["stopped"] is None and second["title_problem"] is None


def test_no_answer_stops(workspace, run, fake, monkeypatch):
    monkeypatch.setattr(getonbrd, "FAILURES_IN_A_ROW", 2)

    def down(url: str):
        raise OSError("connection refused")

    summary = getonbrd.read(workspace, run["run_id"], TITLE, get=down, clock=fake.clock,
                            sleep=fake.sleep)
    assert summary["stopped"]["reason"] == "error" and "no answer" in summary["stopped"]["detail"]


def test_no_results(workspace, run, fake):
    summary = read(workspace, run, fake)
    assert (summary["new"], summary["stopped"]) == (0, None)


def test_provider_file():
    from jobtracker.core import providers

    item = {p["id"]: p for p in providers.list_providers()}["getonbrd"]
    assert item["valid"], item["problems"]
    assert (item["coverage"], item["access"], item["dependencies"], item["requires_login"],
            item["max_results_per_query"]) == ("global", "http", [], False, 60)
    text = (Path(__file__).resolve().parents[1] / "providers" / "getonbrd.md").read_text(
        encoding="utf-8")
    for required in ("jt providers read getonbrd <run_id> --title", "--readings",
                     "remote=true", "Section 7.1", "24 hours", "salary currency not stated"):
        assert required in text, required
