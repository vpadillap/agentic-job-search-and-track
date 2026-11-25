"""applications-board "Document access": download names and Word downloads."""
from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.parse import quote

import docx
import pytest
from fastapi.testclient import TestClient

from jobtracker.core import docx_tools
from jobtracker.web.app import create_app
from tests.helpers import make_docx
from tests.test_applications import jobs  # noqa: F401  (fixture)
from tests.test_documents import based  # noqa: F401  (fixture)

REPO = Path(__file__).resolve().parent.parent
PERSONA = json.loads((REPO / "tests" / "fixtures" / "persona.json").read_text(encoding="utf-8"))


@pytest.fixture
def client():
    return TestClient(create_app(), base_url="http://127.0.0.1:8000")


@pytest.fixture
def send(cli, monkeypatch):
    def run(payload: object, *args: str):
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        return cli(*args)

    return run


def _write(cli, send, job, kind, ext, content, language="en"):
    _, made, _ = cli("documents", "path", job, "--kind", kind, "--ext", ext)
    path = Path(made["path"])
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    meta = {"language": language}
    if kind == "resume-proposed":
        meta.update(summary="Fictional summary of the changes.", support=[], gaps=[])
    code, out, _ = send(meta, "documents", "register", job, kind, made["file_name"], "-")
    assert code == 0, out
    return out["document"]["id"]


def _filename(response) -> str:
    header = response.headers["content-disposition"]
    assert header.startswith("attachment;")
    if "filename*=" in header:
        return header.split("filename*=utf-8''", 1)[1]
    return quote(header.split('filename="', 1)[1].rstrip('"'))


def _paragraphs(content: bytes) -> list[str]:
    return [p.text for p in docx.Document(io.BytesIO(content)).paragraphs]


LETTER = """# Carta de presentación

Estimado equipo de **Altamar**:

Les escribo por el puesto de ingeniera de datos.
Tengo siete años de experiencia.

- Pipelines en Airflow
- Modelado en BigQuery
"""


def test_tailored_resume_downloads_with_name_and_job_id(based, cli, send, client, tmp_path):  # noqa: F811
    setup = based
    cli("privacy", "name", "set", PERSONA["name"])
    job = setup["altamar"]
    doc_id = _write(cli, send, job, "resume-proposed", "docx",
                    make_docx(tmp_path / "r.docx").read_bytes())
    response = client.get(f"/api/applications/{job}/documents/{doc_id}")
    assert response.status_code == 200
    assert _filename(response) == quote(f"{PERSONA['name']} - {job}.docx")
    assert response.content == next(setup["home"].applications.glob(
        f"{job}-*/resume-proposed-v1.docx")).read_bytes()


def test_spanish_cover_letter_downloads_as_word(based, cli, send, client):  # noqa: F811
    setup = based
    cli("privacy", "name", "set", PERSONA["name"])
    job = setup["altamar"]
    doc_id = _write(cli, send, job, "cover-letter", "md", LETTER, language="es")
    response = client.get(f"/api/applications/{job}/documents/{doc_id}")
    assert response.headers["content-type"] == documents_media()
    assert _filename(response) == quote(
        f"{PERSONA['name']} - {job} - Carta de presentación.docx")
    text = _paragraphs(response.content)
    assert "Carta de presentación" in text
    assert "Les escribo por el puesto de ingeniera de datos. Tengo siete años de experiencia." \
        in text
    assert "Pipelines en Airflow" in text
    stored = next(setup["home"].applications.glob(f"{job}-*/cover-letter-v1.md"))
    assert stored.read_text(encoding="utf-8") == LETTER


def test_english_cover_letter_label(based, cli, send, client):  # noqa: F811
    setup = based
    cli("privacy", "name", "set", PERSONA["name"])
    job = setup["finlima"]
    doc_id = _write(cli, send, job, "cover-letter", "md", "Dear team,\n\nFictional.")
    response = client.get(f"/api/applications/{job}/documents/{doc_id}")
    assert _filename(response) == quote(f"{PERSONA['name']} - {job} - Cover letter.docx")


def test_markdown_resume_downloads_as_word(based, cli, send, client):  # noqa: F811
    setup = based
    cli("privacy", "name", "set", PERSONA["name"])
    job = setup["altamar"]
    doc_id = _write(cli, send, job, "resume-proposed", "md",
                    "# Marisol\n\n## Experience\n\n- Built pipelines\n")
    response = client.get(f"/api/applications/{job}/documents/{doc_id}")
    assert _filename(response) == quote(f"{PERSONA['name']} - {job}.docx")
    assert _paragraphs(response.content) == ["Marisol", "Experience", "Built pipelines"]


def test_without_a_recorded_name_the_job_id_names_the_file(based, cli, send, client, tmp_path):  # noqa: F811
    setup = based
    job = setup["altamar"]
    doc_id = _write(cli, send, job, "resume-proposed", "docx",
                    make_docx(tmp_path / "r.docx").read_bytes())
    response = client.get(f"/api/applications/{job}/documents/{doc_id}")
    assert response.headers["content-disposition"] == f'attachment; filename="{job}.docx"'


def test_sent_resume_keeps_its_name(based, cli, client, tmp_path):  # noqa: F811
    setup = based
    cli("privacy", "name", "set", PERSONA["name"])
    job = setup["altamar"]
    source = make_docx(tmp_path / "cv.docx")
    with source.open("rb") as handle:
        uploaded = client.post(f"/api/applications/{job}/resume-sent",
                               files={"file": ("cv.docx", handle)}).json()["document"]
    response = client.get(f"/api/applications/{job}/documents/{uploaded['id']}")
    assert _filename(response) == quote(uploaded["file_name"])
    assert response.content == source.read_bytes()


def test_forbidden_characters_are_left_out(based, cli, send, client, tmp_path):  # noqa: F811
    setup = based
    cli("privacy", "name", "set", 'Marisol: "Quispe"/Tanaka?')
    job = setup["altamar"]
    doc_id = _write(cli, send, job, "resume-proposed", "docx",
                    make_docx(tmp_path / "r.docx").read_bytes())
    response = client.get(f"/api/applications/{job}/documents/{doc_id}")
    assert _filename(response) == quote(f"Marisol QuispeTanaka - {job}.docx")


def test_markdown_to_docx_keeps_bold():
    document = docx.Document(io.BytesIO(docx_tools.markdown_to_docx("Hola **equipo** de datos")))
    runs = document.paragraphs[0].runs
    assert [(r.text, bool(r.bold)) for r in runs] == [("Hola ", False), ("equipo", True),
                                                      (" de datos", False)]


def documents_media() -> str:
    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
