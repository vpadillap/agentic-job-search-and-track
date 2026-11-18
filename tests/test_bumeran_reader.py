"""provider-bumeran: the Bumeran reader against a fake browser that serves fictional
site data. No test opens a real browser or touches bumeran.com.pe."""
from __future__ import annotations

import copy
import json
import re
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

import pytest

from jobtracker.core import db
from jobtracker.core.errors import JobTrackerError
from jobtracker.core.readers import bumeran

FIXTURES = Path(__file__).parent / "fixtures" / "bumeran"
PERSONA = json.loads((Path(__file__).parent / "fixtures" / "persona.json").read_text(
    encoding="utf-8"))
TITLE = "Senior Data Engineer"
RECENT = (date.today() - timedelta(days=1)).strftime("%d-%m-%Y")


def fixture(name: str) -> dict:
    text = (FIXTURES / name).read_text(encoding="utf-8").replace("{recent}", RECENT)
    return json.loads(text)


def results(*entries: dict, total: int | None = None, number: int = 0) -> dict:
    data = fixture("search.json")
    data["content"] = list(entries) if entries else data["content"]
    data["total"] = len(data["content"]) if total is None else total
    data["number"] = number
    return data


def entry(posting_id: int, days_ago: int = 1, company: str = "Altamar Retail S.A.") -> dict:
    item = copy.deepcopy(fixture("search.json")["content"][0])
    item.update(id=posting_id, empresa=company,
                fechaPublicacion=(date.today() - timedelta(days=days_ago)).strftime("%d-%m-%Y"))
    return item


def posting(posting_id: int, name: str = "posting-questions.json") -> dict:
    data = fixture(name)
    data["aviso"]["id"] = posting_id
    data["aviso"]["seoFriendlyUrl"] = f"/empleos/fictional-posting-{posting_id}.html"
    return data


class FakeBrowser:
    """Serves pages by URL; records every page opened, the clock, and the waits."""

    def __init__(self) -> None:
        self.searches: dict[str, dict] = {}
        self.postings: dict[str, dict] = {}
        self.overrides: dict[str, bumeran.Page] = {}
        self.opened: list[str] = []
        self.times: list[float] = []
        self.waits: list[float] = []
        self.now = 1_000.0
        self.started = 0

    @contextmanager
    def browser(self):
        self.started += 1
        yield self.open

    def open(self, url: str, watch: tuple[str, ...]) -> bumeran.Page:
        self.opened.append(url)
        self.times.append(self.now)
        if url in self.overrides:
            return self.overrides[url]
        match = re.search(r"/empleos/(\d+)\.html$", url)
        if match:
            body = self.postings.get(match.group(1)) or posting(int(match.group(1)))
            return bumeran.Page(200, "Fictional posting | Bumeran Perú", url, [
                {"url": f"{bumeran.BASE_URL}/{bumeran.POSTING_API}{match.group(1)}",
                 "status": 200, "body": body}])
        body = self.searches.get(url, results(total=0) | {"content": []})
        page = int(url.split("?page=")[1]) - 1 if "?page=" in url else 0
        return bumeran.Page(200, "Empleos | Bumeran Perú", url, [
            {"url": f"{bumeran.BASE_URL}/{bumeran.SEARCH_API}?pageSize=20&page={page}",
             "status": 200, "body": body}])

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.now += seconds

    def posting_pages(self) -> list[str]:
        return [u for u in self.opened if "/empleos/" in u and "busqueda" not in u]


@pytest.fixture
def fake() -> FakeBrowser:
    return FakeBrowser()


@pytest.fixture
def run(workspace, cli):
    """A run with Bumeran (the repository's provider file) switched on."""
    needs = dict(PERSONA["job_needs"])
    needs["titles"] = PERSONA["target_titles"]
    path = workspace.home / "profile-input.json"
    path.write_text(json.dumps(needs), encoding="utf-8")
    assert cli("profile", "set", str(path))[0] == 0
    path.unlink()
    assert cli("providers", "enable", "bumeran")[0] == 0
    code, started, _ = cli("run", "start", "--days", "7")
    assert code == 0 and started["to_search"] == ["bumeran"], started
    return started


def read(workspace, run, fake, title=TITLE):
    return bumeran.read(workspace, run["run_id"], title, browser=fake.browser,
                        clock=fake.clock, sleep=fake.sleep)


SEARCH_7 = bumeran.search_url(TITLE, 7)


def drafts_of(summary) -> list[dict]:
    return json.loads(Path(summary["drafts_path"]).read_text(encoding="utf-8"))


def run_status(workspace, run) -> dict:
    with db.session(workspace) as conn:
        row = conn.execute("SELECT providers FROM search_runs WHERE id = ?",
                           (run["run_id"],)).fetchone()
    return next(p for p in json.loads(row["providers"]) if p["id"] == "bumeran")


# ── URLs and values ───────────────────────────────────────────────────────

@pytest.mark.parametrize("days, part", [
    (1, "publicacion-menor-a-2-dias"), (2, "publicacion-menor-a-2-dias"),
    (5, "publicacion-menor-a-5-dias"), (7, "publicacion-menor-a-7-dias"),
    (10, "publicacion-menor-a-15-dias"), (30, "publicacion-menor-a-1-mes"), (45, None)])
def test_posting_age_window(days, part):
    assert bumeran.window(days) == part


def test_search_urls():
    assert SEARCH_7 == ("https://www.bumeran.com.pe/empleos-publicacion-menor-a-7-dias-busqueda-"
                        "senior-data-engineer.html")
    assert bumeran.search_url("Analista de Datos Sr.", 7, 2).endswith(
        "busqueda-analista-de-datos-sr.html?page=2")
    assert bumeran.search_url("Ingeniero de Datos", 60) == (
        "https://www.bumeran.com.pe/empleos-busqueda-ingeniero-de-datos.html")


def test_description_keeps_paragraphs_and_list_items():
    text = bumeran.description_text(
        "<p><strong>¿Qué buscamos?</strong></p><ul><li>Python</li><li>SQL &amp; dbt</li></ul>"
        "<p>Línea uno<br>Línea dos</p>")
    assert text == "¿Qué buscamos?\n\n• Python\n• SQL & dbt\n\nLínea uno\nLínea dos"


def test_questions_without_the_expected_answer():
    asked, unknown = bumeran.questions(fixture("posting-questions.json")["aviso"]["preguntas"])
    assert asked == [
        {"text": "¿Cuántos años de experiencia tienes con Airflow?", "kind": "text"},
        {"text": "¿Tienes disponibilidad para ir a la oficina?", "kind": "choice",
         "options": ["Sí", "No"]}]
    assert unknown == 0
    assert "indiceCorrecta" not in json.dumps(asked)
    asked, unknown = bumeran.questions([{"nueva": {"texto": "¿Pregunta de otro tipo?"}}])
    assert asked == [{"text": "¿Pregunta de otro tipo?", "kind": "text"}] and unknown == 1


# ── reading one title ─────────────────────────────────────────────────────

def test_one_title_read_into_drafts(workspace, run, fake):
    fake.searches[SEARCH_7] = results()          # 2 recent postings, 1 from 2020
    fake.postings["900002"] = posting(900002, "posting-salary.json")
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None, summary
    assert (summary["pages"], summary["cards"], summary["outside_window"], summary["new"]) == \
        (1, 3, 1, 2)
    assert fake.opened == [SEARCH_7, f"{bumeran.BASE_URL}/empleos/900001.html",
                           f"{bumeran.BASE_URL}/empleos/900002.html"]
    first, second = drafts_of(summary)
    assert first["external_id"] == "900001"
    assert first["url"] == "https://www.bumeran.com.pe/empleos/fictional-posting-900001.html"
    assert (first["title"], first["company"], first["location"], first["country"]) == (
        "Senior Data Engineer", "Altamar Retail S.A.", "Lima, Lima", "PE")
    assert first["posted_at"] == (date.today() - timedelta(days=1)).isoformat()
    assert first["seniority"] == "Senior" and first["contract_type"] == "full-time"
    assert first["description"].startswith("¿Qué buscamos?\n\nUna persona para el equipo")
    assert "• Airflow & dbt" in first["description"]
    assert [q["kind"] for q in first["form_questions"]] == ["text", "choice"]
    assert first["site_work_mode"] == "hybrid" and first["asks_expected_salary"] is True
    assert first["site_contract"] == {"type": "Full-time", "hiring": "Indeterminado"}
    assert first["work_mode"] is None and first["published_salary"] is None   # agent's reading
    assert second["company"] == "Confidencial"
    assert second["site_work_mode"] == "remote"
    assert second["site_salary"] == {"min": 9000, "max": 12000, "frequency": "Mensual",
                                     "type": "Bruto"}
    assert fake.started == 1


def test_page_two_and_the_page_cap(workspace, run, fake):
    first = [entry(910000 + i) for i in range(20)]
    second = [entry(920000 + i) for i in range(20)]
    fake.searches[SEARCH_7] = results(*first, total=60)
    fake.searches[SEARCH_7 + "?page=2"] = results(*second, total=60, number=1)
    summary = read(workspace, run, fake)
    searches = [u for u in fake.opened if "busqueda" in u]
    assert searches == [SEARCH_7, SEARCH_7 + "?page=2"]             # 40 per title: 2 pages
    assert summary["pages"] == 2 and summary["new"] == 40


def test_a_short_page_is_the_last(workspace, run, fake):
    fake.searches[SEARCH_7] = results(entry(930001), total=1)
    read(workspace, run, fake)
    assert [u for u in fake.opened if "busqueda" in u] == [SEARCH_7]


def test_page_two_that_is_not_page_two_stops(workspace, run, fake):
    fake.searches[SEARCH_7] = results(*[entry(940000 + i) for i in range(20)], total=60)
    fake.searches[SEARCH_7 + "?page=2"] = results(entry(950001), total=60, number=0)
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "error"
    assert run_status(workspace, run)["status"] == "failed"


def test_no_results(workspace, run, fake):
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None and summary["new"] == 0 and summary["drafts_path"] is None
    assert fake.opened == [SEARCH_7]


def test_pacing_holds_within_and_across_calls(workspace, run, fake):
    fake.searches[SEARCH_7] = results(entry(960001), entry(960002), total=2)
    read(workspace, run, fake)
    read(workspace, run, fake, title="Data Platform Engineer")
    gaps = [b - a for a, b in zip(fake.times, fake.times[1:], strict=False)]
    assert gaps and all(gap >= 5 for gap in gaps)


def test_a_posting_is_opened_once_per_run(workspace, run, fake):
    fake.searches[SEARCH_7] = results(entry(970001), total=1)
    other = bumeran.search_url("Data Platform Engineer", 7)
    fake.searches[other] = results(entry(970001), total=1)
    read(workspace, run, fake)
    summary = read(workspace, run, fake, title="Data Platform Engineer")
    assert summary["duplicate_in_run"] == 1
    assert fake.posting_pages() == [f"{bumeran.BASE_URL}/empleos/970001.html"]


def test_a_posting_stored_by_an_earlier_run_is_not_opened_again(workspace, run, fake, cli,
                                                                 tmp_path):
    fake.searches[SEARCH_7] = results(entry(980001), total=1)
    summary = read(workspace, run, fake)
    readings = tmp_path / "r.json"
    readings.write_text(json.dumps([{"external_id": "980001", "work_mode": "hybrid",
                                     "language": "es"}]), encoding="utf-8")
    assert cli("postings", "import", str(run["run_id"]), summary["drafts_path"],
               "--readings", str(readings))[0] == 0
    cli("run", "finish", str(run["run_id"]))
    code, second, _ = cli("run", "start", "--days", "7")
    assert code == 0
    fake.opened.clear()
    again = read(workspace, second, fake)
    assert again["already_seen"] == 1 and again["new"] == 0
    assert fake.posting_pages() == []


# ── stop conditions ───────────────────────────────────────────────────────

@pytest.mark.parametrize("page", [
    bumeran.Page(403, "Attention Required! | Cloudflare", SEARCH_7, []),
    bumeran.Page(200, "Just a moment...", SEARCH_7, []),
    bumeran.Page(429, "Too Many Requests", SEARCH_7, []),
    bumeran.Page(200, "Empleos | Bumeran Perú", SEARCH_7, [
        {"url": f"{bumeran.BASE_URL}/{bumeran.SEARCH_API}", "status": 403, "body": None}]),
])
def test_a_block_or_challenge_stops_bumeran_for_the_run(workspace, run, fake, page):
    fake.overrides[SEARCH_7] = page
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "blocked"
    status = run_status(workspace, run)
    assert status["status"] == "failed" and status["reason"] == "blocked"
    with pytest.raises(JobTrackerError) as refused:
        read(workspace, run, fake, title="Data Platform Engineer")
    assert refused.value.code == "provider_stopped"
    assert len(fake.opened) == 1                                   # nothing opened after


def test_a_block_mid_title_keeps_what_was_read(workspace, run, fake):
    fake.searches[SEARCH_7] = results(entry(990001), entry(990002), total=2)
    fake.overrides[f"{bumeran.BASE_URL}/empleos/990002.html"] = bumeran.Page(
        403, "Attention Required! | Cloudflare", "x", [])
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "blocked"
    assert [d["external_id"] for d in drafts_of(summary)] == ["990001"]


def test_missing_site_data_stops_with_an_error(workspace, run, fake):
    fake.overrides[SEARCH_7] = bumeran.Page(200, "Empleos | Bumeran Perú", SEARCH_7, [])
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "error"
    assert "sent no readable data" in summary["stopped"]["detail"]


def test_a_closed_posting_is_listed_not_drafted(workspace, run, fake):
    fake.searches[SEARCH_7] = results(entry(991001), total=1)
    fake.postings["991001"] = posting(991001, "posting-closed.json")
    summary = read(workspace, run, fake)
    assert summary["new"] == 0 and summary["stopped"] is None
    assert summary["unreadable"] == [{"external_id": "991001",
                                      "url": f"{bumeran.BASE_URL}/empleos/991001.html",
                                      "reason": "the posting is finalizado"}]


def test_a_second_call_while_one_runs_is_refused(workspace, run, fake):
    folder = Path(run["capture_folder"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / bumeran.LOCK_FILE).write_text(str(fake.now), encoding="utf-8")
    with pytest.raises(JobTrackerError) as busy:
        read(workspace, run, fake)
    assert busy.value.code == "reader_busy" and fake.opened == [] and fake.started == 0


def test_a_missing_browser_opens_no_page_and_records_nothing(workspace, run, fake):
    @contextmanager
    def missing():
        raise JobTrackerError("missing_dependency", "Run: " + bumeran.INSTALL,
                              tool="scrapling")
        yield  # pragma: no cover

    with pytest.raises(JobTrackerError) as error:
        bumeran.read(workspace, run["run_id"], TITLE, browser=missing, clock=fake.clock,
                     sleep=fake.sleep)
    assert error.value.code == "missing_dependency"
    assert "jt providers install bumeran" in error.value.message
    assert run_status(workspace, run)["status"] == "pending"
    assert not (Path(run["capture_folder"]) / bumeran.LOCK_FILE).exists()


def test_the_browser_guard_cancels_applications_and_heavy_resources():
    calls = []

    class Route:
        def __init__(self, url, kind):
            self.request = type("R", (), {"url": url, "resource_type": kind})()

        def abort(self):
            calls.append(("abort", self.request.url))

        def continue_(self):
            calls.append(("continue", self.request.url))

    for url, kind in [("https://www.bumeran.com.pe/api/candidates/aviso/1/postularV2", "xhr"),
                      ("https://www.bumeran.com.pe/x.png", "image"),
                      ("https://www.bumeran.com.pe/api/avisos/searchV2", "xhr"),
                      ("https://www.bumeran.com.pe/main.js", "script")]:
        bumeran._route(Route(url, kind))
    assert calls == [("abort", "https://www.bumeran.com.pe/api/candidates/aviso/1/postularV2"),
                     ("abort", "https://www.bumeran.com.pe/x.png"),
                     ("continue", "https://www.bumeran.com.pe/api/avisos/searchV2"),
                     ("continue", "https://www.bumeran.com.pe/main.js")]


def test_no_page_is_an_application_page(workspace, run, fake):
    fake.searches[SEARCH_7] = results()
    read(workspace, run, fake)
    assert all("postular" not in url for url in fake.opened)


def test_the_cli_runs_the_bumeran_reader(workspace, run, cli, monkeypatch, fake):
    fake.searches[SEARCH_7] = results(entry(992001), total=1)
    original = bumeran.read

    def patched(*args, **kwargs):  # the real browser is replaced by the fake one
        return original(*args, browser=fake.browser, clock=fake.clock, sleep=fake.sleep)

    monkeypatch.setattr(bumeran, "read", patched)
    code, out, _ = cli("providers", "read", "bumeran", str(run["run_id"]), "--title", TITLE)
    assert code == 0, out
    assert out["read"]["new"] == 1


# ── import with readings ──────────────────────────────────────────────────

def test_drafts_import_with_questions_and_without_hints(workspace, run, fake, cli, tmp_path):
    fake.searches[SEARCH_7] = results(entry(993001), total=1)
    summary = read(workspace, run, fake)
    readings = tmp_path / "r.json"
    readings.write_text(json.dumps([{
        "external_id": "993001", "work_mode": "hybrid",
        "work_mode_detail": "Híbrido: 3 días en oficina", "language": "es"}],
        ensure_ascii=False), encoding="utf-8")
    code, report, _ = cli("postings", "import", str(run["run_id"]), summary["drafts_path"],
                          "--readings", str(readings))
    assert code == 0, report
    with db.session(workspace) as conn:
        row = conn.execute("SELECT * FROM postings WHERE provider = 'bumeran'").fetchone()
        asked = conn.execute("SELECT text, kind, options FROM form_questions WHERE posting_id = ?"
                             " ORDER BY position", (row["id"],)).fetchall()
    assert row["work_mode"] == "hybrid" and row["work_mode_detail"] == "Híbrido: 3 días en oficina"
    assert row["description"] == drafts_of(summary)[0]["description"]
    assert [(q["kind"], json.loads(q["options"]) if q["options"] else None) for q in asked] == [
        ("text", None), ("choice", ["Sí", "No"])]


# ── live check (contacts bumeran.com.pe; only with JOBTRACKER_LIVE=1) ─────

@pytest.mark.live
@pytest.mark.skipif(not __import__("os").environ.get("JOBTRACKER_LIVE"),
                    reason="contacts the real site; set JOBTRACKER_LIVE=1 to run it")
def test_live_one_search_page():
    """The recipe still works: one results page, read in a headless Scrapling session."""
    with bumeran.scrapling_browser() as open_page:
        page = open_page(bumeran.search_url("Data Engineer", 7), (bumeran.SEARCH_API,))
    bumeran._check(page, page.url)
    data = bumeran._data(page, bumeran.SEARCH_API, page.url)
    assert isinstance(data["content"], list) and "total" in data
