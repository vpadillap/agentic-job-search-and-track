"""The panel in a real browser, against the demo seed (panel-shell, search-results-board).

Needs Chromium for Playwright: `python -m playwright install chromium`. Skipped
when it is not installed.
"""
from __future__ import annotations

import re
import socket
import threading
import time
from datetime import datetime

import pytest

from jobtracker.core import db, demo, search

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


def test_tabs_have_counters_and_placeholders(seeded, page):
    open_board(page)
    expect(page.locator(".tab", has_text="Search").locator(".count")).to_have_text("8")
    expect(page.locator(".tab", has_text="Applications").locator(".count")).to_have_text("2")
    page.get_by_role("link", name="Learning").click()
    expect(page.get_by_role("heading", name=re.compile("coming in a later update"))).to_be_visible()


def test_switching_language_without_reload_and_it_persists(seeded, page):
    open_board(page)
    page.evaluate("window.__marker = 1")
    page.get_by_role("button", name="ES", exact=True).click()
    expect(page.get_by_role("heading", name="Última búsqueda")).to_be_visible()
    assert page.evaluate("window.__marker") == 1                     # no reload
    page.get_by_role("button", name="EN", exact=True).click()
    expect(page.get_by_role("heading", name="Latest search")).to_be_visible()
    expect(page.locator(".tab", has_text="Applications")).to_be_visible()
    page.evaluate("localStorage.clear()")
    page.reload()                                                      # a restart reads config
    expect(page.get_by_role("heading", name="Latest search")).to_be_visible()
    page.get_by_role("button", name="ES", exact=True).click()
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
    expect(page.get_by_role("link", name=re.compile("pending for the agent"))).to_be_visible()


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
    expect(page.locator(".tab", has_text="Applications").locator(".count")).to_have_text("3")
    assert row(page, "Mistral Pagos").locator("a.tracked").get_attribute("href") == "#applications"


def test_track_and_mark_applied(seeded, page):
    open_board(page)
    row(page, "Quena Labs").get_by_role("button", name="Track and mark applied").click()
    expect(row(page, "Quena Labs").locator("a.tracked")).to_have_text(re.compile("Applied"))
    with db.session(seeded) as conn:
        status, applied_on = conn.execute(
            "SELECT a.status, a.applied_on FROM applications a JOIN postings p"
            " ON p.id = a.posting_id WHERE p.company = 'Quena Labs'").fetchone()
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
