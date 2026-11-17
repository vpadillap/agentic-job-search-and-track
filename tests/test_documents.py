"""document-preparation, form-answers, pending-work: storage, tooling, and derivation."""
from __future__ import annotations

import io
import json
from pathlib import Path

import docx
import pytest
from fastapi.testclient import TestClient

from jobtracker.core import db, docx_tools, resume, tracking
from jobtracker.core.errors import JobTrackerError
from jobtracker.web.app import create_app
from tests.test_applications import jobs  # noqa: F401  (fixture)
from tests.test_scoring import submission

SUMMARY = "Summary rewritten toward data platform work; BigQuery bullets moved up."


def make_formatted_docx(path: Path) -> Path:
    """A fictional resume whose headline mixes bold and plain runs."""
    document = docx.Document()
    headline = document.add_paragraph()
    headline.add_run("Marisol Quispe Tanaka").bold = True
    headline.add_run(" · Senior Data Engineer")
    document.add_paragraph("Summary")
    document.add_paragraph("Data engineer with seven years of experience building pipelines "
                           "on Google Cloud for retail and logistics companies.")
    document.add_paragraph("Experience")
    document.add_paragraph("Designed and maintained Airflow and dbt pipelines.")
    document.add_paragraph("Modeled commercial and inventory data on BigQuery.")
    document.add_paragraph("Mentored two junior engineers.")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Skills"
    table.cell(0, 1).text = "Python, SQL, Airflow, dbt, BigQuery, GCP"
    document.add_paragraph("Languages: Spanish (native), English (B2)")
    document.save(str(path))
    return path


@pytest.fixture
def send(cli, monkeypatch):
    def run(payload: object, *args: str):
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        return cli(*args)

    return run


@pytest.fixture
def client():
    return TestClient(create_app(), base_url="http://127.0.0.1:8000")


@pytest.fixture
def based(jobs, tmp_path):  # noqa: F811
    """The tracked applications plus a DOCX base resume."""
    source = make_formatted_docx(tmp_path / "Marisol CV.docx")
    with db.session(jobs["home"]) as conn:
        resume.import_resume(conn, jobs["home"], source)
    return {**jobs, "base": jobs["home"].profile / "resume-base.docx"}


def tailor(send, job, edits):
    return send({"edits": edits}, "documents", "tailor", job, "-")


def register_resume(send, job, file_name, **meta):
    payload = {"language": "en", "summary": SUMMARY,
               "support": [{"term": "BigQuery",
                            "source": "Modeled commercial and inventory data on BigQuery."}],
               "gaps": ["Kafka (asked as desirable)"], **meta}
    return send(payload, "documents", "register", job, "resume-proposed", file_name, "-")


EDITS = [{"find": "Data engineer with seven years", "replace": "Data platform engineer with "
          "seven years"},
         {"move": "Modeled commercial and inventory data", "before": "Designed and maintained"}]


# ── versioning, immutability, registration ────────────────────────────────

def test_paths_are_versioned_and_never_reused(based, cli, send):
    job = based["altamar"]
    _, first, _ = cli("documents", "path", job, "--kind", "resume-proposed", "--ext", "docx")
    assert first["file_name"] == "resume-proposed-v1.docx"
    Path(first["path"]).write_bytes(based["base"].read_bytes())
    _, second, _ = cli("documents", "path", job, "--kind", "cover-letter", "--ext", "md")
    assert second["file_name"] == "cover-letter-v1.md"
    _, again, _ = cli("documents", "path", job, "--kind", "resume-proposed", "--ext", "md")
    assert again["file_name"] == "resume-proposed-v2.md"
    code, out, _ = cli("documents", "path", job, "--kind", "resume-proposed", "--ext", "pdf")
    assert code == 1 and out["error"]["code"] == "invalid_document"
    code, out, _ = cli("documents", "path", job, "--kind", "cover-letter", "--ext", "docx")
    assert code == 1 and out["error"]["code"] == "invalid_document"


def test_second_tailoring_keeps_earlier_version_and_base_unchanged(based, send, cli):
    job = based["altamar"]
    base_bytes = based["base"].read_bytes()
    _, first, _ = tailor(send, job, EDITS)
    assert first["file_name"] == "resume-proposed-v1.docx"
    register_resume(send, job, first["file_name"])
    v1 = Path(first["file"]).read_bytes()

    _, second, _ = tailor(send, job, [{"find": "Mentored two", "replace": "Mentored 2"}])
    assert second["file_name"] == "resume-proposed-v2.docx"
    code, registered, _ = register_resume(send, job, second["file_name"])
    assert code == 0 and registered["document"]["version"] == 2

    assert Path(first["file"]).read_bytes() == v1
    assert based["base"].read_bytes() == base_bytes
    _, listed, _ = cli("documents", "list", job)
    proposed = [d for d in listed["documents"] if d["kind"] == "resume_proposed"]
    assert [(d["version"], d["current"]) for d in proposed] == [(2, True), (1, False)]


def test_a_proposed_resume_must_explain_itself(based, send):
    job = based["altamar"]
    _, made, _ = tailor(send, job, EDITS)
    for meta, field in ((dict(summary=""), "summary"), (dict(language="English"), "language"),
                        (dict(support=[{"term": "Kafka"}]), "support"),
                        (dict(applied_rules=[9999]), "applied_rules"),
                        (dict(level="extreme"), "level")):
        code, out, _ = register_resume(send, job, made["file_name"], **meta)
        assert code == 1 and out["error"]["details"]["field"] == field, (meta, out)
    code, out, _ = register_resume(send, job, made["file_name"])
    assert code == 0
    document = out["document"]
    assert document["summary"] == SUMMARY and document["level"] == "light"
    assert document["support"][0]["term"] == "BigQuery"
    assert document["gaps"] == ["Kafka (asked as desirable)"]
    code, out, _ = register_resume(send, job, made["file_name"])
    assert code == 1 and out["error"]["code"] == "already_registered"


def test_registration_follows_the_naming_rule(based, send):
    job = based["altamar"]
    folder = Path(tailor(send, job, EDITS)[1]["file"]).parent
    (folder / "my-resume.docx").write_bytes(based["base"].read_bytes())
    code, out, _ = register_resume(send, job, "my-resume.docx")
    assert code == 1 and "naming rule" in out["error"]["message"]
    code, out, _ = register_resume(send, job, "resume-proposed-v9.docx")
    assert code == 1  # not a file in the folder


def test_rules_followed_are_recorded(based, send, cli):
    _, rule, _ = cli("rules", "add", "--text", "Never change the resume layout", "--area",
                     "resume")
    rule_id = rule["rules"][0]["id"]
    job = based["altamar"]
    _, made, _ = tailor(send, job, EDITS)
    _, out, _ = register_resume(send, job, made["file_name"], applied_rules=[rule_id])
    assert out["document"]["applied_rules"] == [rule_id]


# ── comparison ────────────────────────────────────────────────────────────

def test_comparison_shows_the_changed_passages(based, send, cli):
    job = based["altamar"]
    _, made, _ = tailor(send, job, EDITS)
    register_resume(send, job, made["file_name"])
    code, out, _ = cli("documents", "diff", job)
    assert code == 0, out
    replaced = [h for h in out["hunks"] if any("Data platform engineer" in line
                                               for line in h["proposed"])]
    assert replaced and any("Data engineer with seven years" in line
                            for line in replaced[0]["base"])
    moved = [h for h in out["hunks"] if any("Modeled commercial" in line
                                            for line in h["proposed"] + h["base"])]
    assert moved
    assert out["stats"]["added"] >= 2 and out["stats"]["removed"] >= 2
    unchanged = "Languages: Spanish (native), English (B2)"
    assert all(unchanged not in h["proposed"] for h in out["hunks"])


def test_comparison_without_a_proposed_resume(based, cli):
    code, out, _ = cli("documents", "diff", based["finlima"])
    assert code == 1 and out["error"]["code"] == "not_found"


def test_comparison_through_the_api(based, send, client):
    job = based["altamar"]
    _, made, _ = tailor(send, job, EDITS)
    _, registered, _ = register_resume(send, job, made["file_name"])
    body = client.get(f"/api/applications/{job}/documents/{registered['document']['id']}/diff"
                      ).json()
    assert body["ok"] and body["hunks"]


# ── tailoring tooling ─────────────────────────────────────────────────────

def test_replacement_keeps_the_formatting_of_its_run(tmp_path):
    base = make_formatted_docx(tmp_path / "base.docx")
    target = tmp_path / "out.docx"
    docx_tools.tailor(base, target, [
        {"find": "Quispe Tanaka · Senior", "replace": "Quispe Tanaka · Lead"},
        {"find": "Python, SQL", "replace": "Python, SQL, Pub/Sub"},
    ])
    headline = docx.Document(str(target)).paragraphs[0]
    assert headline.text == "Marisol Quispe Tanaka · Lead Data Engineer"
    assert headline.runs[0].bold is True and headline.runs[0].text.startswith("Marisol")
    assert docx.Document(str(target)).tables[0].cell(0, 1).text.startswith("Python, SQL, Pub")


def test_paragraphs_can_be_reordered(tmp_path):
    base = make_formatted_docx(tmp_path / "base.docx")
    target = tmp_path / "out.docx"
    docx_tools.tailor(base, target, [EDITS[1]])
    texts = [p.text for p in docx.Document(str(target)).paragraphs]
    assert texts.index("Modeled commercial and inventory data on BigQuery.") < \
        texts.index("Designed and maintained Airflow and dbt pipelines.")


@pytest.mark.parametrize("edit", [
    {"find": "Senior Data Engineer · nowhere", "replace": "x"},   # not found
    {"find": "e", "replace": "x"},                                # many paragraphs
    {"move": "Mentored", "before": "nowhere"},
    {"replace": "x"},
])
def test_edits_apply_all_or_nothing(tmp_path, edit):
    base = make_formatted_docx(tmp_path / "base.docx")
    target = tmp_path / "out.docx"
    with pytest.raises(JobTrackerError) as error:
        docx_tools.tailor(base, target, [EDITS[0], edit])
    assert error.value.code in ("edit_not_applied", "invalid_edit")
    assert not target.exists()


def test_existing_target_is_never_overwritten(tmp_path):
    base = make_formatted_docx(tmp_path / "base.docx")
    target = tmp_path / "out.docx"
    target.write_bytes(b"keep")
    with pytest.raises(JobTrackerError) as error:
        docx_tools.tailor(base, target, EDITS)
    assert error.value.code == "exists"
    assert target.read_bytes() == b"keep"


def test_a_pdf_base_cannot_be_tailored_in_place(jobs, send, tmp_path):  # noqa: F811
    from tests.helpers import make_text_pdf

    with db.session(jobs["home"]) as conn:
        resume.import_resume(conn, jobs["home"], make_text_pdf(tmp_path / "cv.pdf"))
    code, out, _ = tailor(send, jobs["altamar"], EDITS)
    assert code == 1 and out["error"]["code"] == "not_editable"
    assert "consent" in out["error"]["message"]


def test_layout_check_compares_shape(tmp_path):
    base = make_formatted_docx(tmp_path / "base.docx")
    target = tmp_path / "out.docx"
    docx_tools.tailor(base, target, EDITS)
    result = docx_tools.layout_check(base, target)
    assert result["paragraphs"]["base"] == result["paragraphs"]["proposed"]
    assert result["same_shape"] is True
    assert abs(result["characters"]["change_pct"]) < 5


def test_the_tailored_resume_is_a_word_document(based, send, cli):
    job = based["altamar"]
    _, made, _ = tailor(send, job, EDITS)
    assert made["file_name"].endswith(".docx")
    reopened = docx.Document(made["file"])
    assert reopened.paragraphs[0].runs[0].bold is True
    assert "pdf" not in register_resume(send, job, made["file_name"])[1]["document"]


# ── cover letters ─────────────────────────────────────────────────────────

def test_cover_letter_not_required_is_recorded(based, cli):
    job = based["finlima"]
    code, out, _ = cli("documents", "cover-letter", job, "--need", "not_required",
                       "--reason", "The posting does not ask for one")
    assert code == 0
    assert out["cover_letter"] == {"need": "not_required",
                                   "reason": "The posting does not ask for one",
                                   "written": False}
    _, shown, _ = cli("applications", "show", job)
    assert shown["application"]["cover_letter"]["need"] == "not_required"
    assert shown["application"]["documents"]["cover_letter"] is None


def test_writing_a_cover_letter_marks_it_required(based, cli, send):
    job = based["altamar"]
    _, path, _ = cli("documents", "path", job, "--kind", "cover-letter", "--ext", "md")
    Path(path["path"]).write_text("Dear team,\nFictional letter.", encoding="utf-8")
    code, out, _ = send({"language": "es"}, "documents", "register", job, "cover-letter",
                        path["file_name"], "-")
    assert code == 0, out
    _, listed, _ = cli("documents", "list", job)
    assert listed["cover_letter"] == {"need": "required", "reason": None, "written": True}


# ── form answers ──────────────────────────────────────────────────────────

def answers_payload(overrides: dict | None = None):
    overrides = overrides or {}
    items = [
        {"position": 1, "text": "Cinco años, en producción.", "language": "es"},
        {"position": 2, "text": "S/ 15,000 brutos mensuales.", "language": "es",
         "basis": "Basada en el salario sugerido"},
        {"position": 3, "text": "Dos semanas después de aceptar.", "language": "es"},
        {"position": 4, "text": "", "needs_user": True, "language": "es",
         "note": "No hay portafolio en tu CV ni en tu perfil."},
    ]
    for item in items:
        item.update(overrides.get(item["position"], {}))
    return items


def test_each_captured_question_gets_an_answer(based, send, cli):
    job = based["altamar"]
    code, out, _ = send(answers_payload(), "answers", "set", job, "-")
    assert code == 0, out
    assert out["current"] == [1, 2, 3, 4]
    _, listed, _ = cli("answers", "list", job)
    assert all(q["answer"] is not None for q in listed["questions"])
    salary_answer = listed["questions"][1]["answer"]
    assert salary_answer["basis"] == "Basada en el salario sugerido"
    _, shown, _ = cli("applications", "show", job)
    assert shown["application"]["form_answered_count"] == 3
    assert shown["application"]["form_proposed_count"] == 4


def test_unknown_facts_are_left_for_the_user(based, send, cli):
    job = based["altamar"]
    code, out, _ = send(answers_payload({4: {"note": None}}), "answers", "set", job, "-")
    assert code == 1 and out["error"]["code"] == "invalid_answer"
    code, out, _ = send(answers_payload({4: {"needs_user": False}}), "answers", "set", job, "-")
    assert code == 1  # an empty answer must say it needs the user
    send(answers_payload(), "answers", "set", job, "-")
    _, listed, _ = cli("answers", "list", job)
    portfolio = listed["questions"][3]["answer"]
    assert portfolio["needs_user"] is True and portfolio["text"] == ""
    assert "portafolio" in portfolio["note"]


def test_no_captured_questions_means_no_form(based, send, cli):
    job = based["finlima"]
    code, out, _ = send(answers_payload(), "answers", "set", job, "-")
    assert code == 1 and out["error"]["code"] == "no_form"
    code, out, _ = cli("answers", "list", job)
    assert code == 0 and out["questions"] == [] and "no form" in out["message"]


def test_invalid_answers_store_nothing(based, send, cli):
    job = based["altamar"]
    code, out, _ = send([{"position": 9, "text": "x", "language": "es"}], "answers", "set",
                        job, "-")
    assert code == 1 and out["error"]["details"]["index"] == 0
    code, out, _ = send([*answers_payload()[:1], {"position": 1, "text": "x",
                                                   "language": "es"}],
                        "answers", "set", job, "-")
    assert code == 1
    _, listed, _ = cli("answers", "list", job)
    assert all(q["answer"] is None for q in listed["questions"])


def test_user_edits_survive_regeneration(based, send, client, cli):
    job = based["altamar"]
    send(answers_payload(), "answers", "set", job, "-")
    edited = client.post(f"/api/applications/{job}/answers/1",
                         json={"text": "Seis años, con Airflow 2."}).json()["question"]
    assert edited["answer"]["origin"] == "user"

    _, out, _ = send(answers_payload({1: {"text": "Cinco años (nueva versión)."}}),
                     "answers", "set", job, "-")
    assert out["alternatives"] == [1] and 1 not in out["current"]
    question = out["answers"][0]
    assert question["answer"]["text"] == "Seis años, con Airflow 2."
    assert question["answer"]["origin"] == "user"
    assert [a["text"] for a in question["alternatives"]] == ["Cinco años (nueva versión)."]

    picked = client.post(f"/api/applications/{job}/answers-pick",
                         json={"answer_id": question["alternatives"][0]["id"]}).json()
    assert picked["question"]["answer"]["text"] == "Cinco años (nueva versión)."
    assert [a["text"] for a in picked["question"]["alternatives"]] == [
        "Seis años, con Airflow 2."]  # the user's version is kept


def test_agent_answers_replace_earlier_agent_answers(based, send, cli):
    job = based["altamar"]
    send(answers_payload(), "answers", "set", job, "-")
    _, out, _ = send(answers_payload({3: {"text": "Inmediata."}}), "answers", "set", job, "-")
    assert 3 in out["current"]
    assert out["answers"][2]["answer"]["text"] == "Inmediata."
    assert out["answers"][2]["alternatives"] == []


def test_explicit_alternatives(based, send):
    job = based["altamar"]
    send(answers_payload(), "answers", "set", job, "-")
    _, out, _ = send([{"position": 2, "text": "Entre S/ 14,000 y S/ 16,000.", "language": "es"}],
                     "answers", "alternative", job, "-")
    assert out["alternatives"] == [2]
    assert out["answers"][1]["answer"]["text"] == "S/ 15,000 brutos mensuales."


# ── pending work ──────────────────────────────────────────────────────────

def kinds_for(items: list[dict], job: str) -> set[str]:
    return {i["kind"] for i in items if i.get("job_id") == job}


def test_newly_tracked_posting_with_a_form(based, cli):
    _, out, _ = cli("pending")
    assert kinds_for(out["pending"], based["altamar"]) == {"resume", "cover_letter",
                                                           "form_answers"}
    assert kinds_for(out["pending"], based["finlima"]) == {"resume", "cover_letter"}
    form = next(i for i in out["pending"] if i["kind"] == "form_answers")
    assert form["missing"] == 4


def test_already_applied_is_not_listed_for_documents(searchable, cli, tmp_path):
    from tests.test_search import captures

    path = tmp_path / "captures.json"
    path.write_text(json.dumps(captures()), encoding="utf-8")
    _, run, _ = cli("run", "start")
    _, imported, _ = cli("postings", "import", str(run["run_id"]), str(path))
    posting = next(p["posting_id"] for p in imported["postings"] if p["external_id"] == "A-100")
    with db.session(searchable) as conn:
        job = tracking.track(conn, [posting], applied=True)[0]["job_id"]
    _, out, _ = cli("pending")
    assert kinds_for(out["pending"], job) == set()


def test_most_promising_first(based, cli):
    _, out, _ = cli("pending")
    jobs_in_order = list(dict.fromkeys(i["job_id"] for i in out["pending"]))
    assert jobs_in_order[0] == based["altamar"]  # scored; the other has no score


def test_selective_pending(based, cli):
    _, out, _ = cli("pending", "--ids", based["finlima"], "J9999")
    assert {i["job_id"] for i in out["pending"]} == {based["finlima"]}
    assert out["nothing_pending_for"] == ["J9999"]


def test_batch_clears_everything_pending(based, send, cli, tmp_path):
    for job in (based["altamar"], based["finlima"]):
        _, made, _ = tailor(send, job, EDITS)
        assert register_resume(send, job, made["file_name"])[0] == 0
    cli("documents", "cover-letter", based["finlima"], "--need", "not_required")
    _, path, _ = cli("documents", "path", based["altamar"], "--kind", "cover-letter",
                     "--ext", "md")
    Path(path["path"]).write_text("Estimado equipo:\nCarta ficticia.", encoding="utf-8")
    send({"language": "es"}, "documents", "register", based["altamar"], "cover-letter",
         path["file_name"], "-")
    send(answers_payload(), "answers", "set", based["altamar"], "-")

    _, out, _ = cli("pending")
    rescores = [i for i in out["pending"] if i["kind"] == "rescore"]
    assert {i["job_id"] for i in rescores} == {based["altamar"], based["finlima"]}
    assert all(i["resume"]["kind"] == "tailored" for i in rescores)
    assert [i for i in out["pending"] if i["kind"] != "rescore"] == []
    for item in rescores:
        data = submission()
        data["resume"] = item["resume"]
        file = tmp_path / f"score-{item['posting_id']}.json"
        file.write_text(json.dumps(data), encoding="utf-8")
        code, scored, _ = cli("score", "set", str(item["posting_id"]), str(file))
        assert code == 0, scored
        assert scored["score"]["resume_kind"] == "tailored"
    _, out, _ = cli("pending")
    assert out["pending"] == []


def test_header_count_matches_the_pending_list(based, client):
    state = client.get("/api/state").json()
    listed = client.get("/api/pending").json()["pending"]
    assert state["header"]["pending"] == len(listed) > 0
