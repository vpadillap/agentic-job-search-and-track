"""The Profile & agent board and earlier-season views in a real browser
(profile-agent-board, seasons). Fictional persona only. Skipped when Chromium for
Playwright is not installed."""
# ruff: noqa: F811  (pytest fixtures imported from other test modules)
from __future__ import annotations

import re

import pytest

from jobtracker.core import config, db, learning, profile, rules, search, seasons, skills
from tests.test_applications import jobs  # noqa: F401  (fixture)
from tests.test_browser import browser, open_board, page, server  # noqa: F401

playwright_api = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.browser
expect = playwright_api.expect


def card(page, heading):
    return page.locator(".pa-card, .pa-season").filter(
        has=page.get_by_role("heading", name=re.compile(heading)))


# ── season summary ────────────────────────────────────────────────────────

def test_season_card_and_earlier_season(jobs, page):
    home = jobs["home"]
    with db.session(home) as conn:
        from jobtracker.core import applications

        applications.set_status(conn, [jobs["altamar"]], "applied")
        seasons.start(conn, learning="keep", leave_open=True)
    open_board(page, "profile")
    season = page.locator(".pa-season")
    expect(season.get_by_role("heading", name=re.compile(r"^Season 2 · since"))).to_be_visible()
    expect(season.locator(".command-box code")).to_have_text("/new-season")
    season.get_by_role("button", name="View season 1 (archived)").click()

    expect(page).to_have_url(re.compile("#applications$"))
    expect(page.locator(".season-banner")).to_contain_text("viewing season 1 (archived)")
    expect(page.locator(".header-chip").first).to_have_text("Viewing season 1 (archived)")
    row = page.locator("tbody tr").filter(has_text=jobs["altamar"])
    expect(row).to_be_visible()
    # A late reply: the status still changes.
    row.locator(".status-button").click()
    page.get_by_role("radio", name="Interview").click()
    expect(row.locator(".status-button")).to_contain_text("Interview")
    expect(row.locator(".add-chip")).to_have_count(0)            # nothing else is editable
    page.get_by_role("button", name="Back to the current season").click()
    expect(page.locator(".season-banner")).to_have_count(0)
    expect(page.get_by_role("heading", name=re.compile("No applications|nothing tracked", re.I))
           .or_(page.locator(".empty"))).to_be_visible()


def test_no_earlier_season_offers_no_link(searchable, page):
    open_board(page, "profile")
    expect(page.locator(".pa-season")).to_be_visible()
    expect(page.locator(".pa-season-link")).to_have_count(0)


# ── profile ───────────────────────────────────────────────────────────────

def test_profile_titles_by_state_and_including_a_suggestion(searchable, page):
    with db.session(searchable) as conn:
        profile.set_title_state(conn, "Data Platform Engineer", "under_review")
    open_board(page, "profile")
    profile_card = card(page, r"^Profile v\d+")
    expect(profile_card.locator(".pa-title.under_review")).to_contain_text(
        "Data Platform Engineer · review")
    expect(profile_card.locator(".pa-title.excluded s")).to_have_text("ETL Developer")
    profile_card.get_by_role("button", name="Data Architect").click()
    page.get_by_role("button", name="Include", exact=True).click()
    expect(profile_card.locator(".pa-title.included", has_text="Data Architect")).to_be_visible()
    with db.session(searchable) as conn:
        assert "Data Architect" in profile.included_titles(profile.get_active(conn))
        run = search.start_run(conn, searchable)
    assert "Data Architect" in run["titles"]


def test_profile_is_read_only_and_says_how_to_change_it(searchable, page):
    open_board(page, "profile")
    profile_card = card(page, r"^Profile v\d+")
    expect(profile_card.get_by_text("Work mode", exact=True)).to_be_visible()
    expect(profile_card).to_contain_text("tell the agent in Claude Code")
    expect(profile_card.locator("input, textarea, select")).to_have_count(0)


# ── pending work and commands ─────────────────────────────────────────────

def test_nothing_pending(searchable, page):
    open_board(page, "profile")
    expect(card(page, "^Pending for the agent")).to_contain_text("Nothing is pending.")


def test_pending_items_with_the_batch_command(jobs, page):
    open_board(page, "profile")
    pending = card(page, "^Pending for the agent")
    expect(pending.locator(".pa-item").first).to_contain_text("Tailored resume missing")
    expect(pending.locator(".command-box code")).to_have_text("/prepare-documents pending")


def test_spanish_panel_lists_spanish_commands(searchable, page):
    config.set_value(searchable.config, "language", "es")
    skills.sync("es")
    open_board(page, "profile")
    commands = card(page, "^Comandos en Claude Code")
    expect(commands.locator("code", has_text="/nueva-temporada")).to_be_visible()
    expect(commands.locator("code", has_text="/buscar-empleos dias=7")).to_be_visible()
    expect(commands.locator("code", has_text="/new-season")).to_have_count(0)
    expect(commands).to_contain_text("Perfil nuevo; archiva lo anterior")


# ── agent memory ──────────────────────────────────────────────────────────

def test_memory_lists_rules_with_origin_and_date(searchable, page):
    with db.session(searchable) as conn:
        rules.add_rules(conn, [{"origin": "user", "area": "search",
                                "text": "Skip outsourcing consultancies"}])
        lesson = rules.add_rules(conn, [{"origin": "learned", "area": "salary",
                                         "text": "Ask at most 8% over the median",
                                         "evidence": "6 cases"}])[0]
        learning.apply(conn, lesson["id"])
    open_board(page, "profile")
    memory = card(page, "^Agent memory")
    date = re.compile(r"· [A-Z][a-z]{2} \d{1,2}")
    system = memory.locator(".pa-rule").filter(has_text="never submits applications")
    expect(system.locator(".pa-origin")).to_have_text(re.compile(r"^System rule " + date.pattern))
    user = memory.locator(".pa-rule").filter(has_text="Skip outsourcing consultancies")
    expect(user.locator(".pa-origin")).to_have_text(re.compile(r"^You asked " + date.pattern))
    learned = memory.locator(".pa-rule").filter(has_text="Ask at most 8% over the median")
    expect(learned.locator(".pa-origin.learned")).to_have_text(
        re.compile(r"^Learned · applied [A-Z][a-z]{2} \d{1,2}"))
    expect(memory).to_contain_text("To add or change a rule, tell the agent")


# ── providers ─────────────────────────────────────────────────────────────

def test_provider_needing_presence_says_so(searchable, page):
    open_board(page, "profile")
    gamma = card(page, "^Job sites").locator(".pa-provider").filter(has_text="Gamma")
    expect(gamma.locator(".pa-status")).to_have_text("Needs you present (live walk)")
    expect(gamma).to_contain_text("gamma.md")


def test_disabling_a_provider(searchable, page):
    open_board(page, "profile")
    alpha = card(page, "^Job sites").locator(".pa-provider").filter(has_text="Alpha")
    switch = alpha.get_by_role("switch", name="Use Alpha")
    expect(switch).to_have_attribute("aria-checked", "true")
    switch.click()
    expect(switch).to_have_attribute("aria-checked", "false")
    expect(alpha.locator(".pa-status")).to_have_text(
        re.compile(r"^Disabled by you · [A-Z][a-z]{2} \d{1,2}$"))
    with db.session(searchable) as conn:
        run = search.start_run(conn, searchable)
    assert "alpha" not in run["to_search"]
