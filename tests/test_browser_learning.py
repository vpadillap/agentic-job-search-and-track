"""The Learning board in a real browser, against the fictional history at each level
(learning-board). Skipped when Chromium for Playwright is not installed."""
from __future__ import annotations

import re

import pytest

from jobtracker.core import db, demo, insights, learning
from tests.test_browser import browser, open_board, page, server  # noqa: F401

playwright_api = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.browser
expect = playwright_api.expect


def seed(home, level):
    demo.seed(home, learning=level)
    return home


def test_empty_board_explains_what_will_appear(workspace, page):  # noqa: F811
    open_board(page, "learning")
    expect(page.get_by_role("heading", name="Learning level: Collecting")).to_be_visible()
    expect(page.get_by_role("heading", name="Your results will appear here")).to_be_visible()
    expect(page.get_by_text("outcomes come in")).to_be_visible()


def test_collecting_level_shows_what_is_needed(home, page):  # noqa: F811
    seed(home, "collecting")
    open_board(page, "learning")
    expect(page.get_by_role("heading", name="Learning level: Collecting")).to_be_visible()
    expect(page.get_by_text(re.compile(r"Next level needs: \d+ more applications? with an outcome"))
           ).to_be_visible()
    expect(page.get_by_text("Breakdowns appear once 15 applications have an outcome.")
           ).to_be_visible()
    expect(page.locator(".breakdown")).to_have_count(0)
    expect(page.get_by_text(re.compile(r"Fit to you needs \d+ more"))).to_be_visible()


def test_descriptive_level_breakdowns_and_period(home, page):  # noqa: F811
    seed(home, "descriptive")
    open_board(page, "learning")
    expect(page.get_by_role("heading", name="Learning level: Descriptive")).to_be_visible()
    for dimension in ("score_band", "resume_kind", "channel", "salary_delta"):
        expect(page.locator(f'.breakdown[data-dimension="{dimension}"]')).to_be_visible()
    subtitle = page.locator(".learn-title p")
    with db.session(home) as conn:
        counts = {p: insights.summary(conn, p)["applied"] for p in ("all", "30")}
    assert counts["30"] < counts["all"]
    page.get_by_role("button", name="All history").click()
    expect(subtitle).to_contain_text(f"{counts['all']} applications in total")
    page.get_by_role("button", name="30 days", exact=True).click()
    expect(subtitle).to_contain_text(f"{counts['30']} applications in the last 30 days")
    # Nothing above the level: no estimates, track record, or recommendations.
    expect(page.locator(".track-record")).to_have_count(0)
    expect(page.locator(".recommendations")).to_have_count(0)
    open_board(page, "search")
    expect(page.locator(".results")).to_be_visible()
    expect(page.locator(".results .confidence")).to_have_count(0)


def test_predictive_level_shows_estimates_but_no_recommendations(home, page):  # noqa: F811
    seed(home, "predictive")
    open_board(page, "learning")
    expect(page.get_by_role("heading", name="Learning level: Predictive")).to_be_visible()
    expect(page.get_by_role("heading", name="How good the estimates have been")).to_be_visible()
    expect(page.locator(".recommendations")).to_have_count(0)
    open_board(page, "search")
    first = page.locator(".results tbody tr").first.locator(".chance-fit")
    expect(first.locator(".confidence")).to_have_text(re.compile(r"^\d+%$"))
    expect(first.locator(".fit-text")).to_have_text(re.compile(r"^fit (low|medium|high)$"))


def test_prescriptive_level_shows_recommendations(home, page):  # noqa: F811
    seed(home, "prescriptive")
    open_board(page, "learning")
    expect(page.get_by_role("heading", name="Learning level: Prescriptive")).to_be_visible()
    expect(page.get_by_role("heading", name="Apply next")).to_be_visible()
    expect(page.get_by_text("correlation, not proof", exact=False)).to_be_visible()
    open_board(page, "applications")
    expect(page.locator("table .confidence").first).to_have_text(re.compile(r"^\d+%$"))


def test_applying_and_reverting_a_lesson(home, page):  # noqa: F811
    seed(home, "descriptive")
    with db.session(home) as conn:
        learning.propose(conn, [{"text": "Follow up after 9 days.",
                                 "evidence": "12 responses (demo).",
                                 "candidate_key": "timing:demo", "cases": 12, "area": "general",
                                 "effect": {"follow_up_after_days": 9}}])
    open_board(page, "learning")
    lesson = page.locator(".lesson", has_text="Follow up after 9 days.")
    expect(lesson.get_by_text("12 responses (demo).")).to_be_visible()
    lesson.get_by_role("button", name="Apply").click()
    expect(lesson.get_by_text(re.compile(r"^Applied "))).to_be_visible()
    expect(page.locator(".toast")).to_contain_text("Lesson applied.")
    lesson.get_by_role("button", name="Revert").click()
    expect(page.locator(".lesson", has_text="Follow up after 9 days.")).to_have_count(0)


def test_deeper_review_is_suggested_after_ten_outcomes(home, page):  # noqa: F811
    seed(home, "predictive")
    with db.session(home) as conn:
        conn.execute("UPDATE analyses SET resolved = resolved - 12")
    open_board(page, "learning")
    expect(page.get_by_text(re.compile(r"12 applications got an outcome since the last deeper"))
           ).to_be_visible()
    expect(page.locator(".level-review code")).to_have_text("/analyze-results")


def test_offers_card_compares_offered_with_asked(home, page):  # noqa: F811
    seed(home, "predictive")
    with db.session(home) as conn:
        compared = insights.summary(conn, "all")["offered_salary"]["vs_asked"]
    assert compared["cases"] > 0
    open_board(page, "learning")
    page.get_by_role("button", name="All history").click()
    note = page.locator('.kpi[data-kpi="offers"] .kpi-note')
    expect(note).to_contain_text("Offered vs asked:")
    expect(note).to_contain_text(f"{compared['median_pct']}%")
