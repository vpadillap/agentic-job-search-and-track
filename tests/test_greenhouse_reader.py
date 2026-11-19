"""provider-greenhouse: the Greenhouse reader against a fake HTTP getter and fictional
boards. No test reaches Greenhouse."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from jobtracker.core import db
from jobtracker.core.errors import JobTrackerError
from jobtracker.core.readers import greenhouse

PERSONA = json.loads((Path(__file__).parent / "fixtures" / "persona.json").read_text(
    encoding="utf-8"))
TITLE = "Senior Data Engineer"
API = "https://boards-api.greenhouse.io/v1/boards"
CONTENT = ("&lt;p&gt;Somos una empresa &lt;b&gt;ficticia&lt;/b&gt;.&lt;/p&gt;&lt;ul&gt;"
           "&lt;li&gt;Python y SQL&lt;/li&gt;&lt;li&gt;Modalidad híbrida&lt;/li&gt;&lt;/ul&gt;")


def job(job_id: int, title: str = "Data Engineer", where: str = "Lima, Peru",
        days_ago: int = 1, company: str = "Andes Datos Ficticios", **extra) -> dict:
    published = (date.today() - timedelta(days=days_ago)).isoformat()
    return {"id": job_id, "title": title, "location": {"name": where},
            "offices": [{"name": "Peru"}] if "Peru" in where else [],
            "first_published": f"{published}T10:00:00-05:00",
            "updated_at": f"{published}T10:00:00-05:00", "company_name": company,
            "absolute_url": f"https://job-boards.greenhouse.io/andes/jobs/{job_id}",
            "language": "es", "content": CONTENT, "departments": [{"name": "Data"}], **extra}


QUESTIONS = [
    {"label": "Resume/CV", "required": True, "fields": [{"type": "input_file"}]},
    {"label": "¿Por qué quieres trabajar con nosotros?", "required": False,
     "fields": [{"type": "textarea"}]},
    {"label": "Nivel de inglés", "required": True, "fields": [{
        "type": "multi_value_single_select",
        "values": [{"label": "Básico", "value": 1}, {"label": "Avanzado", "value": 2}]}]},
]


class FakeGet:
    """Boards and postings by board name; records requests and the clock."""

    def __init__(self) -> None:
        self.boards: dict[str, list[dict]] = {}
        self.overrides: dict[str, tuple[int, str]] = {}
        self.urls: list[str] = []
        self.times: list[float] = []
        self.now = 1_000.0

    def __call__(self, url: str) -> tuple[int, str]:
        self.urls.append(url)
        self.times.append(self.now)
        if url in self.overrides:
            return self.overrides[url]
        path = url[len(API) + 1:].split("?")[0].split("/")
        board = path[0]
        if board not in self.boards:
            return 404, '{"status":404,"error":"Job not found"}'
        if len(path) == 2:
            return 200, json.dumps({"jobs": self.boards[board], "meta": {"total": 1}})
        found = next((j for j in self.boards[board] if str(j["id"]) == path[2]), None)
        if found is None:
            return 404, '{"status":404,"error":"Job not found"}'
        return 200, json.dumps({**found, "questions": QUESTIONS, "location_questions": []})

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def details_read(self) -> list[str]:
        return [u.split("/jobs/")[1].split("?")[0] for u in self.urls if "questions=true" in u]


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
    assert cli("providers", "enable", "greenhouse")[0] == 0
    code, run, _ = cli("run", "start", "--days", "7")
    assert code == 0 and run["to_search"] == ["greenhouse"], run
    return run


def found(tmp_path, *links: str, name: str = "found.json") -> str:
    path = tmp_path / name
    path.write_text(json.dumps(list(links)), encoding="utf-8")
    return str(path)


def read(workspace, run, fake, title=TITLE, **kwargs):
    return greenhouse.read(workspace, run["run_id"], title, get=fake, clock=fake.clock,
                           sleep=fake.sleep, **kwargs)


def drafts_of(summary) -> list[dict]:
    return json.loads(Path(summary["drafts_path"]).read_text(encoding="utf-8"))


# ── pure parts ────────────────────────────────────────────────────────────

def test_links_give_postings_and_boards():
    postings, boards, ignored = greenhouse.parse_links([
        "https://job-boards.greenhouse.io/encora10/jobs/5283692007",
        "https://boards.greenhouse.io/Topsort/jobs/4816054008?gh_src=x",
        "https://job-boards.eu.greenhouse.io/saasgroup",
        "https://job-boards.greenhouse.io/encora10/jobs/5283692007",
        "https://stripe.com/jobs/search?gh_jid=8172510", 42])
    assert postings == [("encora10", "5283692007"), ("topsort", "4816054008")]
    assert boards == ["saasgroup"]
    assert ignored == ["https://stripe.com/jobs/search?gh_jid=8172510", "42"]


@pytest.mark.parametrize("posting,expected", [
    ("Data Engineer II", True), ("Lead Data Engineer, AWS", True),
    ("Ingeniero de datos", False), ("Data Analyst", False), ("Senior Data-Engineer", True)])
def test_title_match_ignores_seniority(posting, expected):
    assert greenhouse.title_matches(TITLE, posting) is expected


@pytest.mark.parametrize("texts,expected", [
    (["Lima, Peru"], True), (["Perú"], True), (["Remote - LATAM"], True),
    (["Remote, Latin America"], True), (["Buenos Aires, Argentina"], False),
    (["LATAM Hub, Bogotá"], False), (["Remote"], False), (["Limassol, Cyprus"], False)])
def test_location_match(texts, expected):
    places = ["Peru", "Perú", "Lima"]
    regions = ["LATAM", "Latin America"]
    assert greenhouse.location_matches(texts, places, regions) is expected


# ── reading ───────────────────────────────────────────────────────────────

def test_a_board_is_filtered_to_title_country_and_window(workspace, run, fake, tmp_path):
    fake.boards["andes"] = [job(1), job(2, title="Data Analyst"),
                            job(3, where="Santiago, Chile"), job(4, days_ago=20),
                            job(5, title="Lead Data Engineer", where="Remote - LATAM")]
    summary = read(workspace, run, fake,
                   found=found(tmp_path, "https://job-boards.greenhouse.io/andes"))
    assert {k: summary[k] for k in ("boards", "other_title", "other_country",
                                    "outside_window", "new", "stopped")} == {
        "boards": 1, "other_title": 1, "other_country": 1, "outside_window": 1, "new": 2,
        "stopped": None}
    assert fake.details_read() == ["1", "5"]
    first = drafts_of(summary)[0]
    assert (first["external_id"], first["title"], first["company"], first["location"],
            first["country"]) == ("1", "Data Engineer", "Andes Datos Ficticios", "Lima, Peru",
                                  "PE")
    assert first["url"] == "https://job-boards.greenhouse.io/andes/jobs/1"
    assert first["posted_at"] == (date.today() - timedelta(days=1)).isoformat()
    assert first["description"] == ("Somos una empresa ficticia.\n\n- Python y SQL\n\n"
                                    "- Modalidad híbrida")
    assert first["form_questions"] == [
        {"text": "Resume/CV", "kind": "file", "options": None, "required": True},
        {"text": "¿Por qué quieres trabajar con nosotros?", "kind": "long_text",
         "options": None, "required": False},
        {"text": "Nivel de inglés", "kind": "choice", "options": ["Básico", "Avanzado"],
         "required": True}]
    assert first["site_language"] == "es" and first["work_mode"] is None


def test_readings_import_the_drafts_with_their_questions(workspace, run, fake, cli, tmp_path):
    fake.boards["andes"] = [job(11)]
    summary = read(workspace, run, fake,
                   found=found(tmp_path, "https://job-boards.greenhouse.io/andes"))
    readings = tmp_path / "r.json"
    readings.write_text(json.dumps([{"external_id": "11", "language": "es",
                                     "work_mode": "hybrid"}]), encoding="utf-8")
    code, report, _ = cli("postings", "import", str(run["run_id"]), summary["drafts_path"],
                          "--readings", str(readings))
    assert code == 0 and report["new"] == 1, report
    with db.session(workspace) as conn:
        assert conn.execute("SELECT COUNT(*) FROM form_questions").fetchone()[0] == 3


def test_postings_from_the_signed_in_search_skip_the_title_filter(workspace, run, fake,
                                                                  tmp_path):
    fake.boards["encora10"] = [job(21, title="Ingeniero de Datos AWS"),
                               job(22, title="Ingeniero de Datos", where="Bogotá, Colombia")]
    summary = read(workspace, run, fake, found=found(
        tmp_path, "https://job-boards.greenhouse.io/encora10/jobs/21",
        "https://job-boards.greenhouse.io/encora10/jobs/22"))
    assert summary["new"] == 1 and summary["other_country"] == 1
    assert [d["external_id"] for d in drafts_of(summary)] == ["21"]
    # The board is remembered and read again (title-filtered) for the next title.
    saved = json.loads(greenhouse.settings_path(workspace).read_text(encoding="utf-8"))
    assert saved["boards"]["encora10"]["found_via"] == "search"


def test_boards_are_remembered_and_rechecked(workspace, run, fake, cli, tmp_path):
    fake.boards["andes"] = [job(31)]
    first = read(workspace, run, fake,
                 found=found(tmp_path, "https://job-boards.greenhouse.io/andes"))
    readings = tmp_path / "r.json"
    readings.write_text(json.dumps([{"external_id": "31"}]), encoding="utf-8")
    cli("postings", "import", str(run["run_id"]), first["drafts_path"], "--readings",
        str(readings))
    cli("run", "finish", str(run["run_id"]))
    fake.boards["andes"].append(job(32))
    _, second, _ = cli("run", "start", "--days", "7")
    summary = read(workspace, second, fake)                  # nothing found this time
    assert summary["boards"] == 1 and summary["new"] == 1 and summary["already_seen"] == 1
    assert fake.details_read()[-1] == "32"
    saved = json.loads(greenhouse.settings_path(workspace).read_text(encoding="utf-8"))
    assert saved["boards"]["andes"]["titles"] == [TITLE]


def test_a_board_that_is_gone_is_forgotten(workspace, run, fake, cli, tmp_path):
    fake.boards["andes"] = [job(41)]
    read(workspace, run, fake, found=found(tmp_path, "https://job-boards.greenhouse.io/andes"))
    cli("run", "finish", str(run["run_id"]))
    del fake.boards["andes"]
    _, second, _ = cli("run", "start", "--days", "7")
    summary = read(workspace, second, fake)
    assert summary["boards_gone"] == ["andes"] and summary["stopped"] is None
    saved = json.loads(greenhouse.settings_path(workspace).read_text(encoding="utf-8"))
    assert saved["boards"] == {}


def test_boards_without_postings_in_the_country_are_not_remembered(workspace, run, fake,
                                                                   tmp_path):
    fake.boards["faraway"] = [job(51, where="Berlin, Germany")]
    read(workspace, run, fake, found=found(tmp_path, "https://job-boards.greenhouse.io/faraway"))
    assert greenhouse.load_settings(workspace)["boards"] == {}


def test_a_board_is_requested_once_per_run(workspace, run, fake, tmp_path):
    fake.boards["andes"] = [job(61), job(62, title="Data Platform Engineer")]
    links = found(tmp_path, "https://job-boards.greenhouse.io/andes")
    read(workspace, run, fake, found=links)
    read(workspace, run, fake, title="Data Platform Engineer", found=links)
    listing_requests = [u for u in fake.urls if u.endswith("/andes/jobs?content=true")]
    assert len(listing_requests) == 1 and fake.details_read() == ["61", "62"]


def test_stored_and_repeated_postings_are_not_read_again(workspace, run, fake, cli, tmp_path):
    fake.boards["andes"] = [job(71)]
    links = found(tmp_path, "https://job-boards.greenhouse.io/andes/jobs/71")
    summary = read(workspace, run, fake, found=links)
    readings = tmp_path / "r.json"
    readings.write_text(json.dumps([{"external_id": "71"}]), encoding="utf-8")
    cli("postings", "import", str(run["run_id"]), summary["drafts_path"], "--readings",
        str(readings))
    again = read(workspace, run, fake, title="Data Platform Engineer", found=links)
    assert again["duplicate_in_run"] == 1
    cli("run", "finish", str(run["run_id"]))
    _, second, _ = cli("run", "start", "--days", "7")
    later = read(workspace, second, fake, found=links)
    assert later["already_seen"] == 1 and fake.details_read() == ["71"]


def test_the_cap_per_title(workspace, run, fake, tmp_path, monkeypatch):
    fake.boards["andes"] = [job(80 + i) for i in range(5)]
    monkeypatch.setattr(greenhouse.common, "context", _capped(greenhouse.common.context, 3))
    summary = read(workspace, run, fake,
                   found=found(tmp_path, "https://job-boards.greenhouse.io/andes"))
    assert summary["new"] == 3 and summary["capped"] is True


def _capped(original, limit):
    def context(*args, **kwargs):
        ctx = original(*args, **kwargs)
        ctx.max_results = limit
        return ctx
    return context


def test_pacing(workspace, run, fake, tmp_path):
    fake.boards["andes"] = [job(91), job(92)]
    read(workspace, run, fake, found=found(tmp_path, "https://job-boards.greenhouse.io/andes"))
    gaps = [b - a for a, b in zip(fake.times, fake.times[1:], strict=False)]
    assert len(fake.times) == 3 and all(gap >= 5 for gap in gaps), gaps


# ── country words ─────────────────────────────────────────────────────────

def test_a_country_without_place_words_asks_once(workspace, cli, fake, tmp_path):
    set_profile(workspace, cli, country="CL")
    cli("providers", "enable", "greenhouse")
    _, run, _ = cli("run", "start", "--days", "7")
    fake.boards["andes"] = [job(101, where="Santiago, Chile")]
    links = found(tmp_path, "https://job-boards.greenhouse.io/andes")
    with pytest.raises(JobTrackerError) as error:
        read(workspace, run, fake, found=links)
    assert error.value.code == "missing_country" and "--place-words" in error.value.message
    assert read(workspace, run, fake, found=links, place_words="Chile; Santiago")["new"] == 1
    saved = greenhouse.load_settings(workspace)["countries"]["CL"]
    assert saved["places"] == ["Chile", "Santiago"]


# ── stops and bad input ───────────────────────────────────────────────────

def test_refused_requests_stop_greenhouse_for_the_run(workspace, run, fake, tmp_path):
    fake.overrides[f"{API}/andes/jobs?content=true"] = (403, "refused")
    summary = read(workspace, run, fake,
                   found=found(tmp_path, "https://job-boards.greenhouse.io/andes"))
    assert summary["stopped"]["reason"] == "blocked"
    with pytest.raises(JobTrackerError) as error:
        read(workspace, run, fake, title="Data Platform Engineer")
    assert error.value.code == "provider_stopped"


def test_three_unreadable_answers_in_a_row_end_only_the_title(workspace, run, fake, tmp_path):
    for board in ("a1", "a2", "a3"):
        fake.overrides[f"{API}/{board}/jobs?content=true"] = (200, "<html>maintenance</html>")
    summary = read(workspace, run, fake, found=found(
        tmp_path, *(f"https://job-boards.greenhouse.io/{b}" for b in ("a1", "a2", "a3"))))
    assert summary["stopped"] is None and summary["title_retries"] == 3
    assert summary["title_problem"]["kind"] == "unreadable_answers"
    assert len(fake.urls) == 6                       # each answer requested twice
    second = read(workspace, run, fake, title="Analytics Engineer")
    assert second["stopped"] is None


def test_an_unreadable_answer_readable_on_retry(workspace, run, fake, tmp_path):
    url = f"{API}/a1/jobs?content=true"
    answers = [(200, "<html>maintenance</html>"), (200, '{"jobs": []}')]

    def get(asked: str):
        return answers.pop(0) if asked == url else fake(asked)

    summary = greenhouse.read(workspace, run["run_id"], TITLE, get=get, clock=fake.clock,
                              sleep=fake.sleep,
                              found=found(tmp_path, "https://job-boards.greenhouse.io/a1"))
    assert summary["title_retries"] == 1 and summary["title_problem"] is None


def test_no_answer_three_times_stops(workspace, run, fake, tmp_path):
    def down(url: str):
        raise OSError("connection refused")

    summary = greenhouse.read(workspace, run["run_id"], TITLE, get=down, clock=fake.clock,
                              sleep=fake.sleep, found=found(tmp_path, *(
                                  f"https://job-boards.greenhouse.io/{b}"
                                  for b in ("a1", "a2", "a3"))))
    assert summary["stopped"]["reason"] == "error"
    assert "no answer" in summary["stopped"]["detail"]


def test_found_file_must_be_a_list(workspace, run, fake, tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"links": []}', encoding="utf-8")
    with pytest.raises(JobTrackerError) as error:
        read(workspace, run, fake, found=str(path))
    assert error.value.code == "invalid_found"


def test_cli_options_are_checked_per_provider(workspace, run, cli, tmp_path):
    code, out, _ = cli("providers", "read", "greenhouse", str(run["run_id"]), "--title", TITLE,
                       "--search-url", "https://www.glassdoor.com/Job/x")
    assert code == 1 and out["error"]["code"] == "invalid_option"


def test_provider_file():
    from jobtracker.core import providers

    item = {p["id"]: p for p in providers.list_providers()}["greenhouse"]
    assert item["valid"], item["problems"]
    assert (item["kind"], item["coverage"], item["access"], item["dependencies"],
            item["requires_login"], item["live_walk"]) == (
        "jobs", "global", "http", [], False, False)
    text = (Path(__file__).resolve().parents[1] / "providers" / "greenhouse.md").read_text(
        encoding="utf-8")
    for required in ("jt providers read greenhouse <run_id> --title", "--found", "--readings",
                     "my.greenhouse.io/jobs/search", "site:job-boards.greenhouse.io",
                     "| PE | Peru;", "--place-words", "Never press Apply"):
        assert required in text, required


def test_a_throttle_is_waited_out_with_retry_after(workspace, run, fake, tmp_path):
    url = f"{API}/andes/jobs?content=true"
    fake.overrides[url] = (429, "slow down", "30")
    summary = read(workspace, run, fake,
                   found=found(tmp_path, "https://job-boards.greenhouse.io/andes"))
    assert summary["stopped"]["reason"] == "throttled"     # still 429 after three attempts
    board = [t for u, t in zip(fake.urls, fake.times, strict=True) if u == url]
    assert len(board) == 3 and board[1] - board[0] == pytest.approx(30)
    with pytest.raises(JobTrackerError) as error:
        read(workspace, run, fake, title="Data Platform Engineer")
    assert error.value.code == "provider_cooling"
