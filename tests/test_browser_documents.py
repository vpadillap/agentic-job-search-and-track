"""Documents and form answers in the panel (document-preparation, form-answers, pending-work).

Needs Chromium for Playwright: `python -m playwright install chromium`.
"""
from __future__ import annotations

import re

import pytest

from jobtracker.core import answers, db, documents, docx_tools, resume
from tests.test_browser import (  # noqa: F401  (fixtures)
    app_row,
    browser,
    expect,
    open_board,
    page,
    seeded,
    server,
)
from tests.test_documents import EDITS, SUMMARY, make_formatted_docx

pytestmark = pytest.mark.browser
COMPANY = "Quipu Analytics"


def _job(conn, company: str) -> str:
    return conn.execute("SELECT a.job_id FROM applications a JOIN postings p"
                        " ON p.id = a.posting_id WHERE p.company = ?", (company,)).fetchone()[0]


@pytest.fixture
def prepared(seeded, tmp_path):  # noqa: F811
    """Quipu Analytics with a tailored resume and proposed answers, one left for the user."""
    home = seeded
    with db.session(home) as conn:
        resume.import_resume(conn, home, make_formatted_docx(tmp_path / "base.docx"))
        job = _job(conn, COMPANY)
        target = documents.next_path(conn, home, job, "resume-proposed", "docx")
    docx_tools.tailor(home.profile / "resume-base.docx", target, EDITS)
    with db.session(home) as conn:
        documents.register(conn, home, job, "resume-proposed", target.name, {
            "language": "es", "summary": SUMMARY,
            "support": [{"term": "BigQuery",
                         "source": "Modeled commercial and inventory data on BigQuery."}],
            "gaps": ["Kafka (deseable)"]})
        answers.propose(conn, job, [
            {"position": 1, "text": "Cinco años con Airflow en producción.", "language": "es"},
            {"position": 2, "text": "S/ 14,500 brutos mensuales.", "language": "es",
             "basis": "Basada en el salario sugerido"},
            {"position": 3, "text": "", "needs_user": True, "language": "es",
             "note": "Tu CV no indica disponibilidad."},
        ])
    return {"home": home, "job": job}


def open_detail(page, company=COMPANY):  # noqa: F811
    open_board(page, "applications")
    app_row(page, company).get_by_role("button", name=re.compile("Show details")).click()
    return page.locator(".detail")


def test_document_states_in_the_table(prepared, page):  # noqa: F811
    open_board(page, "applications")
    lines = app_row(page, COMPANY).locator(".doc-line")
    expect(lines.nth(0)).to_have_text("Tailored resume ready")
    expect(lines.nth(1)).to_have_text("Cover letter not decided")
    expect(lines.nth(2)).to_have_text("Form 2/3 · 1 needs you")


def test_proposed_resume_card_and_comparison(prepared, page):  # noqa: F811
    detail = open_detail(page)
    card = detail.locator(".doc-card").first
    expect(card).to_contain_text("resume-proposed-v1.docx")
    expect(card.locator(".doc-summary")).to_have_text(SUMMARY)
    expect(card).to_contain_text("From your main resume (v1)")
    expect(card.locator(".doc-gaps")).to_contain_text("Kafka (deseable)")
    card.get_by_text("1 emphasized term and where it comes from").click()
    expect(card.locator(".doc-support")).to_contain_text("BigQuery")
    card.get_by_role("button", name="View changes against base resume").click()
    diff = card.get_by_role("region", name="Changes against your base resume")
    expect(diff.locator(".diff-line.added").first).to_be_visible()
    expect(diff).to_contain_text("Data platform engineer with seven years")
    expect(diff.locator(".diff-line.removed", has_text="Data engineer with seven years")
           ).to_have_count(1)
    card.get_by_role("button", name="Hide changes").click()
    expect(diff).to_have_count(0)


def test_answers_show_origin_and_can_be_copied(prepared, page):  # noqa: F811
    detail = open_detail(page)
    qa = detail.locator(".qa")
    expect(qa).to_have_count(3)
    expect(qa.nth(0)).to_contain_text("Cinco años con Airflow en producción.")
    expect(qa.nth(0).locator(".answer-tag")).to_have_text("Proposed by the agent")
    expect(qa.nth(1).locator(".answer-tag.basis")).to_have_text("Basada en el salario sugerido")
    expect(qa.nth(2).locator(".answer-tag")).to_have_text("Needs your input")
    expect(qa.nth(2)).to_contain_text("Tu CV no indica disponibilidad.")
    qa.nth(0).get_by_role("button", name="Copy answer").click()
    copied = page.evaluate("navigator.clipboard.readText()")
    assert copied == "Cinco años con Airflow en producción."


def test_editing_an_answer_marks_it_as_yours_and_persists(prepared, page):  # noqa: F811
    detail = open_detail(page)
    qa = detail.locator(".qa").nth(2)
    qa.get_by_role("button", name="Write answer").click()
    qa.get_by_role("textbox", name="Your answer").fill("Dos semanas después de la oferta.")
    qa.get_by_role("button", name="Save").click()
    expect(qa.locator(".answer-tag")).to_have_text("Edited by you")
    expect(app_row(page, COMPANY).locator(".doc-line").nth(2)).to_have_text("Form 3/3")
    page.reload()
    detail = open_detail(page)
    expect(detail.locator(".qa").nth(2)).to_contain_text("Dos semanas después de la oferta.")


def test_regenerated_answer_is_offered_as_an_alternative(prepared, page):  # noqa: F811
    with db.session(prepared["home"]) as conn:
        answers.edit(conn, prepared["job"], 1, "Seis años, mi versión.")
        answers.propose(conn, prepared["job"], [
            {"position": 1, "text": "Cinco años (otra versión del agente).", "language": "es"}])
    detail = open_detail(page)
    qa = detail.locator(".qa").first
    expect(qa.locator(".qa-a").first).to_have_text("Seis años, mi versión.")
    qa.get_by_text("1 other version").click()
    qa.get_by_role("button", name="Use this version").click()
    expect(qa.locator(".qa-a").first).to_have_text("Cinco años (otra versión del agente).")
    expect(qa.locator(".answer-tag").first).to_have_text("Proposed by the agent")
    qa.get_by_text("1 other version").click()
    expect(qa.locator(".alternative")).to_contain_text("Seis años, mi versión.")


def test_header_lists_pending_items_with_the_batch_command(seeded, page):  # noqa: F811
    open_board(page)
    page.get_by_role("button", name=re.compile("5 pending for the agent")).click()
    region = page.get_by_role("region", name="Pending for the agent")
    items = region.locator("li")
    expect(items).to_have_count(5)
    expect(items.filter(has_text="Tailored resume missing")).to_have_count(2)
    expect(items.filter(has_text="3 form questions without an answer")).to_contain_text(COMPANY)
    expect(region.locator(".command-box code")).to_have_text("/prepare-documents pending")
    region.get_by_role("button", name="Copy command").click()
    assert page.evaluate("navigator.clipboard.readText()") == "/prepare-documents pending"
    page.keyboard.press("Escape")
    expect(region).to_have_count(0)


def test_header_list_in_spanish(seeded, page):  # noqa: F811
    open_board(page)
    page.get_by_role("button", name="ES", exact=True).click()
    page.get_by_role("button", name=re.compile("5 pendientes")).click()
    region = page.get_by_role("region", name="Pendiente para el agente")
    expect(region.locator("li").first).to_contain_text("Falta CV adaptado")
    page.get_by_role("button", name="EN", exact=True).click()
