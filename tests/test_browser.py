"""The panel in a real browser, against the demo seed (panel-shell, search-results-board).

Needs Chromium for Playwright: `python -m playwright install chromium`. Skipped
when it is not installed.
"""
from __future__ import annotations

import json
import re
import socket
import threading
import time
from datetime import datetime

import pytest

from jobtracker.core import db, demo, salary, search

playwright_api = pytest.importorskip("playwright.sync_api")
uvicorn = pytest.importorskip("uvicorn")

pytestmark = pytest.mark.browser
expect = playwright_api.expect


@pytest.fixture(scope="module")
def browser():
    try:
        with playwright_api.sync_playwright() as p:
            instance = p.chromium.launch()
            yield instance
            instance.close()
    except Exception as error:  # browser not installed
        pytest.skip(f"Chromium for Playwright is not available: {error}")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def server(home):
    from jobtracker.web.app import create_app

    port = _free_port()
    config = uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning")
    instance = uvicorn.Server(config)
    thread = threading.Thread(target=instance.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not instance.started and time.time() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    instance.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def seeded(home):
    demo.seed(home)
    return home


@pytest.fixture
def page(browser, server):
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="en-US")
    context.grant_permissions(["clipboard-read", "clipboard-write"], origin=server)
    tab = context.new_page()
    errors: list[str] = []
    tab.on("pageerror", lambda error: errors.append(str(error)))
    tab.base = server  # type: ignore[attr-defined]
    yield tab
    context.close()
    assert errors == [], errors


def open_board(page, tab="search"):
    page.goto(f"{page.base}/#{tab}")
    expect(page.locator(".brand-name")).to_be_visible()


def row(page, company: str):
    return page.locator("tbody tr").filter(has=page.locator(".job-company", has_text=re.compile(
        f"^{re.escape(company)}$")))


# ── panel-shell ───────────────────────────────────────────────────────────

def test_local_access_loads_the_panel(seeded, page):
    open_board(page)
    expect(page.locator(".brand-name")).to_have_text("Job Radar")
    expect(page.get_by_role("heading", name="Latest search")).to_be_visible()


def test_reload_keeps_the_tab(seeded, page):
    open_board(page)
    page.get_by_role("link", name=re.compile("^Applications")).click()
    expect(page).to_have_url(re.compile("#applications$"))
    page.reload()
    current = page.locator('.tab[aria-current="page"]')
    expect(current).to_contain_text("Applications")
    page.goto(page.base + "/")
    expect(page.locator('.tab[aria-current="page"]')).to_contain_text("Applications")


def test_tabs_have_counters(seeded, page):
    open_board(page)
    expect(page.locator(".tab", has_text="Search").locator(".count")).to_have_text("8")
    expect(page.locator(".tab", has_text="Applications").locator(".count")).to_have_text("7")
    page.get_by_role("link", name="Profile & agent").click()
    expect(page.get_by_role("heading", name="Agent memory")).to_be_visible()


def _switch_language(page, name: str) -> None:
    """Click a language button and wait until the server has saved the choice: the
    panel switches at once, the save follows in the background."""
    with page.expect_response(lambda r: r.url.endswith("/api/settings/language")
                              and r.request.method == "POST") as saved:
        page.get_by_role("button", name=name, exact=True).click()
    assert saved.value.ok


def test_switching_language_without_reload_and_it_persists(seeded, page):
    open_board(page)
    page.evaluate("window.__marker = 1")
    _switch_language(page, "ES")
    expect(page.get_by_role("heading", name="Última búsqueda")).to_be_visible()
    assert page.evaluate("window.__marker") == 1                     # no reload
    _switch_language(page, "EN")
    expect(page.get_by_role("heading", name="Latest search")).to_be_visible()
    expect(page.locator(".tab", has_text="Applications")).to_be_visible()
    page.evaluate("localStorage.clear()")
    page.reload()                                                      # a restart reads config
    expect(page.get_by_role("heading", name="Latest search")).to_be_visible()
    _switch_language(page, "ES")
    expect(page.get_by_role("heading", name="Última búsqueda")).to_be_visible()
    page.evaluate("localStorage.clear()")
    page.reload()
    expect(page.get_by_role("heading", name="Última búsqueda")).to_be_visible()


def test_agent_text_is_unchanged_by_the_language(seeded, page):
    open_board(page)
    target = row(page, "Altamar Retail")
    target.get_by_role("button", name=re.compile("Show details")).click()
    note = page.locator(".note", has_text="Matches the target title").first
    before = note.inner_text()
    description = page.locator(".description").first.inner_text()
    page.get_by_role("button", name="ES", exact=True).click()
    expect(page.get_by_role("heading", name="Descripción original")).to_be_visible()
    assert page.locator(".note", has_text="Matches the target title").first.inner_text() == before
    assert page.locator(".description").first.inner_text() == description


def test_new_results_appear_without_reloading(seeded, page):
    open_board(page)
    expect(page.locator("tbody tr")).to_have_count(9)
    with db.session(seeded) as conn:
        run = search.start_run(conn, seeded, 7, demo=True,
                               demo_providers=[{"id": "linkedin", "name": "LinkedIn"}],
                               demo_titles=["Data Engineer"])
        search.import_postings(conn, run["run_id"], [{
            "provider": "linkedin", "external_id": "fresh-1",
            "url": "https://example.com/demo/fresh-1", "title": "Staff Data Engineer",
            "company": "Ondina Analytics", "location": "Lima", "country": "PE",
            "work_mode": "remote", "contract_type": "full-time",
            "posted_at": datetime.now().date().isoformat(), "description": "Fictional."}])
        search.finish_run(conn, run["run_id"])
    expect(page.locator(".job-company", has_text="Ondina Analytics")).to_be_visible(timeout=10000)


def test_two_searches_of_one_day_on_one_page(seeded, page):
    with db.session(seeded) as conn:
        for number, company in ((1, "Ondina Analytics"), (2, "Pradera Datos")):
            run = search.start_run(conn, seeded, 7, demo=True, new_group=number == 1,
                                   demo_providers=[{"id": "linkedin", "name": "LinkedIn"}],
                                   demo_titles=["Data Engineer"])
            search.import_postings(conn, run["run_id"], [{
                "provider": "linkedin", "external_id": f"same-day-{number}",
                "url": f"https://example.com/demo/same-day-{number}",
                "title": "Staff Data Engineer", "company": company, "location": "Lima",
                "country": "PE", "work_mode": "remote", "contract_type": "full-time",
                "posted_at": datetime.now().date().isoformat(), "description": "Fictional."}])
            search.finish_run(conn, run["run_id"])
    open_board(page)
    expect(page.locator("tbody tr")).to_have_count(2)
    expect(page.locator(".job-company", has_text="Ondina Analytics")).to_be_visible()
    expect(page.locator(".job-company", has_text="Pradera Datos")).to_be_visible()
    expect(page.get_by_test_id("page-searches")).to_contain_text("2 searches on this page")


def _running_search(home, scored: bool = False) -> int:
    """A search still running, on its own page: two sites, one done and one cooling
    down, and two new postings, the first one scored when asked."""
    from jobtracker.core import scoring
    from tests.test_scoring import submission
    with db.session(home) as conn:
        run = search.start_run(conn, home, 7, demo=True, new_group=True,
                               demo_providers=[{"id": "linkedin", "name": "LinkedIn"},
                                               {"id": "bumeran", "name": "Bumeran"}],
                               demo_titles=["Data Engineer"])
        report = search.import_postings(conn, run["run_id"], [{
            "provider": "linkedin", "external_id": f"live-{number}",
            "url": f"https://example.com/demo/live-{number}", "title": "Staff Data Engineer",
            "company": company, "location": "Lima", "country": "PE", "work_mode": "remote",
            "contract_type": "full-time", "posted_at": datetime.now().date().isoformat(),
            "description": "Fictional."} for number, company in
            ((1, "Ondina Analytics"), (2, "Pradera Datos"))])
        search.record_provider(conn, run["run_id"], "linkedin", "ok")
        search.record_cooldown(conn, run["run_id"], "bumeran", None, "429", time.time())
        if scored:
            first = report["postings"][0]["posting_id"]
            scoring.set_score(conn, first, submission(), run_id=run["run_id"])
    return run["run_id"]


def _score_live_posting(home, run_id: int, company: str) -> None:
    from jobtracker.core import scoring
    from tests.test_scoring import submission
    with db.session(home) as conn:
        posting = conn.execute("SELECT id FROM postings WHERE company = ?", (company,)).fetchone()
        scoring.set_score(conn, posting["id"], submission(), run_id=run_id)


def test_running_search_shows_unscored_postings_as_scoring(seeded, page):
    _running_search(seeded, scored=True)
    open_board(page)
    expect(page.locator("tbody tr")).to_have_count(2)
    expect(row(page, "Ondina Analytics").locator(".score")).to_have_text("86")
    expect(row(page, "Pradera Datos").locator(".score.pending")).to_have_text("Scoring…")


def test_minimum_score_keeps_postings_being_scored(seeded, page):
    run_id = _running_search(seeded)
    open_board(page)
    page.get_by_role("button", name="Score: any").click()
    page.get_by_role("radio", name="≥ 80").check()
    expect(page.locator("tbody tr")).to_have_count(2)            # both still being scored
    _score_live_posting(seeded, run_id, "Ondina Analytics")       # 86: stays
    expect(row(page, "Ondina Analytics").locator(".score")).to_have_text("86", timeout=10000)
    expect(page.locator("tbody tr")).to_have_count(2)
    with db.session(seeded) as conn:                              # 66: now hidden by the filter
        from jobtracker.core import scoring
        from tests.test_scoring import submission
        posting = conn.execute("SELECT id FROM postings WHERE company = 'Pradera Datos'").fetchone()
        scoring.set_score(conn, posting["id"], submission(skills={"points": 7}), run_id=run_id)
    expect(page.locator("tbody tr")).to_have_count(1, timeout=10000)


def test_score_arrives_without_reloading(seeded, page):
    run_id = _running_search(seeded)
    open_board(page)
    expect(row(page, "Pradera Datos").locator(".score.pending")).to_be_visible()
    _score_live_posting(seeded, run_id, "Pradera Datos")
    expect(row(page, "Pradera Datos").locator(".score")).to_have_text("86", timeout=10000)


def test_tracking_during_a_running_search(seeded, page):
    run_id = _running_search(seeded, scored=True)
    open_board(page)
    row(page, "Ondina Analytics").get_by_role("button", name="Track", exact=True).click()
    expect(row(page, "Ondina Analytics").locator("a.tracked")).to_have_text(re.compile("Tracked"))
    with db.session(seeded) as conn:
        assert search.summary(conn, run_id)["status"] == "running"   # the search goes on
    expect(page.get_by_test_id("run-progress")).to_be_visible()


def test_finished_search_shows_a_dash_for_an_unscored_posting(seeded, page):
    run_id = _running_search(seeded)
    with db.session(seeded) as conn:
        search.finish_run(conn, run_id)
    open_board(page)
    expect(row(page, "Pradera Datos").locator(".score.none")).to_have_text("–")
    expect(page.locator(".score.pending")).to_have_count(0)
    expect(page.get_by_test_id("run-progress")).to_have_count(0)


def test_progress_of_a_running_search(seeded, page):
    _running_search(seeded, scored=True)
    open_board(page)
    progress = page.get_by_test_id("run-progress")
    expect(progress).to_contain_text("Sites done: 1 of 2")
    expect(progress).to_contain_text("Scored: 1 of 2 new")
    expect(progress).to_contain_text(re.compile(r"Bumeran resumes at \d"))


def test_change_while_typing_keeps_input_and_offers_to_load(seeded, page):
    open_board(page)
    box = page.get_by_role("searchbox", name="Search results")
    box.click()
    box.type("Alt")
    with db.session(seeded) as conn:
        db.bump_changes(conn)
    expect(page.get_by_text("New data is available.")).to_be_visible(timeout=10000)
    expect(box).to_have_value("Alt")
    expect(box).to_be_focused()
    page.get_by_role("button", name="Load it now").click()
    expect(page.get_by_text("New data is available.")).to_have_count(0)
    expect(box).to_have_value("Alt")


def test_freshness_is_shown(seeded, page):
    open_board(page)
    expect(page.locator(".header-meta").first).to_contain_text("Data updated")


def test_copying_a_command(seeded, page):
    open_board(page)
    chip = page.locator(".command-box")
    command = chip.locator("code").inner_text()
    chip.get_by_role("button", name="Copy command").click()
    expect(chip.get_by_role("button", name="Copied")).to_be_visible()
    assert page.evaluate("navigator.clipboard.readText()") == command == "/job-search days=7"


def test_pending_indicator_is_shown(seeded, page):
    open_board(page)
    expect(page.get_by_role("button", name=re.compile("pending for the agent"))).to_be_visible()


def test_before_setup(home, page):
    open_board(page)
    expect(page.get_by_role("heading", name="Setup is needed")).to_be_visible()
    expect(page.locator(".command-box code")).to_have_text("/setup")


# ── search-results-board ──────────────────────────────────────────────────

def test_run_summary_and_skipped_provider(seeded, page):
    open_board(page)
    summary = page.locator(".run")
    expect(summary).to_contain_text("15 found")
    expect(summary).to_contain_text("10 new for you")
    expect(summary).to_contain_text("LinkedIn · 7")
    skipped = re.compile("Glassdoor skipped: needs you present")
    expect(summary.locator(".chip.warn")).to_have_text(skipped)


def test_filtered_out_list_with_reasons(seeded, page):
    open_board(page)
    page.get_by_role("button", name="See filtered out and why").click()
    items = page.locator("#filtered-list li")
    expect(items).to_have_count(3)
    expect(items.filter(has_text="Andes Minería")).to_contain_text("Location")
    expect(items.filter(has_text="Andes Minería")).to_contain_text("Arequipa")


def _pending_count(page) -> int:
    button = page.get_by_role("button", name=re.compile("pending for the agent"))
    return int(re.search(r"\d+", button.inner_text()).group())


def test_restoring_a_filtered_out_posting(seeded, page):
    open_board(page)
    before = _pending_count(page)
    page.get_by_role("button", name="See filtered out and why").click()
    items = page.locator("#filtered-list li")
    andes = items.filter(has_text="Andes Minería")
    andes.get_by_role("button", name=re.compile("^Restore")).click()
    expect(page.get_by_text("Restored: it will be scored with the pending work")).to_be_visible()
    expect(items).to_have_count(2)
    expect(row(page, "Andes Minería").locator(".score.none")).to_have_text("–")
    expect(page.get_by_role("button", name=re.compile("pending for the agent"))).to_contain_text(
        str(before + 1))


def test_restoring_during_a_running_search(seeded, page):
    run_id = _running_search(seeded)
    with db.session(seeded) as conn:
        posting = conn.execute("SELECT id FROM postings WHERE company = 'Pradera Datos'").fetchone()
        search.filter_postings(conn, run_id, [{"posting_id": posting["id"], "reason": "location",
                                               "detail": "Onsite in Chiclayo"}])
    open_board(page)
    expect(page.locator("tbody tr")).to_have_count(1)
    page.get_by_role("button", name="See filtered out and why").click()
    page.locator("#filtered-list li").filter(has_text="Pradera Datos").get_by_role(
        "button", name=re.compile("^Restore")).click()
    expect(page.get_by_text("Restored: this search will score it")).to_be_visible()
    expect(row(page, "Pradera Datos").locator(".score.pending")).to_have_text("Scoring…")


def test_site_chip_shows_when_it_was_last_searched(seeded, page):
    _running_search(seeded)
    open_board(page)
    expect(page.get_by_test_id("provider-linkedin")).to_have_text(
        re.compile(r"^LinkedIn · 2 · \d{1,2}:\d{2}"))


def test_salary_without_reliable_data(seeded, page):
    open_board(page)
    cell = row(page, "Nortia Seguros")
    expect(cell).to_contain_text("No reliable data")
    assert cell.locator(".money").count() == 0


def test_source_link_opens_in_a_new_tab(seeded, page):
    open_board(page)
    link = row(page, "Quena Labs").locator("a.source")
    assert link.get_attribute("target") == "_blank"
    assert "noopener" in link.get_attribute("rel")
    assert link.get_attribute("href") == "https://example.com/demo/linkedin/quena"


def test_expanding_a_row(seeded, page):
    open_board(page)
    row(page, "Altamar Retail").get_by_role("button", name=re.compile("Show details")).click()
    detail = page.locator(".detail")
    expect(detail.locator(".description")).to_contain_text("Altamar Retail busca un/a Senior")
    expect(detail.locator(".component")).to_have_count(5)
    expect(detail.get_by_role("heading", name="Why 86")).to_be_visible()
    expect(detail.locator("a.evidence")).to_have_count(3)
    expect(detail).to_contain_text("High confidence · 3 comparable sources")


def test_type_ahead_filters_on_each_keystroke(seeded, page):
    open_board(page)
    box = page.get_by_role("searchbox", name="Search results")
    box.type("Quena")
    expect(page.locator("tbody tr")).to_have_count(1)
    expect(page.locator(".job-company")).to_have_text("Quena Labs")
    expect(page.locator(".footer")).to_contain_text("hidden by the search text")


def test_hidden_rows_are_disclosed(seeded, page):
    open_board(page)
    page.get_by_role("button", name="Score: any").click()
    page.get_by_role("radio", name="≥ 70").check()
    expect(page.locator(".footer")).to_contain_text("Showing 6 of 9")
    expect(page.locator(".footer")).to_contain_text("3 hidden by Score ≥ 70")


def test_possible_duplicates_are_separate_rows_with_a_mark(seeded, page):
    open_board(page)
    linkedin = row(page, "Altamar Retail")
    indeed = row(page, "Altamar Retail S.A.C.")
    expect(linkedin.locator(".tag.dup")).to_contain_text("Indeed in this search")
    expect(indeed.locator(".tag.dup")).to_contain_text("LinkedIn in this search")


def test_track(seeded, page):
    open_board(page)
    row(page, "Mistral Pagos").get_by_role("button", name="Track", exact=True).click()
    expect(row(page, "Mistral Pagos").locator("a.tracked")).to_have_text(re.compile("Tracked"))
    expect(page.locator(".tab", has_text="Applications").locator(".count")).to_have_text("8")
    assert row(page, "Mistral Pagos").locator("a.tracked").get_attribute("href") == "#applications"


def test_track_and_mark_applied(seeded, page):
    open_board(page)
    row(page, "Quena Labs").get_by_role("button", name="Track and mark applied").click()
    expect(row(page, "Quena Labs").locator("a.tracked")).to_have_text(re.compile("Applied"))
    with db.session(seeded) as conn:
        status, applied_on = conn.execute(
            "SELECT s.key, a.applied_on FROM applications a JOIN postings p"
            " ON p.id = a.posting_id JOIN statuses s ON s.id = a.status_id"
            " WHERE p.company = 'Quena Labs'").fetchone()
    assert status == "applied" and applied_on == datetime.now().date().isoformat()


def test_bulk_track(seeded, page):
    open_board(page)
    row(page, "Mistral Pagos").get_by_role("checkbox").check()
    row(page, "Cobre Logística").get_by_role("checkbox").check()
    expect(page.get_by_text("2 selected")).to_be_visible()
    page.locator(".filters").get_by_role("button", name="Track", exact=True).click()
    expect(row(page, "Mistral Pagos").locator("a.tracked")).to_be_visible()
    expect(row(page, "Cobre Logística").locator("a.tracked")).to_be_visible()


def test_dismissing_for_location_and_undo(seeded, page):
    open_board(page)
    target = row(page, "Cobre Logística")
    target.get_by_role("button", name="Dismiss with a reason").click()
    page.get_by_role("button", name="Location").click()
    expect(row(page, "Cobre Logística")).to_have_count(0)
    with db.session(seeded) as conn:
        reason = conn.execute(
            "SELECT d.reason FROM dismissals d JOIN postings p ON p.id = d.posting_id"
            " WHERE p.company = 'Cobre Logística'").fetchone()[0]
    assert reason == "location"
    expect(page.locator(".footer")).to_contain_text("2 dismissed")
    page.locator(".toast").get_by_role("button", name="Undo").click()
    expect(row(page, "Cobre Logística")).to_have_count(1)


def test_dismiss_with_other_reason_from_the_detail(seeded, page):
    open_board(page)
    row(page, "Vértiz Salud").get_by_role("button", name=re.compile("Show details")).click()
    page.locator(".detail").get_by_role("button", name="Other…").click()
    page.locator(".detail").get_by_role("textbox").fill("Recruiting agency")
    page.locator(".detail").get_by_role("button", name="Dismiss", exact=True).click()
    expect(row(page, "Vértiz Salud")).to_have_count(0)
    with db.session(seeded) as conn:
        note = conn.execute("SELECT note FROM dismissals WHERE reason = 'other'").fetchone()[0]
    assert note == "Recruiting agency"


def test_viewing_a_previous_run(seeded, page):
    open_board(page)
    page.get_by_label("Search shown").select_option(index=1)
    expect(page.get_by_role("heading", name=re.compile("^Search of"))).to_be_visible()
    expect(page.locator(".job-company")).to_have_text(["Kallpa Energía", "Inti Bank"])


def test_sorting_by_column(seeded, page):
    open_board(page)
    page.get_by_role("button", name="Job · company").click()
    titles = page.locator(".job-title").all_inner_texts()
    assert titles == sorted(titles, key=str.casefold)
    header = page.locator("th", has=page.get_by_role("button", name="Job · company"))
    expect(header).to_have_attribute("aria-sort", "ascending")


# ── keyboard ──────────────────────────────────────────────────────────────

def test_filter_menu_by_keyboard(seeded, page):
    open_board(page)
    button = page.get_by_role("button", name="Work mode: all")
    button.focus()
    page.keyboard.press("Enter")
    expect(page.get_by_role("checkbox", name="Remote")).to_be_focused()
    page.keyboard.press("Space")
    page.keyboard.press("Escape")
    expect(page.get_by_role("button", name="Work mode: Remote")).to_be_focused()
    expect(page.locator(".footer")).to_contain_text("hidden by Work mode: Remote")


def test_dismiss_by_keyboard(seeded, page):
    open_board(page)
    row(page, "Cobre Logística").get_by_role("button", name="Dismiss with a reason").focus()
    page.keyboard.press("Enter")
    expect(page.get_by_role("button", name="Industry")).to_be_focused()
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")                        # Low salary
    expect(row(page, "Cobre Logística")).to_have_count(0)


def test_expand_and_sort_by_keyboard(seeded, page):
    open_board(page)
    expand = row(page, "Mistral Pagos").get_by_role("button", name=re.compile("Show details"))
    expand.focus()
    page.keyboard.press("Enter")
    collapse = page.get_by_role("button", name=re.compile("Hide details of Data Engineer"))
    expect(collapse).to_have_attribute("aria-expanded", "true")
    page.get_by_role("button", name="Published").focus()
    page.keyboard.press("Enter")
    header = page.locator("th", has=page.get_by_role("button", name="Published"))
    expect(header).to_have_attribute("aria-sort", "descending")


# ── applications-board ────────────────────────────────────────────────────

def app_row(page, company: str):
    return page.locator("tbody tr").filter(has=page.locator(".job-company", has_text=company))


def test_score_changed_by_the_sent_resume(seeded, page):
    open_board(page, "applications")
    row_ = app_row(page, "Huaral Minerals")
    expect(row_.locator(".score")).to_have_text("90")
    expect(row_.locator(".delta")).to_have_text("+9 with your sent resume")


def test_ended_applications_are_hidden_by_default(seeded, page):
    open_board(page, "applications")
    expect(page.locator("tbody .job-company")).to_have_count(7)
    expect(app_row(page, "Altiplano Seguros")).to_have_count(0)
    expect(app_row(page, "Tika Foods")).to_have_count(0)          # custom ending status
    expect(page.locator(".footer")).to_contain_text("2 ended hidden")
    show = page.get_by_role("checkbox", name=re.compile("Show ended"))
    expect(show).to_have_accessible_name(re.compile("Rejected, Position frozen"))
    show.check()
    expect(app_row(page, "Tika Foods").locator(".status-chip")).to_have_text("Position frozen")
    expect(page.locator("tbody .job-company")).to_have_count(9)


def test_applications_type_ahead(seeded, page):
    open_board(page, "applications")
    box = page.get_by_role("searchbox", name="Search applications")
    box.type("Ceibo")
    expect(page.locator("tbody .job-company")).to_have_count(1)
    box.fill("")
    box.type("referral")                                         # tags are searched too
    expect(page.locator("tbody .job-company")).to_have_count(1)
    expect(app_row(page, "Lumen Edu")).to_have_count(1)


def test_one_count_card_per_status_in_use(seeded, page):
    open_board(page, "applications")
    cards = page.locator(".funnel-card .funnel-label")
    expect(cards).to_have_text(["New", "Applied", "Interview", "Offer", "Rejected (hidden)",
                                "Position frozen (hidden)"])
    applied = page.locator(".funnel-card", has_text="Applied")
    expect(applied.locator(".funnel-count")).to_have_text("3")


def test_funnel_card_filters_by_status(seeded, page):
    open_board(page, "applications")
    card = page.locator(".funnel-card", has_text="Interview")
    card.click()
    expect(card).to_have_attribute("aria-pressed", "true")
    expect(page.locator("tbody .job-company")).to_have_count(1)
    expect(app_row(page, "Ceibo Pagos")).to_have_count(1)


def test_an_ending_status_card_lists_its_hidden_applications(seeded, page):
    open_board(page, "applications")
    page.locator(".funnel-card", has_text="Position frozen").click()
    expect(page.locator("tbody .job-company")).to_have_count(1)
    expect(app_row(page, "Tika Foods")).to_have_count(1)
    expect(page.locator(".footer")).not_to_contain_text("hidden")


def test_sorting_by_status_follows_the_status_list(seeded, page):
    open_board(page, "applications")
    page.get_by_role("button", name="Status and tags").click()
    order = ["New", "Applied", "Interview", "Offer"]
    shown = [order.index(text) for text in page.locator("tbody .status-chip").all_inner_texts()]
    assert shown == sorted(shown) and len(shown) == 7


def test_inline_status_change_persists(seeded, page):
    open_board(page, "applications")
    quipu = app_row(page, "Quipu Analytics")
    quipu.get_by_role("button", name="Status: New. Change status").click()
    page.get_by_role("radio", name="Applied").click()      # picking closes the list
    expect(app_row(page, "Quipu Analytics").locator(".status-chip")).to_have_text("Applied")
    page.reload()
    expect(app_row(page, "Quipu Analytics").locator(".status-chip")).to_have_text("Applied")


def test_status_opens_from_the_status_itself(seeded, page):
    open_board(page, "applications")
    chip = app_row(page, "Quipu Analytics").locator(".status-chip")
    expect(chip).to_have_attribute("aria-expanded", "false")
    chip.click()                                   # the visible status, not a separate icon
    expect(chip).to_have_attribute("aria-expanded", "true")
    expect(page.get_by_role("radio", name="New")).to_be_checked()
    expect(page.get_by_role("textbox", name="New status")).to_be_visible()
    expect(page.get_by_role("textbox", name="Add tag")).to_have_count(0)
    page.keyboard.press("Escape")
    expect(chip).to_be_focused()
    page.keyboard.press("Enter")                   # keyboard opens it too
    expect(page.get_by_role("radio", name="Applied")).to_be_visible()


def test_tags_have_their_own_control(seeded, page):
    open_board(page, "applications")
    app_row(page, "Quipu Analytics").get_by_role("button", name="Add a tag").click()
    expect(page.get_by_role("textbox", name="Add tag")).to_be_visible()
    expect(page.get_by_role("radio")).to_have_count(0)
    expect(page.get_by_role("textbox", name="New status")).to_have_count(0)


def test_status_control_in_spanish(seeded, page):
    open_board(page, "applications")
    page.get_by_role("button", name="ES", exact=True).click()
    app_row(page, "Quipu Analytics").get_by_role(
        "button", name="Estado: Nuevo. Cambiar estado").click()
    expect(page.get_by_role("radio", name="Postulado")).to_be_visible()
    page.keyboard.press("Escape")
    expect(app_row(page, "Quipu Analytics").get_by_role(
        "button", name="Añadir una etiqueta")).to_be_visible()
    page.get_by_role("button", name="EN", exact=True).click()


def test_inline_status_creation_and_tags(seeded, page):
    open_board(page, "applications")
    app_row(page, "Finlima S.A.").get_by_role("button", name="Status: New. Change status").click()
    page.get_by_role("textbox", name="New status").fill("On hold")
    expect(page.get_by_role("checkbox", name="The application ended with this status")
           ).not_to_be_checked()
    page.get_by_role("button", name="Create and apply").click()
    expect(app_row(page, "Finlima S.A.").locator(".status-chip")).to_have_text("On hold")
    app_row(page, "Finlima S.A.").get_by_role("button", name="Add a tag").click()
    page.get_by_role("textbox", name="Add tag").fill("Remote friendly")
    page.get_by_role("button", name="Add tag", exact=True).click()
    expect(app_row(page, "Finlima S.A.").locator(".tag-chip")).to_contain_text("Remote friendly")
    page.keyboard.press("Escape")
    app_row(page, "Finlima S.A.").get_by_role("button", name="Remove tag Remote friendly").click()
    expect(app_row(page, "Finlima S.A.").locator(".tag-chip")).to_have_count(0)


def test_creating_an_ending_status_hides_the_application(seeded, page):
    open_board(page, "applications")
    app_row(page, "Finlima S.A.").get_by_role("button", name="Status: New. Change status").click()
    page.get_by_role("textbox", name="New status").fill("Hiring cancelled")
    page.get_by_role("checkbox", name="The application ended with this status").check()
    page.get_by_role("button", name="Create and apply").click()
    expect(app_row(page, "Finlima S.A.")).to_have_count(0)
    expect(page.locator(".footer")).to_contain_text("3 ended hidden")
    expect(page.locator(".funnel-card", has_text="Hiring cancelled")).to_contain_text("(hidden)")


def test_application_without_a_form(seeded, page):
    open_board(page, "applications")
    app_row(page, "Puna Energía").get_by_role("button", name=re.compile("Show details")).click()
    expect(page.locator(".detail")).to_contain_text("no visible application form")


def test_detail_shows_documents_questions_and_history(seeded, page):
    open_board(page, "applications")
    app_row(page, "Huaral Minerals").get_by_role("button", name=re.compile("Show details")).click()
    detail = page.locator(".detail")
    expect(detail.locator(".doc-card.sent")).to_contain_text("resume-sent.pdf")
    expect(detail.locator(".qa")).to_have_count(4)
    expect(detail.locator(".qa").first).to_contain_text("No proposed answer yet")
    expect(detail.locator(".history-row").first).to_contain_text("Found on Bumeran")
    expect(detail.locator(".history")).to_contain_text("Status: Applied")


def test_missing_documents_summary_filters(seeded, page):
    open_board(page, "applications")
    page.get_by_role("button", name="2 without a tailored resume").click()
    expect(page.locator("tbody .job-company")).to_have_count(2)
    expect(app_row(page, "Quipu Analytics")).to_have_count(1)
    expect(app_row(page, "Finlima S.A.")).to_have_count(1)
    expect(page.locator(".attention .command-box code")).to_have_text("/prepare-documents pending")


def test_copying_a_cover_letter(seeded, page):
    open_board(page, "applications")
    app_row(page, "Huaral Minerals").get_by_role("button", name=re.compile("Show details")).click()
    page.get_by_role("button", name="Copy text").click()
    expect(page.get_by_role("button", name="Copied")).to_be_visible()
    assert page.evaluate("navigator.clipboard.readText()").startswith("Estimado equipo")


def test_opening_a_document_downloads_it(seeded, page):
    open_board(page, "applications")
    app_row(page, "Huaral Minerals").get_by_role("button", name=re.compile("Show details")).click()
    with page.expect_download() as download:
        page.locator(".doc-card.sent").get_by_role("link", name="Open").click()
    assert download.value.suggested_filename == "resume-sent.pdf"


def test_details_save_on_change_and_persist(seeded, page):
    open_board(page, "applications")
    app_row(page, "Finlima S.A.").get_by_role("button", name=re.compile("Show details")).click()
    notes = page.get_by_role("textbox", name="Notes")
    notes.fill("Recruiter asked for references.")
    page.get_by_role("textbox", name="Contact").click()          # leaving the field saves it
    expect(page.locator(".field-state.saved")).to_be_visible()
    page.reload()
    app_row(page, "Finlima S.A.").get_by_role("button", name=re.compile("Show details")).click()
    expect(page.get_by_role("textbox", name="Notes")).to_have_value(
        "Recruiter asked for references.")


def test_uploading_the_sent_resume_from_the_board(seeded, page):
    open_board(page, "applications")
    app_row(page, "Finlima S.A.").get_by_role("button", name=re.compile("Show details")).click()
    page.locator(".detail input[type=file]").set_input_files(
        {"name": "final.pdf", "mimeType": "application/pdf", "buffer": b"%PDF-1.4 fictional"})
    expect(page.locator(".toast")).to_contain_text("Resume uploaded")
    expect(app_row(page, "Finlima S.A.").locator(".doc-line").first).to_have_text("Resume sent")
    page.get_by_role("button", name=re.compile("pending for the agent")).click()
    expect(page.get_by_role("region", name="Pending for the agent").locator("li").filter(
        has_text="Score to recalculate")).to_contain_text("Finlima S.A.")


def test_unsupported_upload_shows_the_reason(seeded, page):
    open_board(page, "applications")
    app_row(page, "Finlima S.A.").get_by_role("button", name=re.compile("Show details")).click()
    page.locator(".detail input[type=file]").set_input_files(
        {"name": "notes.txt", "mimeType": "text/plain", "buffer": b"hello"})
    expect(page.locator(".toast")).to_contain_text("PDF or DOCX")


def test_ghost_is_proposed_and_confirmed_by_the_user(seeded, page):
    open_board(page, "applications")
    row_ = app_row(page, "Lumen Edu")
    expect(row_.locator(".status-chip")).to_have_text("Applied")
    expect(row_).to_contain_text("days without a response")
    row_.get_by_role("button", name="Mark as ghosted?").click()
    expect(app_row(page, "Lumen Edu")).to_have_count(0)          # now ended, hidden
    expect(page.locator(".footer")).to_contain_text("3 ended hidden")


def test_applications_board_in_spanish(seeded, page):
    open_board(page, "applications")
    page.get_by_role("button", name="ES", exact=True).click()
    expect(page.locator(".funnel-card", has_text="Nuevo")).to_be_visible()
    expect(page.locator(".funnel-card", has_text="Rechazado")).to_contain_text("(ocultas)")
    expect(app_row(page, "Ceibo Pagos").locator(".status-chip")).to_have_text("Entrevista")


def test_search_track_actions_land_on_the_applications_board(seeded, page):
    open_board(page)
    row(page, "Mistral Pagos").get_by_role("button", name="Track", exact=True).click()
    row(page, "Quena Labs").get_by_role("button", name="Track and mark applied").click()
    expect(row(page, "Quena Labs").locator("a.tracked")).to_have_text(re.compile("Applied"))
    row(page, "Mistral Pagos").locator("a.tracked").click()
    expect(page).to_have_url(re.compile("#applications$"))
    expect(app_row(page, "Mistral Pagos").locator(".status-chip")).to_have_text("New")
    quena = app_row(page, "Quena Labs")
    expect(quena.locator(".status-chip")).to_have_text("Applied")
    expect(quena).to_contain_text("Follow up")                   # applied today: follow-up date set


# ── work mode with detail ─────────────────────────────────────────────────

def test_search_row_shows_the_work_mode_detail(seeded, page):
    open_board(page)
    expect(row(page, "Nortia Seguros").locator(".wm-chip")).to_contain_text(
        "Hybrid · Híbrido: 2 días presencial por semana")
    expect(row(page, "Cobre Logística").locator(".wm-chip")).to_contain_text("Work mode not stated")


def test_user_fills_in_a_missing_work_mode(seeded, page):
    open_board(page)
    row(page, "Cobre Logística").get_by_role("button", name=re.compile("^Edit work mode")).click()
    page.get_by_role("radio", name="Remote").check()
    page.get_by_label("How the posting describes it").fill("Early Friday")
    page.get_by_role("button", name="Save").click()
    chip = row(page, "Cobre Logística").locator(".wm-chip")
    expect(chip).to_contain_text("Remote · Early Friday")
    expect(chip.locator(".wm-edited")).to_have_text("edited")
    page.reload()
    expect(row(page, "Cobre Logística").locator(".wm-chip")).to_contain_text(
        "Remote · Early Friday")


def test_work_mode_corrected_in_applications_shows_everywhere(seeded, page):
    open_board(page, "applications")
    app_row(page, "Huaral Minerals").get_by_role(
        "button", name=re.compile("^Edit work mode")).click()
    page.get_by_role("radio", name="Hybrid").check()
    page.get_by_label("How the posting describes it").fill("Fridays from home")
    page.keyboard.press("Enter")
    expect(app_row(page, "Huaral Minerals").locator(".wm-chip")).to_contain_text(
        "Hybrid · Fridays from home")
    app_row(page, "Huaral Minerals").get_by_role("button", name=re.compile("Show details")).click()
    expect(page.locator(".detail .history")).to_contain_text(
        "Work mode set by you: Hybrid · Fridays from home")
    with db.session(seeded) as conn:
        posting_id = conn.execute(
            "SELECT p.id FROM postings p WHERE p.company = 'Huaral Minerals'").fetchone()[0]
        assert search.posting(conn, posting_id, detail=False)["work_mode_detail"] == (
            "Fridays from home")


# ── reading the posting ───────────────────────────────────────────────────

LONG_TAIL = "Last line of a long fictional description."


def make_long_description(home, company: str) -> None:
    text = "\n".join(f"• Fictional requirement number {n}." for n in range(1, 61))
    with db.session(home) as conn:
        conn.execute("UPDATE postings SET description = ? WHERE company = ?",
                     (text + "\n" + LONG_TAIL, company))


def no_inner_scroll(locator) -> bool:
    return locator.evaluate(
        "e => e.scrollHeight <= e.clientHeight + 1"
        " && !['auto', 'scroll'].includes(getComputedStyle(e).overflowY)")


def test_search_description_can_be_read_in_full(seeded, page):
    make_long_description(seeded, "Mistral Pagos")
    open_board(page)
    row(page, "Mistral Pagos").get_by_role("button", name=re.compile("Show details")).click()
    detail = page.locator(".detail")
    more = detail.get_by_role("button", name="Read the full description")
    description = detail.locator(".description")
    expect(more).to_have_attribute("aria-expanded", "false")
    assert description.evaluate("e => e.scrollHeight > e.clientHeight + 1")  # rest is hidden
    more.click()
    expect(detail.get_by_role("button", name="Show less")).to_have_attribute(
        "aria-expanded", "true")
    expect(description).to_contain_text(LONG_TAIL)
    assert no_inner_scroll(description)  # everything shown, no scroll bar of its own
    detail.get_by_role("button", name="Show less").click()
    expect(detail.get_by_role("button", name="Read the full description")).to_be_focused()


def test_applications_show_the_description_and_the_posting_link(seeded, page):
    make_long_description(seeded, "Huaral Minerals")
    open_board(page, "applications")
    target = app_row(page, "Huaral Minerals")
    link = target.get_by_role("link", name=re.compile("^Open posting · Bumeran"))
    expect(link).to_have_attribute("href", re.compile(r"^https://example\.com/demo/bumeran/"))
    expect(link).to_have_attribute("target", "_blank")
    expect(link).to_have_attribute("rel", "noopener noreferrer")
    target.get_by_role("button", name=re.compile("Show details")).click()
    detail = page.locator(".detail")
    expect(detail.locator(".posting-description")).to_contain_text(
        "Fictional requirement number 1.")
    detail.get_by_role("button", name="Read the full description").click()
    expect(detail.locator(".description")).to_contain_text(LONG_TAIL)
    assert no_inner_scroll(detail.locator(".description"))
    expect(detail.locator(".posting-description").get_by_role(
        "link", name=re.compile("^Open posting"))).to_have_attribute("target", "_blank")


def test_offered_salary_is_entered_and_shown(seeded, page):
    open_board(page, "applications")
    expect(app_row(page, "Puna Energía").locator(".offered")).to_contain_text("offered")
    app_row(page, "Puna Energía").get_by_role("button", name=re.compile("Show details")).click()
    expect(page.locator(".history")).to_contain_text("Applied on")
    app_row(page, "Puna Energía").get_by_role("button", name=re.compile("Hide details")).click()
    finlima = app_row(page, "Finlima S.A.")
    expect(finlima.locator(".offered")).to_have_count(0)
    finlima.get_by_role("button", name=re.compile("Show details")).click()
    page.get_by_role("textbox", name="Salary offered / month").fill("11000")
    page.get_by_role("textbox", name="Contact").click()          # leaving the field saves it
    expect(page.locator(".field-state.saved")).to_be_visible()
    expect(app_row(page, "Finlima S.A.").locator(".offered")).to_contain_text("11")
    page.reload()
    expect(app_row(page, "Finlima S.A.").locator(".offered")).to_contain_text("offered")


# ── the tables fit the screen (improve-table-layout) ─────────────────────

def _fits(page) -> dict:
    expect(page.locator("section.results tbody tr").first).to_be_attached()
    return page.evaluate("""() => {
      const doc = document.documentElement;
      const box = document.querySelector('section.results');
      return { page: doc.scrollWidth <= doc.clientWidth + 1,
               table: box.scrollWidth <= box.clientWidth + 1 };
    }""")


@pytest.mark.parametrize("width", [1366, 1280])
@pytest.mark.parametrize("tab", ["search", "applications"])
def test_tables_fit_a_laptop_screen(seeded, page, tab, width):
    page.set_viewport_size({"width": width, "height": 900})
    open_board(page, tab)
    expect(page.locator("tbody tr").first).to_be_visible()
    assert _fits(page) == {"page": True, "table": True}
    last = page.locator("thead th").last
    box = last.bounding_box()
    assert box and box["x"] + box["width"] <= width          # the last column is on screen
    if tab == "search":
        actions = row(page, "Mistral Pagos").get_by_role("button", name="Track", exact=True)
        expect(actions).to_be_in_viewport()


def test_narrow_screen_moves_secondary_columns_into_the_detail(seeded, page):
    page.set_viewport_size({"width": 1024, "height": 900})
    open_board(page)
    expect(page.locator("thead th", has_text="Published")).to_be_hidden()
    assert _fits(page)["table"]
    target = row(page, "Mistral Pagos")
    target.get_by_role("button", name=re.compile("Show details")).click()
    hidden = page.locator(".detail-cell .hidden-cols")
    expect(hidden.get_by_text("Published", exact=True)).to_be_visible()
    expect(hidden.get_by_text("Conditions", exact=True)).to_be_hidden()   # still in the row


def test_phone_shows_each_posting_as_a_card(seeded, page):
    page.set_viewport_size({"width": 390, "height": 900})
    open_board(page)
    expect(page.locator("thead")).to_be_hidden()
    assert _fits(page) == {"page": True, "table": True}
    card = row(page, "Mistral Pagos")
    expect(card.locator(".job-title")).to_be_visible()
    expect(card.locator("td.col-labelled")).to_be_visible()                # the salary
    expect(card.get_by_role("button", name="Track", exact=True)).to_be_visible()
    expect(card.locator("td", has_text="days ago")).to_be_hidden()        # published: detail
    card.get_by_role("button", name=re.compile("Show details")).click()
    hidden = page.locator(".detail-cell .hidden-cols")
    expect(hidden.get_by_text("Published", exact=True)).to_be_visible()


def test_compact_actions_have_names_and_are_reachable_by_keyboard(seeded, page):
    open_board(page)
    target = row(page, "Mistral Pagos")
    applied = target.get_by_role("button", name="Already applied: Track and mark applied")
    expect(applied).to_have_attribute("title", "Already applied: Track and mark applied")
    target.get_by_role("button", name="Track", exact=True).focus()
    page.keyboard.press("Tab")
    expect(applied).to_be_focused()
    page.keyboard.press("Tab")
    expect(target.get_by_role("button", name="Dismiss with a reason")).to_be_focused()


# ── salary as the agent's analysis (rework-salary-research) ──────────────

def test_salary_cell_shows_offered_and_the_suggestion_with_its_note(seeded, page):
    with db.session(seeded) as conn:
        posting = conn.execute("SELECT id FROM postings WHERE company = 'Mistral Pagos'"
                               " AND is_demo = 1").fetchone()["id"]
        offer = conn.execute(
            "SELECT a.job_id FROM applications a JOIN postings p ON p.id = a.posting_id"
            " WHERE a.offered_salary_amount IS NOT NULL").fetchone()["job_id"]
        currency = conn.execute("SELECT offered_salary_currency FROM applications"
                                " WHERE job_id = ?", (offer,)).fetchone()[0]
        conn.execute("UPDATE postings SET published_salary = ? WHERE id = ?",
                     (json.dumps({"min": 9000, "max": 11000, "currency": currency,
                                  "period": "month"}), posting))
        salary.set_suggestion(conn, posting, {
            "criteria": {"currency": currency}, "range_min": 10000, "range_max": 12000,
            "inputs": [{"kind": "offer", "application": offer}],
            "note": "Close to what a similar company offered you."})
    open_board(page)
    cell = row(page, "Mistral Pagos").locator("td.col-labelled")
    expect(cell).to_contain_text("Offered")
    expect(cell).to_contain_text("1 your history")
    expect(cell.locator("[title='Close to what a similar company offered you.']")).to_have_count(1)
    row(page, "Mistral Pagos").get_by_role("button", name=re.compile("Show details")).click()
    detail = page.locator(".detail")
    expect(detail.locator(".salary-note")).to_contain_text("Close to what a similar company")
    expect(detail).to_contain_text(f"({offer})")
