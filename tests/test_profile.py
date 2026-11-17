"""Scenarios of the `profile` spec and of resume intake."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from tests.helpers import RESUME_TEXT, make_docx, make_image_only_pdf, make_text_pdf

PERSONA = json.loads(
    (Path(__file__).parent / "fixtures" / "persona.json").read_text(encoding="utf-8")
)


@pytest.fixture
def send(cli, monkeypatch):
    """Run a CLI command with a JSON document on standard input."""

    def run(payload: object, *args: str):
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        return cli(*args)

    return run


@pytest.fixture
def profiled(workspace, send):
    needs = {**PERSONA["job_needs"]}
    needs["minimum_salary"] = {k: v for k, v in needs["minimum_salary"].items() if k != "period"}
    code, out, _ = send({**needs, "titles": PERSONA["target_titles"]}, "profile", "set", "-")
    assert code == 0, out
    return workspace


# ── versions ──────────────────────────────────────────────────────────────

def test_first_profile_is_version_one(profiled, cli):
    _, out, _ = cli("profile", "show")
    profile = out["profile"]
    assert profile["version"] == 1 and profile["active"] is True
    assert profile["work_modes"] == ["remote", "hybrid"]
    assert profile["contract_types"] == ["full-time", "contractor"]
    assert profile["minimum_salary"] == {
        "amount": 11000, "currency": "PEN", "period": "month", "basis": "gross"}
    assert profile["posting_age_days"] == 7


def test_changing_a_job_need_creates_a_new_version(profiled, send, cli):
    code, out, _ = send({"work_modes": ["remote"]}, "profile", "set", "-")
    assert code == 0
    assert out["profile"]["version"] == 2
    assert out["profile"]["work_modes"] == ["remote"]
    assert out["profile"]["contract_types"] == ["full-time", "contractor"]  # untouched

    _, old, _ = cli("profile", "show", "--version", "1")
    assert old["profile"]["work_modes"] == ["remote", "hybrid"]
    assert old["profile"]["active"] is False

    _, history, _ = cli("profile", "history")
    assert [(v["version"], v["active"]) for v in history["versions"]] == [(1, False), (2, True)]


def test_identical_update_does_not_create_a_version(profiled, send):
    _, out, _ = send({"work_modes": ["remote", "hybrid"]}, "profile", "set", "-")
    assert out["profile"]["version"] == 1


def test_optional_answers_are_not_invented(workspace, send):
    _, out, _ = send({"work_modes": ["remote"], "contract_types": ["full-time"]},
                     "profile", "set", "-")
    profile = out["profile"]
    assert profile["minimum_salary"] is None
    assert profile["country"] is None
    assert profile["seniority"] is None
    assert profile["locations"] == []


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"work_modes": ["remote", "office"]}, "work_modes"),
        ({"contract_types": "full-time"}, "contract_types"),
        ({"country": "Peru"}, "country"),
        ({"minimum_salary": {"amount": 11000.5, "currency": "PEN"}}, "minimum_salary"),
        ({"minimum_salary": {"amount": 11000, "currency": "soles"}}, "minimum_salary"),
        ({"posting_age_days": 0}, "posting_age_days"),
        ({"titles": [{"title": "Data Engineer"}, {"title": "data engineer"}]}, "titles"),
        ({"titles": [{"title": "Data Engineer", "state": "maybe"}]}, "titles"),
        ({"favourite_colour": "blue"}, "favourite_colour"),
    ],
)
def test_invalid_profile_is_rejected_and_nothing_is_stored(profiled, send, cli, changes, field):
    code, out, _ = send(changes, "profile", "set", "-")
    assert code == 1
    assert out["error"]["code"] == "invalid_profile"
    assert out["error"]["details"]["field"] == field
    _, shown, _ = cli("profile", "show")
    assert shown["profile"]["version"] == 1


# ── titles ────────────────────────────────────────────────────────────────

def _states(profile: dict) -> dict[str, str]:
    return {item["title"]: item["state"] for item in profile["titles"]}


def test_accepting_and_rejecting_proposals(profiled, cli):
    for title in ("Analytics Engineer", "BI Engineer", "MLOps Engineer"):
        cli("profile", "title", title, "suggested", "--reason", "seen in current postings")
    cli("profile", "title", "Analytics Engineer", "included")
    _, out, _ = cli("profile", "title", "bi engineer", "excluded")  # case-insensitive match

    states = _states(out["profile"])
    assert states["Analytics Engineer"] == "included"
    assert states["BI Engineer"] == "excluded"
    assert states["MLOps Engineer"] == "suggested"
    assert len([t for t in states if t.casefold() == "bi engineer"]) == 1


def test_excluding_an_included_title_is_a_new_version(profiled, cli):
    _, out, _ = cli("profile", "title", "Senior Data Engineer", "excluded")
    assert out["profile"]["version"] == 2
    assert _states(out["profile"])["Senior Data Engineer"] == "excluded"
    _, context, _ = cli("context")
    included = [t["title"] for t in context["profile"]["titles"] if t["state"] == "included"]
    assert included == ["Data Platform Engineer"]


def test_setting_the_same_state_changes_nothing(profiled, cli):
    _, out, _ = cli("profile", "title", "Senior Data Engineer", "included")
    assert out["profile"]["version"] == 1


def test_title_needs_a_profile(workspace, cli):
    code, out, _ = cli("profile", "title", "Data Engineer", "included")
    assert code == 1 and out["error"]["code"] == "no_profile"


# ── base resume ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("maker", [make_docx, make_text_pdf], ids=["docx", "pdf"])
def test_readable_resume_is_stored_unchanged_with_its_text(workspace, cli, tmp_path, maker):
    extension = "docx" if maker is make_docx else "pdf"
    source = maker(tmp_path / f"My Resume.{extension}")
    code, out, _ = cli("resume", "import", str(source), "--language", "en")
    assert code == 0, out
    resume = out["resume"]
    stored = workspace.profile / f"resume-base-en.{extension}"
    assert Path(resume["path"]) == stored
    assert stored.read_bytes() == source.read_bytes()
    text = (workspace.profile / "resume-base-en.md").read_text(encoding="utf-8")
    assert "Senior Data Engineer" in text and "BigQuery" in text
    assert resume["version"] == 1 and resume["text_source"] == "extracted"
    assert resume["original_name"] == source.name
    assert resume["rescore_needed"] is False


def test_unreadable_resume_is_reported_and_nothing_is_stored(workspace, cli, tmp_path):
    source = make_image_only_pdf(tmp_path / "scan.pdf")
    code, out, _ = cli("resume", "import", str(source), "--language", "en")
    assert code == 1
    assert out["error"]["code"] == "no_text_extracted"
    assert "--text" in out["error"]["message"]
    assert list(workspace.profile.iterdir()) == []
    _, shown, _ = cli("resume", "show")
    assert shown["by_language"] == []


def test_visually_read_text_can_be_confirmed(workspace, cli, tmp_path):
    source = make_image_only_pdf(tmp_path / "scan.pdf")
    confirmed = tmp_path / "confirmed.md"
    confirmed.write_text(RESUME_TEXT, encoding="utf-8")
    code, out, _ = cli("resume", "import", str(source), "--language", "en", "--text",
                       str(confirmed))
    assert code == 0
    assert out["resume"]["text_source"] == "provided"
    assert "Airflow" in (workspace.profile / "resume-base-en.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["resume.odt", "resume.png", "resume"])
def test_unsupported_file_types_are_rejected(workspace, cli, tmp_path, name):
    source = tmp_path / name
    source.write_text("x", encoding="utf-8")
    code, out, _ = cli("resume", "import", str(source), "--language", "en")
    assert code == 1 and out["error"]["code"] == "unsupported_resume"


def test_corrupt_documents_are_rejected(workspace, cli, tmp_path):
    for name in ("broken.docx", "broken.pdf"):
        source = tmp_path / name
        source.write_bytes(b"this is not a real document")
        code, out, _ = cli("resume", "import", str(source), "--language", "en")
        assert code == 1 and out["error"]["code"] == "unreadable_resume", name
    assert list(workspace.profile.iterdir()) == []


def test_updated_base_resume_keeps_the_previous_one_and_asks_for_rescoring(
        workspace, cli, tmp_path):
    first = make_docx(tmp_path / "first.docx")
    second = make_text_pdf(tmp_path / "second.pdf", RESUME_TEXT + "\nKafka\n")
    cli("resume", "import", str(first), "--language", "en")
    _, context, _ = cli("context")
    assert context["rescore_since"] is None

    code, out, _ = cli("resume", "import", str(second), "--language", "en")
    assert code == 0
    assert out["resume"]["version"] == 2
    assert out["resume"]["replaced_version"] == 1
    assert out["resume"]["rescore_needed"] is True

    profile_dir = workspace.profile
    assert (profile_dir / "resume-base-en-v1.docx").read_bytes() == first.read_bytes()
    assert "Kafka" not in (profile_dir / "resume-base-en-v1.md").read_text(encoding="utf-8")
    assert (profile_dir / "resume-base-en.pdf").is_file()
    assert "Kafka" in (profile_dir / "resume-base-en.md").read_text(encoding="utf-8")
    assert not (profile_dir / "resume-base-en.docx").exists()

    _, context, _ = cli("context")
    assert context["rescore_since"] is not None
    assert [r["version"] for r in context["base_resumes"]] == [2]


def test_reimporting_the_current_base_resume_does_not_lose_it(workspace, cli, tmp_path):
    cli("resume", "import", str(make_docx(tmp_path / "cv.docx")), "--language", "en")
    current = workspace.profile / "resume-base-en.docx"
    original = current.read_bytes()
    code, _, _ = cli("resume", "import", str(current), "--language", "en")
    assert code == 0
    assert current.read_bytes() == original
    assert (workspace.profile / "resume-base-en-v1.docx").read_bytes() == original


def test_profile_exposes_resume_and_titles(profiled, cli, tmp_path):
    cli("resume", "import", str(make_docx(tmp_path / "cv.docx")), "--language", "en")
    _, out, _ = cli("profile", "show")
    profile = out["profile"]
    assert profile["version"] == 1
    assert [r["file_name"] for r in profile["base_resumes"]] == ["resume-base-en.docx"]
    assert {t["state"] for t in profile["titles"]} == {"included", "excluded", "suggested"}
    _, resume, _ = cli("resume", "show")
    assert Path(resume["by_language"][0]["path"]).is_file()
