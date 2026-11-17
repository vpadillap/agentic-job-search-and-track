"""provider-indeed: the Indeed reader against a fake browser and fictional pages.
No test opens a real browser or reaches Indeed."""
from __future__ import annotations

import json
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from jobtracker.core import db, search
from jobtracker.core.errors import JobTrackerError
from jobtracker.core.readers import indeed

PERSONA = json.loads((Path(__file__).parent / "fixtures" / "persona.json").read_text(
    encoding="utf-8"))
TITLE = "Data Engineer"


def card(job_id: str, days_ago: int = 1, **extra) -> dict:
    published = datetime.combine(date.today() - timedelta(days=days_ago), datetime.min.time())
    return {"jobkey": job_id, "title": f"Ingeniero de Datos {job_id}",
            "company": "Andes Datos Ficticios", "formattedLocation": "Lima, Lima",
            "pubDate": int(published.timestamp() * 1000), "jobTypes": [],
            "remoteLocation": False, "extractedSalary": None, **extra}


def page(*cards: dict, title: str = "Empleos de Data Engineer en Lima | Indeed") -> tuple:
    data = {"metaData": {"mosaicProviderJobCardsModel": {"results": list(cards)}}}
    html = (f"<html><head><title>{title}</title></head><body><script>"
            f'window.mosaic.providerData["mosaic-provider-jobcards"]={json.dumps(data)};'
            "</script></body></html>")
    return 200, html, title


DESCRIPTION = ("Somos una empresa ficticia.\n\n\n  Requisitos:   Python y SQL\n"
               "Modalidad híbrida: 2 días en oficina")


class FakeBrowser:
    """Search pages by `start`, panels by job id; records actions and the clock."""

    def __init__(self) -> None:
        self.pages: dict[int, tuple] = {}
        self.panels: dict[str, tuple] = {}
        self.actions: list[str] = []
        self.times: list[float] = []
        self.now = 1_000.0
        self.locales: list[str] = []
        self.closed = 0

    def __call__(self, locale: str) -> FakeBrowser:
        self.locales.append(locale)
        return self

    def search(self, url: str):
        self.actions.append(url)
        self.times.append(self.now)
        start = int(urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("start", [0])[0])
        return self.pages.get(start, page())

    def open(self, job_id: str):
        self.actions.append(f"open {job_id}")
        self.times.append(self.now)
        return self.panels.get(job_id, (DESCRIPTION, "Empleos | Indeed"))

    def close(self) -> None:
        self.closed += 1

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def opened(self) -> list[str]:
        return [a.split(" ", 1)[1] for a in self.actions if a.startswith("open ")]


@pytest.fixture
def fake() -> FakeBrowser:
    return FakeBrowser()


def start_run(cli) -> dict:
    code, run, _ = cli("run", "start", "--days", "7")
    assert code == 0 and run["to_search"] == ["indeed"], run
    return run


@pytest.fixture
def run(workspace, cli):
    needs = dict(PERSONA["job_needs"])
    needs["titles"] = PERSONA["target_titles"]
    path = workspace.home / "profile-input.json"
    path.write_text(json.dumps(needs), encoding="utf-8")
    assert cli("profile", "set", str(path))[0] == 0
    path.unlink()
    assert cli("providers", "enable", "indeed")[0] == 0
    return start_run(cli)


def read(workspace, run, fake, title=TITLE, location="Lima"):
    return indeed.read(workspace, run["run_id"], title, location, browser=fake,
                       clock=fake.clock, sleep=fake.sleep)


def drafts_of(summary) -> list[dict]:
    return json.loads(Path(summary["drafts_path"]).read_text(encoding="utf-8"))


# ── search parameters ─────────────────────────────────────────────────────

@pytest.mark.parametrize("days,expected", [(1, 1), (2, 3), (7, 7), (10, 14), (90, 14)])
def test_posting_age(days, expected):
    assert indeed.fromage(days) == expected


def test_site_of_the_country():
    assert (indeed.site("PE"), indeed.site("US"), indeed.site(None)) == (
        "pe.indeed.com", "www.indeed.com", "www.indeed.com")


def test_search_url(workspace, run, fake):
    read(workspace, run, fake)
    query = urllib.parse.parse_qs(urllib.parse.urlparse(fake.actions[0]).query)
    assert fake.actions[0].startswith("https://pe.indeed.com/jobs?")
    assert query == {"q": [TITLE], "l": ["Lima"], "fromage": ["7"]}
    assert fake.locales == ["es-PE"] and fake.closed == 1


# ── drafts ────────────────────────────────────────────────────────────────

def test_one_title_read_into_drafts(workspace, run, fake):
    fake.pages[0] = page(card("a1"), card("a2", jobTypes=["Tiempo completo"],
                                          extractedSalary={"min": 3100, "max": 5500,
                                                           "type": "MONTHLY"}),
                         card("a3", days_ago=10))
    summary = read(workspace, run, fake)
    assert {k: summary[k] for k in ("pages", "cards", "outside_window", "new", "stopped")} == {
        "pages": 1, "cards": 3, "outside_window": 1, "new": 2, "stopped": None}
    first, second = drafts_of(summary)
    assert first["url"] == "https://pe.indeed.com/viewjob?jk=a1"
    assert (first["title"], first["company"], first["location"], first["country"]) == (
        "Ingeniero de Datos a1", "Andes Datos Ficticios", "Lima, Lima", "PE")
    assert first["posted_at"] == (date.today() - timedelta(days=1)).isoformat()
    assert first["description"] == ("Somos una empresa ficticia.\n\nRequisitos: Python y SQL\n"
                                    "Modalidad híbrida: 2 días en oficina")
    assert first["work_mode"] is None and first["language"] is None  # the agent's reading
    assert (second["contract_type"], second["salary_shown"]) == ("full-time",
                                                                 "3100-5500 (monthly)")
    assert fake.opened() == ["a1", "a2"]                  # never the posting outside the window
    folder = Path(run["capture_folder"])
    assert len(list(folder.glob("indeed-*.html"))) == 1
    assert len(list(folder.glob("indeed-*.txt"))) == 2


def test_readings_import_the_drafts(workspace, run, fake, cli, tmp_path):
    fake.pages[0] = page(card("b1"))
    summary = read(workspace, run, fake)
    readings = tmp_path / "r.json"
    readings.write_text(json.dumps([{"external_id": "b1", "work_mode": "hybrid",
                                     "work_mode_detail": "Modalidad híbrida: 2 días en oficina",
                                     "language": "es"}]), encoding="utf-8")
    code, report, _ = cli("postings", "import", str(run["run_id"]), summary["drafts_path"],
                          "--readings", str(readings))
    assert code == 0 and report["new"] == 1, report


def test_paging_until_no_new_postings_or_the_limit(workspace, run, fake):
    fake.pages[0] = page(*(card(f"p{i}") for i in range(15)))
    fake.pages[10] = page(*(card(f"p{i}") for i in range(10, 25)))
    fake.pages[20] = page(*(card(f"p{i}") for i in range(20, 35)))
    summary = read(workspace, run, fake)
    assert summary["cards"] == 30 and summary["pages"] == 2    # the limit: 30 postings
    assert summary["duplicate_in_run"] == 5 and len(fake.opened()) == 25
    assert all("start=20" not in a for a in fake.actions)


def test_no_results(workspace, run, fake):
    summary = read(workspace, run, fake)
    assert (summary["pages"], summary["cards"], summary["stopped"]) == (1, 0, None)


# ── pacing, duplicates, stored postings, one call at a time ──────────────

def test_pacing_within_and_across_calls(workspace, run, fake):
    fake.pages[0] = page(card("c1"), card("c2"))
    read(workspace, run, fake)
    read(workspace, run, fake, title="Analytics Engineer")
    gaps = [b - a for a, b in zip(fake.times, fake.times[1:], strict=False)]
    assert len(fake.times) == 4 and all(gap >= 5 for gap in gaps), gaps


def test_a_posting_stored_earlier_is_not_clicked(workspace, run, fake, cli, tmp_path):
    fake.pages[0] = page(card("d1"))
    summary = read(workspace, run, fake)
    readings = tmp_path / "r.json"
    readings.write_text(json.dumps([{"external_id": "d1", "language": "es"}]),
                        encoding="utf-8")
    cli("postings", "import", str(run["run_id"]), summary["drafts_path"], "--readings",
        str(readings))
    cli("run", "finish", str(run["run_id"]))
    later = start_run(cli)
    fake.pages[0] = page(card("d1"), card("d2"))
    summary = read(workspace, later, fake)
    assert (summary["already_seen"], summary["new"]) == (1, 1)
    assert fake.opened() == ["d1", "d2"]                  # d1 only in the first run


def test_a_second_call_while_one_runs_is_refused(workspace, run, fake):
    lock = Path(run["capture_folder"]) / "indeed.lock"
    lock.write_text(str(fake.now - 60), encoding="utf-8")
    with pytest.raises(JobTrackerError) as busy:
        read(workspace, run, fake)
    assert busy.value.code == "reader_busy" and fake.actions == []


# ── stop conditions ───────────────────────────────────────────────────────

@pytest.mark.parametrize("answer,reason", [
    ((403, "<html></html>", "Blocked - Indeed.com"), "blocked"),
    ((200, "<html></html>", "Security Check - Indeed.com"), "blocked"),
    ((200, "<html></html>", "Iniciar sesión | Cuentas Indeed"), "blocked"),
    ((200, "<html><body>nothing</body></html>", "Indeed"), "error"),
])
def test_stops(workspace, run, fake, answer, reason):
    fake.pages[0] = answer
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == reason
    with db.session(workspace) as conn:
        provider = next(p for p in search.summary(conn, run["run_id"])["providers"]
                        if p["id"] == "indeed")
    assert (provider["status"], provider["reason"]) == ("failed", reason)
    before = len(fake.actions)
    with pytest.raises(JobTrackerError) as refused:
        read(workspace, run, fake, title="Analytics Engineer")
    assert refused.value.code == "provider_stopped" and len(fake.actions) == before


def test_a_missing_panel_keeps_what_was_read(workspace, run, fake):
    fake.pages[0] = page(card("e1"), card("e2"), card("e3"))
    fake.panels["e2"] = (None, "Empleos | Indeed")
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "error"
    assert [d["external_id"] for d in drafts_of(summary)] == ["e1"]
    assert fake.opened() == ["e1", "e2"] and fake.closed == 1


def test_a_browser_failure_is_an_error(workspace, run, fake):
    def broken(url):
        raise RuntimeError("net::ERR_CONNECTION_RESET")

    fake.search = broken
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "error" and fake.closed == 1
