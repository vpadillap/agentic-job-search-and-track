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


def page(*cards: dict, title: str = "Empleos de Data Engineer en Lima | Indeed",
         total: int | None = None, status: int = 200) -> tuple:
    data = {"metaData": {"mosaicProviderJobCardsModel": {"results": list(cards)}}}
    count = f'<script>window.x={{"totalJobCount": {total}}};</script>' if total else ""
    html = (f"<html><head><title>{title}</title></head><body><script>"
            f'window.mosaic.providerData["mosaic-provider-jobcards"]={json.dumps(data)};'
            f"</script>{count}</body></html>")
    return status, html, title


DESCRIPTION = ("Somos una empresa ficticia.\n\n\n  Requisitos:   Python y SQL\n"
               "Modalidad híbrida: 2 días en oficina")


def variant_of(url: str) -> str:
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if query.get("sort") == ["date"]:
        return "date"
    if query.get("l") == ["remoto"]:
        return "remote"
    if query.get("fromage") == ["1"]:
        return "last day"
    if query.get("fromage") == ["3"]:
        return "last 3 days"
    return "relevance" if "l" in query else "whole country"


class FakeBrowser:
    """First pages by variant, panels by job id; records actions and the clock."""

    def __init__(self) -> None:
        self.pages: dict[str, tuple] = {}
        self.panels: dict[str, str | None] = {}
        self.actions: list[str] = []
        self.times: list[float] = []
        self.now = 1_000.0
        self.locales: list[str] = []
        self.closed = 0

    def __call__(self, locale: str) -> FakeBrowser:
        self.locales.append(locale)
        return self

    def search(self, url: str, select):
        self.actions.append(url)
        self.times.append(self.now)
        answer = self.pages.get(variant_of(url), page())
        if isinstance(answer, list):   # answers in order; the last one is repeated
            answer = answer.pop(0) if len(answer) > 1 else answer[0]
        status, html, title = answer
        result = indeed.SearchPage(status, html, title)
        for job_id in select(html):
            self.actions.append(f"open {job_id}")
            result.panels[job_id] = self.panels.get(job_id, DESCRIPTION)
        return result

    def close(self) -> None:
        self.closed += 1

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def opened(self) -> list[str]:
        return [a.split(" ", 1)[1] for a in self.actions if a.startswith("open ")]

    def searched(self) -> list[str]:
        return [variant_of(a) for a in self.actions if not a.startswith("open ")]


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


def test_the_variants_of_one_search():
    names = [n for n, _ in indeed.variants("pe.indeed.com", TITLE, "Lima", 7)]
    assert names == ["relevance", "date", "last day", "whole country", "remote", "last 3 days"]
    urls = dict(indeed.variants("pe.indeed.com", TITLE, "Lima", 7))
    query = urllib.parse.parse_qs(urllib.parse.urlparse(urls["date"]).query)
    assert query == {"q": [TITLE], "l": ["Lima"], "fromage": ["7"], "sort": ["date"]}
    assert "l=" not in urls["whole country"] and "l=remoto" in urls["remote"]
    no_place = [n for n, _ in indeed.variants("pe.indeed.com", TITLE, None, 3)]
    assert no_place == ["relevance", "date", "last day", "remote"]      # no 3-day repeat


def test_search_url(workspace, run, fake):
    read(workspace, run, fake)
    query = urllib.parse.parse_qs(urllib.parse.urlparse(fake.actions[0]).query)
    assert fake.actions[0].startswith("https://pe.indeed.com/jobs?")
    assert query == {"q": [TITLE], "l": ["Lima"], "fromage": ["7"]}
    assert fake.locales == ["es-PE"] and fake.closed == 1


# ── drafts ────────────────────────────────────────────────────────────────

def test_one_title_read_into_drafts(workspace, run, fake):
    fake.pages["relevance"] = page(card("a1"), card("a2", jobTypes=["Tiempo completo"],
                                                    extractedSalary={"min": 3100, "max": 5500,
                                                                     "type": "MONTHLY"}),
                                   card("a3", days_ago=10))
    summary = read(workspace, run, fake)
    assert {k: summary[k] for k in ("cards", "outside_window", "new", "stopped")} == {
        "cards": 3, "outside_window": 1, "new": 2, "stopped": None}
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


def test_readings_import_the_drafts(workspace, run, fake, cli, tmp_path):
    fake.pages["relevance"] = page(card("b1"))
    summary = read(workspace, run, fake)
    readings = tmp_path / "r.json"
    readings.write_text(json.dumps([{"external_id": "b1", "work_mode": "hybrid",
                                     "work_mode_detail": "Modalidad híbrida: 2 días en oficina",
                                     "language": "es"}]), encoding="utf-8")
    code, report, _ = cli("postings", "import", str(run["run_id"]), summary["drafts_path"],
                          "--readings", str(readings))
    assert code == 0 and report["new"] == 1, report


# ── several first pages ───────────────────────────────────────────────────

def test_variants_add_postings_one_page_does_not_show(workspace, run, fake):
    fake.pages["relevance"] = page(card("v1"), card("v2"), total=40)
    fake.pages["date"] = page(card("v2"), card("v3"), total=40)
    fake.pages["last day"] = page(card("v4"), total=40)
    summary = read(workspace, run, fake)
    assert fake.opened() == ["v1", "v2", "v3", "v4"]            # each posting clicked once
    assert summary["site_total"] == 40 and summary["new"] == 4
    assert [(v["variant"], v["new"]) for v in summary["variants"]] == [
        ("relevance", 2), ("date", 1), ("last day", 1), ("whole country", 0), ("remote", 0)]
    assert fake.searched() == ["relevance", "date", "last day", "whole country", "remote"]


def test_variants_stop_at_the_site_total(workspace, run, fake):
    fake.pages["relevance"] = page(card("t1"), card("t2"), total=2)
    summary = read(workspace, run, fake)
    assert fake.searched() == ["relevance"] and summary["new"] == 2


def test_variants_stop_after_two_without_anything_new(workspace, run, fake):
    fake.pages["relevance"] = page(card("n1"))
    fake.pages["date"] = page(card("n1"))
    fake.pages["last day"] = page(card("n1"))
    read(workspace, run, fake)
    assert fake.searched() == ["relevance", "date", "last day"]


def test_the_cap_ends_the_title(workspace, run, fake, monkeypatch):
    fake.pages["relevance"] = page(*(card(f"c{i}") for i in range(4)), total=50)
    fake.pages["date"] = page(*(card(f"d{i}") for i in range(4)), total=50)
    original = indeed.common.context

    def capped(*args, **kwargs):
        ctx = original(*args, **kwargs)
        ctx.max_results = 3
        return ctx

    monkeypatch.setattr(indeed.common, "context", capped)
    summary = read(workspace, run, fake)
    assert summary["capped"] is True and summary["new"] == 3
    assert fake.searched() == ["relevance"]


@pytest.mark.parametrize("wall", [
    page(title="Iniciar sesión | Cuentas Indeed"),
    page(status=403, title="Security Check - Indeed.com"),
])
def test_a_wall_on_a_later_variant_ends_the_title_but_not_indeed(workspace, run, fake, wall):
    fake.pages["relevance"] = page(card("w1"), total=30)
    fake.pages["date"] = wall
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None and summary["new"] == 1
    assert summary["ended_early"].startswith("date:")
    fake.pages["relevance"] = page(card("w2"), total=1)
    later = read(workspace, run, fake, title="Analytics Engineer")
    assert later["stopped"] is None and later["new"] == 1       # the next title still reads


def test_no_results(workspace, run, fake):
    summary = read(workspace, run, fake)
    assert (summary["cards"], summary["stopped"]) == (0, None)


# ── pacing, duplicates, stored postings, one call at a time ──────────────

def test_pacing_within_and_across_calls(workspace, run, fake):
    fake.pages["relevance"] = page(card("c1"), card("c2"), total=2)
    read(workspace, run, fake)
    read(workspace, run, fake, title="Analytics Engineer")
    gaps = [b - a for a, b in zip(fake.times, fake.times[1:], strict=False)]
    assert len(fake.times) == 2 and all(gap >= 5 for gap in gaps), gaps


def test_a_posting_stored_earlier_is_not_clicked(workspace, run, fake, cli, tmp_path):
    fake.pages["relevance"] = page(card("d1"), total=1)
    summary = read(workspace, run, fake)
    readings = tmp_path / "r.json"
    readings.write_text(json.dumps([{"external_id": "d1", "language": "es"}]),
                        encoding="utf-8")
    cli("postings", "import", str(run["run_id"]), summary["drafts_path"], "--readings",
        str(readings))
    cli("run", "finish", str(run["run_id"]))
    later = start_run(cli)
    fake.pages["relevance"] = page(card("d1"), card("d2"), total=2)
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

SECURITY_CHECK = (200, "<html></html>", "Security Check - Indeed.com")


def test_a_security_check_that_clears_is_waited_out(workspace, run, fake):
    fake.pages["relevance"] = [SECURITY_CHECK, page()]
    summary = read(workspace, run, fake)
    assert summary["stopped"] is None
    assert 10 <= fake.times[1] - fake.times[0] <= 20


def test_a_security_check_that_stays_is_a_cool_down(workspace, run, fake):
    fake.pages["relevance"] = SECURITY_CHECK
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "throttled"
    assert len(fake.actions) == 3
    with db.session(workspace) as conn:
        provider = next(p for p in search.summary(conn, run["run_id"])["providers"]
                        if p["id"] == "indeed")
    assert provider["status"] == "pending" and provider["cooldown_until"]
    with pytest.raises(JobTrackerError) as refused:
        read(workspace, run, fake, title="Analytics Engineer")
    assert refused.value.code == "provider_cooling" and len(fake.actions) == 3
    fake.now += 15 * 60
    fake.pages["relevance"] = page()
    assert read(workspace, run, fake)["stopped"] is None      # the same run goes on


@pytest.mark.parametrize("answer,reason", [
    ((403, "<html></html>", "Blocked - Indeed.com"), "blocked"),
    ((200, "<html></html>", "Attention Required! | Cloudflare"), "blocked"),
    ((200, "<html></html>", "Iniciar sesión | Cuentas Indeed"), "blocked"),
    ((200, "<html><body>nothing</body></html>", "Indeed"), "error"),
])
def test_stops_on_the_first_page(workspace, run, fake, answer, reason):
    fake.pages["relevance"] = answer
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
    fake.pages["relevance"] = page(card("e1"), card("e2"), card("e3"))
    fake.panels["e2"] = None
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "error"
    assert [d["external_id"] for d in drafts_of(summary)] == ["e1"]
    assert fake.closed == 1


def test_a_browser_failure_is_an_error(workspace, run, fake):
    def broken(url, select):
        raise RuntimeError("net::ERR_CONNECTION_RESET")

    fake.search = broken
    summary = read(workspace, run, fake)
    assert summary["stopped"]["reason"] == "error" and fake.closed == 1


def test_a_missing_scrapling_names_the_install_command(workspace, run, fake):
    def missing(locale):
        raise JobTrackerError("missing_dependency", "Run: " + indeed.INSTALL, tool="scrapling")

    with pytest.raises(JobTrackerError) as error:
        indeed.read(workspace, run["run_id"], TITLE, "Lima", browser=missing,
                    clock=fake.clock, sleep=fake.sleep)
    assert "jt providers install indeed" in error.value.message
