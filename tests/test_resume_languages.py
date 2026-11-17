"""Base resumes per language (profile) and tailoring from the matching one."""
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
    """English and Spanish base resumes; English imported first."""
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
    assert base["en"]["main"] is True and base["es"]["main"] is False
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


def test_choosing_the_main_resume(two, cli):
    code, out, _ = cli("resume", "main", "es")
    assert code == 0 and out["resume"]["language"] == "es"
    base = current_by_language(cli)
    assert base["es"]["main"] is True and base["en"]["main"] is False
    _, context, _ = cli("context")
    assert context["base_resume"]["language"] == "es"
    code, out, _ = cli("resume", "main", "pt")
    assert code == 1 and out["error"]["code"] == "not_found"


def test_rescoring_only_for_the_main_resume(two, cli, tmp_path):
    code, out, _ = cli("resume", "import", str(make_spanish_docx(tmp_path / "es2.docx")),
                       "--language", "es")
    assert out["resume"]["rescore_needed"] is False
    _, context, _ = cli("context")
    assert context["rescore_since"] is None
    _, out, _ = cli("resume", "import", str(make_formatted_docx(tmp_path / "en2.docx")),
                    "--language", "en")
    assert out["resume"]["rescore_needed"] is True and out["resume"]["main"] is True


def test_language_codes_are_checked(workspace, cli, tmp_path):
    code, out, _ = cli("resume", "import", str(make_formatted_docx(tmp_path / "cv.docx")),
                       "--language", "English")
    assert code == 1 and out["error"]["code"] == "invalid_language"
    code, out, _ = cli("resume", "import", str(make_formatted_docx(tmp_path / "cv.docx")))
    assert code == 2 and out["error"]["code"] == "usage"  # the language is required


def test_existing_workspace_resume_without_a_language(workspace, cli, tmp_path):
    with db.session(workspace) as conn:  # how resumes were imported before this change
        resume.import_resume(conn, workspace, make_formatted_docx(tmp_path / "old.docx"))
    old_file = workspace.profile / "resume-base.docx"
    old_bytes = old_file.read_bytes()
    _, context, _ = cli("context")
    assert context["base_resume"]["language"] is None and context["base_resume"]["main"]

    code, out, _ = cli("resume", "import", str(make_spanish_docx(tmp_path / "es.docx")),
                       "--language", "es")
    assert code == 1 and out["error"]["code"] == "language_unknown"
    assert not (workspace.profile / "resume-base-es.docx").exists()

    code, out, _ = cli("resume", "language", "en")
    assert code == 0 and out["resume"]["language"] == "en" and out["resume"]["main"]
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


def test_migration_makes_the_existing_resume_the_main_one(workspace, tmp_path, monkeypatch):
    with closing(sqlite3.connect(workspace.database)) as conn:
        conn.execute("PRAGMA user_version = 7")
        conn.execute("DROP INDEX base_resumes_one_current_per_language")
        conn.execute("DROP INDEX base_resumes_one_main")
        for column in ("language", "is_main"):
            conn.execute(f"ALTER TABLE base_resumes DROP COLUMN {column}")
        conn.execute("ALTER TABLE documents DROP COLUMN base_resume_id")
        conn.execute("CREATE UNIQUE INDEX base_resumes_one_current ON base_resumes (is_current)"
                     " WHERE is_current = 1")
        conn.execute(
            "INSERT INTO base_resumes (version, file_name, text_name, original_name, characters,"
            " text_source, imported_at, is_current)"
            " VALUES (1, 'resume-base.docx', 'resume-base.md', 'cv.docx', 900, 'extracted',"
            " '2026-10-01T00:00:00Z', 1)")
        conn.commit()
    with db.session(workspace) as conn:
        row = conn.execute("SELECT language, is_main, is_current FROM base_resumes").fetchone()
    assert (row["language"], row["is_main"], row["is_current"]) == (None, 1, 1)


# ── tailoring from the matching language ──────────────────────────────────

@pytest.fixture
def tailorable(jobs, cli, tmp_path):  # noqa: F811
    """Tracked applications plus English (main) and Spanish base resumes."""
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


def test_tailoring_starts_from_the_resume_in_the_postings_language(tailorable, send, cli):
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


def test_without_a_matching_resume_the_main_one_is_translated(tailorable, send):
    job = tailorable["altamar"]
    set_posting_language(tailorable["home"], job, "pt")
    _, out, _ = send({"edits": [{"find": "Mentored two", "replace": "Mentored 2"}]},
                     "documents", "tailor", job, "-")
    assert out["base"] == {"language": "en", "version": 1, "main": True}
    assert out["translate"] is True
    _, registered, _ = register(send, job, out["file_name"])
    assert registered["document"]["base_resume"]["language"] == "en"


def test_unknown_posting_language_uses_the_main_resume(tailorable, send):
    job = tailorable["altamar"]
    set_posting_language(tailorable["home"], job, None)
    _, out, _ = send({"edits": [{"find": "Mentored two", "replace": "Mentored 2"}]},
                     "documents", "tailor", job, "-")
    assert out["base"]["language"] == "en" and out["translate"] is None


def test_choosing_another_base_explicitly(tailorable, send):
    job = tailorable["altamar"]
    set_posting_language(tailorable["home"], job, "es")
    _, out, _ = send({"edits": [{"find": "Mentored two", "replace": "Mentored 2"}]},
                     "documents", "tailor", job, "-", "--base", "en")
    assert out["base"]["language"] == "en" and out["translate"] is True
    code, out, _ = send({"edits": [{"find": "x", "replace": "y"}]},
                        "documents", "tailor", job, "-", "--base", "fr")
    assert code == 1 and out["error"]["code"] == "not_found"


def test_comparison_uses_the_base_it_came_from(tailorable, send, cli):
    job = tailorable["altamar"]
    set_posting_language(tailorable["home"], job, "es")
    _, out, _ = send({"edits": [{"find": "Mentoría a dos", "replace": "Mentoría a 2"}]},
                     "documents", "tailor", job, "-")
    register(send, job, out["file_name"], base="es")
    code, diff, _ = cli("documents", "diff", job)
    assert code == 0, diff
    assert diff["base_resume"]["language"] == "es"
    assert diff["stats"] == {**diff["stats"], "added": 1, "removed": 1}
    assert diff["hunks"][0]["base"] == ["Mentoría a dos ingenieros junior."]


def test_cover_letters_have_no_base(tailorable, send, cli):
    job = tailorable["altamar"]
    _, path, _ = cli("documents", "path", job, "--kind", "cover-letter", "--ext", "md")
    Path(path["path"]).write_text("Estimado equipo:\nCarta ficticia.", encoding="utf-8")
    code, out, _ = send({"language": "es", "base": "es"}, "documents", "register", job,
                        "cover-letter", path["file_name"], "-")
    assert code == 1 and out["error"]["details"]["field"] == "base"
