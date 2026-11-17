"""Each base resume is the source for its own language: scoring, tailoring, drafts."""
from __future__ import annotations

import io
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import docx
import pytest

from jobtracker.core import db, resume
from tests.test_applications import jobs  # noqa: F401  (fixture)
from tests.test_documents import make_formatted_docx


def make_spanish_docx(path: Path) -> Path:
    """The fictional persona's resume, translated by hand."""
    document = docx.Document()
    headline = document.add_paragraph()
    headline.add_run("Marisol Quispe Tanaka").bold = True
    headline.add_run(" · Ingeniera de Datos Senior")
    for text in ("Resumen",
                 "Ingeniera de datos con siete años de experiencia construyendo pipelines en "
                 "Google Cloud para empresas de retail y logística.",
                 "Experiencia",
                 "Diseñé y mantuve pipelines de Airflow y dbt.",
                 "Modelé datos comerciales y de inventario en BigQuery.",
                 "Mentoría a dos ingenieros junior.",
                 "Idiomas: español (nativo), inglés (B2)"):
        document.add_paragraph(text)
    document.save(str(path))
    return path


@pytest.fixture
def send(cli, monkeypatch):
    def run(payload: object, *args: str):
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        return cli(*args)

    return run


@pytest.fixture
def two(workspace, cli, tmp_path):
    """English and Spanish base resumes."""
    en = make_formatted_docx(tmp_path / "cv-en.docx")
    es = make_spanish_docx(tmp_path / "cv-es.docx")
    assert cli("resume", "import", str(en), "--language", "en")[0] == 0
    assert cli("resume", "import", str(es), "--language", "es")[0] == 0
    return {"home": workspace, "en": en, "es": es}


def current_by_language(cli) -> dict[str, dict]:
    _, out, _ = cli("resume", "show")
    return {r["language"]: r for r in out["by_language"]}


# ── profile ───────────────────────────────────────────────────────────────

def test_second_language_keeps_the_first(two, cli):
    base = current_by_language(cli)
    assert set(base) == {"en", "es"}
    assert Path(base["en"]["path"]).read_bytes() == two["en"].read_bytes()
    assert Path(base["es"]["path"]).name == "resume-base-es.docx"
    assert "Ingeniera de datos" in Path(base["es"]["text_path"]).read_text(encoding="utf-8")


def test_new_version_of_one_language(two, cli, tmp_path):
    english_before = Path(current_by_language(cli)["en"]["path"]).read_bytes()
    newer = make_spanish_docx(tmp_path / "cv-es-2.docx")
    code, out, _ = cli("resume", "import", str(newer), "--language", "es")
    assert code == 0 and out["resume"]["replaced_version"] == 2
    profile = two["home"].profile
    assert (profile / "resume-base-es-v2.docx").read_bytes() == two["es"].read_bytes()
    assert Path(current_by_language(cli)["en"]["path"]).read_bytes() == english_before
    _, listed, _ = cli("resume", "list")
    assert [(r["language"], r["version"], r["current"]) for r in listed["resumes"]] == [
        ("en", 1, True), ("es", 3, True), ("es", 2, False)]


def test_there_is_no_main_resume(two, cli):
    code, out, _ = cli("resume", "main", "es")
    assert code == 2 and out["error"]["code"] == "usage"
    _, context, _ = cli("context")
    assert "base_resume" not in context
    assert {r["language"] for r in context["base_resumes"]} == {"en", "es"}
    assert all("main" not in r for r in context["base_resumes"])


def test_replacing_a_language_flags_rescoring(two, cli, tmp_path):
    code, out, _ = cli("resume", "import", str(make_spanish_docx(tmp_path / "es2.docx")),
                       "--language", "es")
    assert code == 0 and out["resume"]["rescore_needed"] is True


def test_language_codes_are_checked(workspace, cli, tmp_path):
    code, out, _ = cli("resume", "import", str(make_formatted_docx(tmp_path / "cv.docx")),
                       "--language", "English")
    assert code == 1 and out["error"]["code"] == "invalid_language"
    code, out, _ = cli("resume", "import", str(make_formatted_docx(tmp_path / "cv.docx")))
    assert code == 2 and out["error"]["code"] == "usage"  # the language is required


def test_existing_workspace_resume_without_a_language(workspace, cli, tmp_path):
    with db.session(workspace) as conn:  # how resumes were imported before languages
        resume.import_resume(conn, workspace, make_formatted_docx(tmp_path / "old.docx"))
    old_file = workspace.profile / "resume-base.docx"
    old_bytes = old_file.read_bytes()
    _, context, _ = cli("context")
    assert [r["language"] for r in context["base_resumes"]] == [None]
    with db.session(workspace) as conn:  # used for every posting while it is the only one
        assert resume.choose_row(conn, "pt")["file_name"] == "resume-base.docx"

    code, out, _ = cli("resume", "import", str(make_spanish_docx(tmp_path / "es.docx")),
                       "--language", "es")
    assert code == 1 and out["error"]["code"] == "language_unknown"
    assert not (workspace.profile / "resume-base-es.docx").exists()

    code, out, _ = cli("resume", "language", "en")
    assert code == 0 and out["resume"]["language"] == "en"
    assert old_file.read_bytes() == old_bytes  # files keep their names
    code, _, _ = cli("resume", "import", str(make_spanish_docx(tmp_path / "es.docx")),
                     "--language", "es")
    assert code == 0
    assert set(current_by_language(cli)) == {"en", "es"}
    code, out, _ = cli("resume", "language", "en")
    assert code == 1 and out["error"]["code"] == "not_found"


def test_stating_a_language_that_already_has_a_resume(workspace, cli, tmp_path):
    with db.session(workspace) as conn:
        resume.import_resume(conn, workspace, make_formatted_docx(tmp_path / "old.docx"))
        conn.execute("UPDATE base_resumes SET language = 'es'")  # pretend: es already exists
        resume.import_resume(conn, workspace, make_formatted_docx(tmp_path / "x.docx"))
    code, out, _ = cli("resume", "language", "es")
    assert code == 1 and out["error"]["code"] == "language_taken"


def test_migrations_keep_an_existing_resume(workspace):
    from tests.migrations import rewind

    rewind(workspace.database, 7)
    with closing(sqlite3.connect(workspace.database)) as conn:
        conn.execute(
            "INSERT INTO base_resumes (version, file_name, text_name, original_name, characters,"
            " text_source, imported_at, is_current)"
            " VALUES (1, 'resume-base.docx', 'resume-base.md', 'cv.docx', 900, 'extracted',"
            " '2026-10-01T00:00:00Z', 1)")
        conn.commit()
    with db.session(workspace) as conn:
        row = conn.execute("SELECT * FROM base_resumes").fetchone()
        columns = {r[1] for r in conn.execute("PRAGMA table_info(base_resumes)")}
    assert (row["language"], row["is_current"]) == (None, 1)
    assert "is_main" not in columns and "translated_from" in columns


# ── tailoring from the posting's language ─────────────────────────────────

@pytest.fixture
def tailorable(jobs, cli, tmp_path):  # noqa: F811
    """Tracked applications plus English and Spanish base resumes."""
    for maker, code in ((make_formatted_docx, "en"), (make_spanish_docx, "es")):
        assert cli("resume", "import", str(maker(tmp_path / f"cv-{code}.docx")),
                   "--language", code)[0] == 0
    return jobs


def set_posting_language(home, job_id: str, language: str | None) -> None:
    with db.session(home) as conn:
        conn.execute("UPDATE postings SET language = ? WHERE id = (SELECT posting_id"
                     " FROM applications WHERE job_id = ?)", (language, job_id))


def register(send, job, file_name, **extra):
    return send({"language": "es", "summary": "Resumen reorientado.", **extra},
                "documents", "register", job, "resume-proposed", file_name, "-")


EDIT_EN = {"edits": [{"find": "Mentored two", "replace": "Mentored 2"}]}


def test_tailoring_starts_from_the_resume_in_the_postings_language(tailorable, send):
    job = tailorable["altamar"]
    set_posting_language(tailorable["home"], job, "es")
    code, out, _ = send({"edits": [{"find": "Mentoría a dos", "replace": "Mentoría a 2"}]},
                        "documents", "tailor", job, "-")
    assert code == 0, out
    assert out["base"]["language"] == "es" and out["translate"] is False
    text = "\n".join(p.text for p in docx.Document(out["file"]).paragraphs)
    assert "Mentoría a 2 ingenieros junior." in text
    _, registered, _ = register(send, job, out["file_name"], base="es")
    assert registered["document"]["base_resume"]["language"] == "es"


def test_no_resume_in_the_postings_language(tailorable, send):
    job = tailorable["altamar"]
    set_posting_language(tailorable["home"], job, "pt")
    code, out, _ = send(EDIT_EN, "documents", "tailor", job, "-")
    assert code == 1 and out["error"]["code"] == "no_resume_for_language"
    assert out["error"]["details"]["language"] == "pt"
    assert not list(tailorable["home"].applications.rglob("resume-proposed-*"))


def test_unknown_posting_language_with_several_resumes(tailorable, send):
    job = tailorable["altamar"]
    set_posting_language(tailorable["home"], job, None)
    code, out, _ = send(EDIT_EN, "documents", "tailor", job, "-")
    assert code == 1 and out["error"]["code"] == "posting_language_unknown"
    code, out, _ = send(EDIT_EN, "documents", "tailor", job, "-", "--base", "en")
    assert code == 0 and out["base"] == {"language": "en", "version": 1}


def test_choosing_another_base_explicitly(tailorable, send):
    job = tailorable["altamar"]
    set_posting_language(tailorable["home"], job, "es")
    _, out, _ = send(EDIT_EN, "documents", "tailor", job, "-", "--base", "en")
    assert out["base"]["language"] == "en" and out["translate"] is True
    code, out, _ = send({"edits": [{"find": "x", "replace": "y"}]},
                        "documents", "tailor", job, "-", "--base", "fr")
    assert code == 1 and out["error"]["code"] == "no_resume_for_language"


def test_comparison_uses_the_base_it_came_from(tailorable, send, cli):
    job = tailorable["altamar"]
    set_posting_language(tailorable["home"], job, "es")
    _, out, _ = send({"edits": [{"find": "Mentoría a dos", "replace": "Mentoría a 2"}]},
                     "documents", "tailor", job, "-")
    register(send, job, out["file_name"], base="es")
    code, diff, _ = cli("documents", "diff", job)
    assert code == 0, diff
    assert diff["base_resume"]["language"] == "es"
    assert (diff["stats"]["added"], diff["stats"]["removed"]) == (1, 1)
    assert diff["hunks"][0]["base"] == ["Mentoría a dos ingenieros junior."]


def test_cover_letters_have_no_base(tailorable, send, cli):
    job = tailorable["altamar"]
    _, path, _ = cli("documents", "path", job, "--kind", "cover-letter", "--ext", "md")
    Path(path["path"]).write_text("Estimado equipo:\nCarta ficticia.", encoding="utf-8")
    code, out, _ = send({"language": "es", "base": "es"}, "documents", "register", job,
                        "cover-letter", path["file_name"], "-")
    assert code == 1 and out["error"]["details"]["field"] == "base"


# ── scoring against the posting's language ────────────────────────────────

def score(cli, tmp_path, posting_id):
    from tests.test_scoring import submission

    file = tmp_path / f"score-{posting_id}.json"
    file.write_text(json.dumps(submission()), encoding="utf-8")
    return cli("score", "set", str(posting_id), str(file))


def test_scores_record_the_resume_in_the_postings_language(tailorable, cli, tmp_path):
    home, postings = tailorable["home"], tailorable["postings"]
    spanish, english = postings["A-100"], postings["A-101"]
    with db.session(home) as conn:
        conn.execute("UPDATE postings SET language = 'es' WHERE id = ?", (spanish,))
        conn.execute("UPDATE postings SET language = 'en' WHERE id = ?", (english,))
    _, es_score, _ = score(cli, tmp_path, spanish)
    _, en_score, _ = score(cli, tmp_path, english)
    by_lang = current_by_language(cli)
    assert es_score["score"]["resume_ref"] == str(by_lang["es"]["version"])
    assert en_score["score"]["resume_ref"] == str(by_lang["en"]["version"])

    cli("resume", "import", str(make_spanish_docx(tmp_path / "es-new.docx")), "--language", "es")
    _, pending, _ = cli("pending")
    stale = {i["posting_id"] for i in pending["pending"] if i["kind"] == "rescore"}
    assert spanish in stale and english not in stale


def test_scoring_a_posting_in_a_language_without_resume(tailorable, cli, tmp_path):
    posting = tailorable["postings"]["A-100"]
    with db.session(tailorable["home"]) as conn:
        conn.execute("UPDATE postings SET language = 'pt' WHERE id = ?", (posting,))
        before = conn.execute("SELECT COUNT(*) FROM scores WHERE posting_id = ?",
                              (posting,)).fetchone()[0]
    code, out, _ = score(cli, tmp_path, posting)
    assert code == 1 and out["error"]["code"] == "no_resume_for_language"
    with db.session(tailorable["home"]) as conn:
        after = conn.execute("SELECT COUNT(*) FROM scores WHERE posting_id = ?",
                             (posting,)).fetchone()[0]
    assert after == before


# ── translated drafts ─────────────────────────────────────────────────────

def test_translated_draft_then_import(two, send, cli):
    english_before = Path(current_by_language(cli)["en"]["path"]).read_bytes()
    code, draft, _ = send({"edits": [
        {"find": "Senior Data Engineer", "replace": "Engenheira de Dados Sênior"},
        {"find": "Mentored two junior engineers.", "replace": "Mentoria de dois engenheiros."},
    ]}, "resume", "translate", "--from", "en", "--to", "pt", "-")
    assert code == 0, draft
    assert draft["file_name"] == "resume-draft-pt-v1.docx"
    assert draft["layout"]["same_shape"] is True
    headline = docx.Document(draft["file"]).paragraphs[0]
    assert headline.runs[0].bold is True and "Engenheira de Dados" in headline.text
    assert "pt" not in current_by_language(cli)  # a draft is not a base resume

    code, out, _ = cli("resume", "import", draft["file"], "--language", "pt",
                       "--translated-from", "en")
    assert code == 0 and out["resume"]["translated_from"] == "en"
    assert Path(current_by_language(cli)["en"]["path"]).read_bytes() == english_before
    _, listed, _ = cli("resume", "list")
    assert {r["language"]: r["translated_from"] for r in listed["resumes"]} == {
        "en": None, "es": None, "pt": "en"}


def test_translation_needs_a_source_and_a_different_language(two, send):
    code, out, _ = send({"edits": [{"find": "x", "replace": "y"}]},
                        "resume", "translate", "--from", "fr", "--to", "pt", "-")
    assert code == 1 and out["error"]["code"] == "no_resume_for_language"
    code, out, _ = send({"edits": [{"find": "x", "replace": "y"}]},
                        "resume", "translate", "--from", "en", "--to", "en", "-")
    assert code == 1 and out["error"]["code"] == "invalid_language"
