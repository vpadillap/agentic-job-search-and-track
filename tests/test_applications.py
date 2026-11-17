"""application-tracking: statuses, applied date, tags, details, uploads, history, ghosting."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from jobtracker.core import applications, board, db, tracking
from jobtracker.web.app import create_app
from tests.test_salary import report
from tests.test_scoring import submission
from tests.test_search import captures

PDF = b"%PDF-1.4\n% fictional resume\n"
DOCX = b"PK\x03\x04 fictional docx"


@pytest.fixture
def client():
    return TestClient(create_app(), base_url="http://127.0.0.1:8000")


@pytest.fixture
def jobs(searchable, cli, tmp_path) -> dict:
    """Two tracked applications from fictional captures, one scored with a salary."""
    path = tmp_path / "captures.json"
    path.write_text(json.dumps(captures()), encoding="utf-8")
    _, run, _ = cli("run", "start")
    _, imported, _ = cli("postings", "import", str(run["run_id"]), str(path))
    ids = {p["external_id"]: p.get("posting_id") for p in imported["postings"]}
    cli("run", "finish", str(run["run_id"]))
    with db.session(searchable) as conn:
        from jobtracker.core import salary, scoring

        scoring.set_score(conn, ids["A-100"], submission())
        evidence = salary.add_evidence(conn, [
            {**report(), "posting_id": ids["A-100"]},
            {**report(url="https://example.test/s/2"), "posting_id": ids["A-100"]}])
        salary.set_suggestion(conn, ids["A-100"], {
            "evidence_ids": [e["id"] for e in evidence], "criteria": {"currency": "PEN"}})
        tracked = tracking.track(conn, [ids["A-100"], ids["A-101"]])
    return {"altamar": tracked[0]["job_id"], "finlima": tracked[1]["job_id"],
            "home": searchable, "postings": ids}


def detail(home, job_id):
    with db.session(home) as conn:
        return applications.detail(conn, job_id)


# ── persistence and statuses ──────────────────────────────────────────────

def test_tracked_application_survives_a_new_search(jobs, cli, tmp_path):
    before = detail(jobs["home"], jobs["altamar"])
    path = tmp_path / "again.json"
    path.write_text(json.dumps(captures()), encoding="utf-8")
    _, run, _ = cli("run", "start")
    cli("postings", "import", str(run["run_id"]), str(path))
    cli("run", "finish", str(run["run_id"]))
    after = detail(jobs["home"], jobs["altamar"])
    for key in ("status", "tags", "applied_on", "score", "salary", "documents"):
        assert after[key] == before[key]


def _keys(value) -> set:
    """Every dictionary key anywhere in a JSON value."""
    if isinstance(value, dict):
        return set(value) | set().union(*(_keys(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(_keys(v) for v in value)) if value else set()
    return set()


def test_new_application_starts_as_new(jobs):
    item = detail(jobs["home"], jobs["altamar"])
    assert item["status"]["key"] == "new" and item["ended"] is False
    assert item["applied_on"] is None


def test_changing_status_records_history_with_full_names(jobs, cli):
    cli("applications", "set-status", jobs["altamar"], "--to", "Applied")
    code, out, _ = cli("applications", "set-status", jobs["altamar"], "--to", "interview")
    assert code == 0
    assert out["applications"][0]["status"]["name"] == "Interview"
    assert out["applications"][0]["ended"] is False
    changes = [h for h in detail(jobs["home"], jobs["altamar"])["history"]
               if h["kind"] == "status_changed"]
    assert [(c["data"]["from_name"], c["data"]["to_name"]) for c in changes] == [
        ("New", "Applied"), ("Applied", "Interview")]
    assert all(c["at"].startswith(datetime.now().strftime("%Y-")) for c in changes)


def test_ending_status(jobs, cli):
    code, out, _ = cli("applications", "set-status", jobs["altamar"], "--to", "rejected")
    assert code == 0 and out["applications"][0]["ended"] is True
    _, listed, _ = cli("applications", "statuses", "list")
    ends = {s["key"]: s["ends"] for s in listed["statuses"]}
    assert [k for k, v in ends.items() if v] == ["accepted", "rejected", "ghosted",
                                                 "offer_declined", "no_economic_alignment",
                                                 "withdrawn"]


def test_no_stage_anywhere(jobs, cli):
    cli("applications", "set-status", jobs["altamar"], "--to", "applied")
    for command in (("applications", "list"), ("applications", "show", jobs["altamar"]),
                    ("applications", "statuses", "list"), ("context",)):
        _, out, _ = cli(*command)
        assert not {k for k in _keys(out) if "stage" in k}, command


def test_creating_a_status_inline(jobs, cli):
    code, out, _ = cli("applications", "set-status", jobs["altamar"], "--to", "Position frozen",
                       "--ends", "yes")
    assert code == 0
    assert out["applications"][0]["status"]["name"] == "Position frozen"
    assert out["applications"][0]["ended"] is True
    code, _, _ = cli("applications", "set-status", jobs["finlima"], "--to", "position frozen")
    assert code == 0                                             # available for all others
    _, listed, _ = cli("applications", "statuses", "list")
    created = next(s for s in listed["statuses"] if s["name"] == "Position frozen")
    assert created["ends"] is True and created["builtin"] is False


def test_unknown_status_without_ends_is_refused(jobs, cli):
    code, out, _ = cli("applications", "set-status", jobs["altamar"], "--to", "Limbo")
    assert code == 1 and "ends" in out["error"]["message"]


def test_creating_a_status_asks_whether_it_ends(jobs, cli):
    code, out, _ = cli("applications", "statuses", "create", "Limbo")
    assert code == 2 and out["error"]["code"] == "usage"


def test_custom_status_before_applying_leaves_no_applied_date(jobs, cli):
    code, out, _ = cli("applications", "set-status", jobs["altamar"], "--to",
                       "Waiting for a referral", "--ends", "no")
    assert code == 0
    item = detail(jobs["home"], jobs["altamar"])
    assert item["applied_on"] is None and item["snapshot"] is None
    assert item["next_step"] == {"kind": "prepare_documents"}
    _, listed, _ = cli("applications", "list")
    assert jobs["altamar"] in listed["attention"]["missing_resume"]


def test_withdrawn_leaves_no_applied_date(jobs, cli):
    cli("applications", "set-status", jobs["altamar"], "--to", "withdrawn")
    assert detail(jobs["home"], jobs["altamar"])["applied_on"] is None


def test_applied_date_entered_by_hand_makes_the_application_applied(jobs, cli, tmp_path):
    home, job = jobs["home"], jobs["altamar"]
    cli("applications", "set-status", job, "--to", "Technical test sent", "--ends", "no")
    path = tmp_path / "d.json"
    path.write_text(json.dumps({"applied_on": "2026-11-10"}), encoding="utf-8")
    code, out, _ = cli("applications", "update", job, str(path))
    assert code == 0, out
    item = detail(home, job)
    assert item["snapshot"]["applied_on"] == "2026-11-10" and item["snapshot"]["score"] == 86
    assert item["next_step"]["kind"] in ("follow_up", "ghost")
    _, listed, _ = cli("applications", "list")
    assert job not in listed["attention"]["missing_resume"]


def test_the_agent_gets_full_status_names_and_their_history(jobs, cli):
    job = jobs["altamar"]
    cli("applications", "set-status", job, "--to", "applied")
    cli("applications", "set-status", job, "--to", "Technical test sent", "--ends", "no")
    cli("applications", "set-status", job, "--to", "interview")
    _, out, _ = cli("applications", "show", job)
    item = out["application"]
    assert (item["status"]["name"], item["status"]["key"], item["ended"]) == (
        "Interview", "interview", False)
    changes = [h for h in item["history"] if h["kind"] == "status_changed"]
    assert [(c["data"]["from_name"], c["data"]["to_name"]) for c in changes] == [
        ("New", "Applied"), ("Applied", "Technical test sent"),
        ("Technical test sent", "Interview")]
    assert all(c["at"][:10] == datetime.now().strftime("%Y-%m-%d") for c in changes)
    cli("config", "set", "language", "es")
    _, out, _ = cli("applications", "show", job)
    changes = [h for h in out["application"]["history"] if h["kind"] == "status_changed"]
    assert changes[-1]["data"]["to_name"] == "Entrevista"
    assert out["application"]["status"]["name_en"] == "Interview"


def test_list_by_status(jobs, cli):
    cli("applications", "set-status", jobs["finlima"], "--to", "applied")
    code, out, _ = cli("applications", "list", "--status", "Applied")
    assert code == 0 and [a["job_id"] for a in out["applications"]] == [jobs["finlima"]]
    code, out, _ = cli("applications", "list", "--status", "Nope")
    assert code == 1 and out["error"]["code"] == "not_found"


def test_retiring_a_status_in_use(jobs, cli):
    cli("applications", "set-status", jobs["altamar"], "--to", "On hold", "--ends", "no")
    _, listed, _ = cli("applications", "statuses", "list")
    status_id = next(s["id"] for s in listed["statuses"] if s["name"] == "On hold")
    code, _, _ = cli("applications", "statuses", "retire", str(status_id))
    assert code == 0
    assert detail(jobs["home"], jobs["altamar"])["status"]["name"] == "On hold"
    _, listed, _ = cli("applications", "statuses", "list")
    assert "On hold" not in [s["name"] for s in listed["statuses"]]
    code, out, _ = cli("applications", "set-status", jobs["finlima"], "--to", "On hold")
    assert code == 1 and out["error"]["code"] == "retired_status"


def test_built_in_statuses_cannot_be_renamed_or_retired(jobs, cli):
    _, listed, _ = cli("applications", "statuses", "list")
    builtin = next(s for s in listed["statuses"] if s["key"] == "rejected")
    code, out, _ = cli("applications", "statuses", "retire", str(builtin["id"]))
    assert code == 1 and out["error"]["code"] == "builtin_status"
    assert len([s for s in listed["statuses"] if s["builtin"]]) == 10


def test_custom_status_rename(jobs, cli):
    _, created, _ = cli("applications", "statuses", "create", "Paused", "--ends", "no")
    code, out, _ = cli("applications", "statuses", "rename", str(created["status"]["id"]),
                       "Paused by company")
    assert code == 0 and out["status"]["name"] == "Paused by company"


def test_built_in_statuses_are_localized(jobs, cli):
    cli("config", "set", "language", "es")
    _, listed, _ = cli("applications", "statuses", "list")
    assert {s["key"]: s["name"] for s in listed["statuses"]}["interview"] == "Entrevista"


# ── tags and details ──────────────────────────────────────────────────────

def test_tags(jobs, cli):
    code, out, _ = cli("applications", "tag", jobs["altamar"], "--add", "Referral",
                       "--add", "Technical 2 of 3")
    assert code == 0 and out["tags"] == ["Referral", "Technical 2 of 3"]
    _, out, _ = cli("applications", "tag", jobs["altamar"], "--remove", "referral")
    assert out["tags"] == ["Technical 2 of 3"]


def test_asked_salary_is_stored_with_currency_next_to_the_suggestion(jobs, cli, tmp_path):
    path = tmp_path / "d.json"
    path.write_text(json.dumps({"asked_salary": {"amount": 15500, "currency": "PEN"},
                                "channel": "Company site", "contact": "Recruiter (fictional)",
                                "notes": "Asked for availability."}), encoding="utf-8")
    code, out, _ = cli("applications", "update", jobs["altamar"], str(path))
    assert code == 0, out
    item = out["application"]
    assert item["asked_salary"] == {"amount": 15500, "currency": "PEN", "basis": "gross",
                                    "period": "month"}
    assert item["salary"]["amount"] == 15000 and item["salary"]["currency"] == "PEN"
    fields = {h["data"]["field"] for h in detail(jobs["home"], jobs["altamar"])["history"]
              if h["kind"] == "field_changed"}
    assert fields == {"asked_salary", "channel", "contact", "notes"}


@pytest.mark.parametrize("bad", [
    {"applied_on": "yesterday"}, {"asked_salary": {"amount": -5, "currency": "PEN"}},
    {"asked_salary": {"amount": 100, "currency": "soles"}}, {"color": "red"},
])
def test_invalid_details_are_rejected(jobs, cli, tmp_path, bad):
    path = tmp_path / "d.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    code, out, _ = cli("applications", "update", jobs["altamar"], str(path))
    assert code == 1 and out["error"]["code"] == "invalid_details"


# ── snapshot ──────────────────────────────────────────────────────────────

def test_snapshot_is_taken_when_first_applying_and_keeps_its_facts(jobs, cli, tmp_path):
    home, job = jobs["home"], jobs["altamar"]
    path = tmp_path / "d.json"
    path.write_text(json.dumps({"channel": "LinkedIn"}), encoding="utf-8")
    cli("applications", "update", job, str(path))
    assert detail(home, job)["snapshot"] is None
    cli("applications", "set-status", job, "--to", "applied")
    snap = detail(home, job)["snapshot"]
    assert snap["score"] == 86 and snap["resume_kind"] == "base"
    assert snap["channel"] == "LinkedIn" and snap["suggested_salary"]["amount"] == 15000
    assert snap["applied_on"] == datetime.now().date().isoformat()
    with db.session(home) as conn:      # later changes do not touch the captured facts
        from jobtracker.core import scoring

        scoring.set_score(conn, jobs["postings"]["A-100"], submission(title={"points": 5}))
    path.write_text(json.dumps({"channel": "Email", "applied_on": "2026-11-01",
                                "asked_salary": {"amount": 16000, "currency": "PEN"}}),
                    encoding="utf-8")
    cli("applications", "update", job, str(path))
    cli("applications", "set-status", job, "--to", "interview")
    snap = detail(home, job)["snapshot"]
    assert snap["score"] == 86 and snap["channel"] == "LinkedIn"
    assert snap["applied_on"] == "2026-11-01" and snap["asked_salary"]["amount"] == 16000


def test_track_and_mark_applied_takes_the_snapshot(jobs):
    with db.session(jobs["home"]) as conn:
        application = tracking.track(conn, [jobs["postings"]["B-7"]], applied=True)[0]
        assert applications.snapshot(conn, application["job_id"]) is not None


# ── next step, follow-up, ghosting ────────────────────────────────────────

def _age(home, job_id, days):
    when = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with db.session(home) as conn:
        conn.execute("UPDATE applications SET status_changed_at = ?, applied_on = ?"
                     " WHERE job_id = ?", (when, when[:10], job_id))


def test_next_step_is_derived_from_the_status(jobs, cli, tmp_path):
    home, job = jobs["home"], jobs["altamar"]
    assert detail(home, job)["next_step"] == {"kind": "prepare_documents"}
    cli("applications", "set-status", job, "--to", "applied")
    step = detail(home, job)["next_step"]
    assert step["kind"] == "follow_up" and step["due"] is False
    cli("applications", "set-status", job, "--to", "interview")
    assert detail(home, job)["next_step"] == {"kind": "set_date"}
    path = tmp_path / "d.json"
    path.write_text(json.dumps({"next_step_on": "2026-11-19",
                                "next_step_note": "Technical interview"}), encoding="utf-8")
    cli("applications", "update", job, str(path))
    assert detail(home, job)["next_step"] == {"kind": "user", "note": "Technical interview",
                                              "date": "2026-11-19"}


def test_follow_up_is_due_after_a_week(jobs, cli):
    cli("applications", "set-status", jobs["altamar"], "--to", "applied")
    _age(jobs["home"], jobs["altamar"], 8)
    item = detail(jobs["home"], jobs["altamar"])
    assert item["flags"]["follow_up_due"] is True and item["flags"]["ghost"] is False


def test_no_response_is_flagged_but_status_is_unchanged(jobs, cli):
    cli("applications", "set-status", jobs["altamar"], "--to", "applied")
    _age(jobs["home"], jobs["altamar"], 22)
    item = detail(jobs["home"], jobs["altamar"])
    assert item["flags"]["ghost"] is True
    assert item["next_step"]["kind"] == "ghost" and item["next_step"]["days"] == 22
    assert item["status"]["key"] == "applied"
    _, listed, _ = cli("applications", "list")
    assert listed["attention"]["no_response"] == [jobs["altamar"]]
    code, out, _ = cli("applications", "set-status", jobs["altamar"], "--to", "ghosted")
    assert code == 0 and out["applications"][0]["ended"] is True


def test_an_ended_application_is_not_flagged(jobs, cli):
    cli("applications", "set-status", jobs["altamar"], "--to", "applied")
    cli("applications", "set-status", jobs["altamar"], "--to", "Position frozen",
        "--ends", "yes")
    _age(jobs["home"], jobs["altamar"], 30)
    item = detail(jobs["home"], jobs["altamar"])
    assert item["flags"] == {"ghost": False, "follow_up_due": False}
    assert item["next_step"] == {"kind": "none"}


def test_a_custom_status_after_applying_gets_follow_up_and_ghost(jobs, cli):
    cli("applications", "set-status", jobs["altamar"], "--to", "applied")
    cli("applications", "set-status", jobs["altamar"], "--to", "Technical test sent",
        "--ends", "no")
    _age(jobs["home"], jobs["altamar"], 22)
    assert detail(jobs["home"], jobs["altamar"])["flags"]["ghost"] is True


def test_ghost_threshold_comes_from_rules(jobs, cli):
    cli("applications", "set-status", jobs["altamar"], "--to", "applied")
    _age(jobs["home"], jobs["altamar"], 15)
    assert detail(jobs["home"], jobs["altamar"])["flags"]["ghost"] is False
    with db.session(jobs["home"]) as conn:
        conn.execute(
            "INSERT INTO rules (origin, status, area, text, effect, created_at, updated_at)"
            " VALUES ('user', 'active', 'statuses', 'Ghost after two weeks', ?, 'x', 'x')",
            (json.dumps({"ghost_after_days": 14}),))
    assert detail(jobs["home"], jobs["altamar"])["flags"]["ghost"] is True


def test_attention_lists_missing_resumes_and_unanswered_forms(jobs, cli):
    _, listed, _ = cli("applications", "list")
    attention = listed["attention"]
    assert sorted(attention["missing_resume"]) == sorted([jobs["altamar"], jobs["finlima"]])
    assert attention["unanswered_form"] == [jobs["altamar"]]     # A-100 has 4 questions


def test_list_can_hide_ended(jobs, cli):
    cli("applications", "set-status", jobs["finlima"], "--to", "rejected")
    _, listed, _ = cli("applications", "list", "--hide-ended")
    assert [a["job_id"] for a in listed["applications"]] == [jobs["altamar"]]
    assert [(f["name"], f["count"]) for f in listed["funnel"]] == [("New", 1)]


def test_one_count_per_status_in_use_in_list_order(jobs, cli):
    cli("applications", "set-status", jobs["finlima"], "--to", "Technical test sent",
        "--ends", "no")
    cli("applications", "set-status", jobs["altamar"], "--to", "rejected")
    _, listed, _ = cli("applications", "list")
    assert [(f["name"], f["count"], f["ends"]) for f in listed["funnel"]] == [
        ("Rejected", 1, True), ("Technical test sent", 1, False)]


# ── uploads and documents ─────────────────────────────────────────────────

def test_uploading_the_sent_resume(jobs, client):
    home, job = jobs["home"], jobs["altamar"]
    response = client.post(f"/api/applications/{job}/resume-sent",
                           files={"file": ("My resume final.pdf", PDF, "application/pdf")})
    assert response.status_code == 200, response.json()
    document = response.json()["document"]
    assert document["kind"] == "resume_sent" and document["file_name"] == "resume-sent.pdf"
    assert document["original_name"] == "My resume final.pdf"
    folder = home.applications / f"{job}-altamar-retail"
    assert (folder / "resume-sent.pdf").read_bytes() == PDF
    item = detail(home, job)
    assert item["documents"]["resume_sent"]["id"] == document["id"]
    with db.session(home) as conn:
        pending = [p for p in board.pending(conn) if p["kind"] == "rescore"]
    assert [(p["job_id"], p["resume"]["ref"]) for p in pending] == [(job, "resume-sent.pdf#v1")]
    assert any(h["kind"] == "document_registered" for h in item["history"])


def test_replacing_an_upload_keeps_the_earlier_file(jobs, client):
    home, job = jobs["home"], jobs["altamar"]
    client.post(f"/api/applications/{job}/resume-sent",
                files={"file": ("first.pdf", PDF, "application/pdf")})
    response = client.post(f"/api/applications/{job}/resume-sent",
                           files={"file": ("second.docx", DOCX, "application/octet-stream")})
    assert response.status_code == 200
    folder = home.applications / f"{job}-altamar-retail"
    assert sorted(p.name for p in folder.iterdir()) == ["resume-sent-v1.pdf", "resume-sent.docx"]
    item = detail(home, job)
    assert item["documents"]["resume_sent"]["file_name"] == "resume-sent.docx"
    assert [d["version"] for d in item["all_documents"]] == [2, 1]


@pytest.mark.parametrize("name,data,code", [
    ("resume.txt", b"plain text", "unsupported_file"),
    ("resume.pdf", b"<html>not a pdf</html>", "unsupported_file"),
    ("resume.exe", b"MZ", "unsupported_file"),
    ("resume.pdf", b"%PDF" + b"0" * (10 * 1024 * 1024), "file_too_large"),
])
def test_unsupported_uploads_are_rejected(jobs, client, name, data, code):
    response = client.post(f"/api/applications/{jobs['altamar']}/resume-sent",
                           files={"file": (name, data, "application/octet-stream")})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == code
    assert not (jobs["home"].applications / f"{jobs['altamar']}-altamar-retail").exists() \
        or not any((jobs["home"].applications / f"{jobs['altamar']}-altamar-retail").iterdir())


def test_documents_download_as_attachments(jobs, client):
    job = jobs["altamar"]
    document = client.post(f"/api/applications/{job}/resume-sent",
                           files={"file": ("cv.pdf", PDF, "application/pdf")}).json()["document"]
    response = client.get(f"/api/applications/{job}/documents/{document['id']}")
    assert response.status_code == 200 and response.content == PDF
    assert response.headers["content-disposition"].startswith("attachment")
    assert response.headers["content-type"] == "application/octet-stream"
    assert client.get(f"/api/applications/{job}/documents/{document['id']}/text"
                      ).status_code == 400


def test_downloads_are_confined_to_the_private_folder(jobs, client):
    job = jobs["altamar"]
    document = client.post(f"/api/applications/{job}/resume-sent",
                           files={"file": ("cv.pdf", PDF, "application/pdf")}).json()["document"]
    outside = jobs["home"].home.parent / "outside.txt"
    outside.write_text("not private", encoding="utf-8")
    with db.session(jobs["home"]) as conn:
        conn.execute("UPDATE documents SET file_name = ? WHERE id = ?",
                     ("../../../outside.txt", document["id"]))
    response = client.get(f"/api/applications/{job}/documents/{document['id']}")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "forbidden_path"
    other = jobs["finlima"]
    assert client.get(f"/api/applications/{other}/documents/{document['id']}").status_code == 404


def test_cover_letter_text_can_be_copied(jobs, client):
    home, job = jobs["home"], jobs["altamar"]
    folder = home.applications / f"{job}-altamar-retail"
    folder.mkdir(parents=True)
    (folder / "cover-letter-v1.md").write_text("Dear team,\nFictional letter.", encoding="utf-8")
    with db.session(home) as conn:
        document = applications.register_document(conn, home, job, "cover_letter",
                                                   "cover-letter-v1.md", "agent")
    body = client.get(f"/api/applications/{job}/documents/{document['id']}/text").json()
    assert body["text"] == "Dear team,\nFictional letter."


def test_rescore_against_the_sent_resume_clears_pending_and_shows_the_change(jobs, client, cli,
                                                                            tmp_path):
    job = jobs["altamar"]
    client.post(f"/api/applications/{job}/resume-sent",
                files={"file": ("cv.pdf", PDF, "application/pdf")})
    _, pending, _ = cli("pending")
    item = next(p for p in pending["pending"] if p["kind"] == "rescore")
    data = submission(skills={"points": 33, "note": "All skills match.", "missing": []})
    data["resume"] = item["resume"]
    path = tmp_path / "s.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    code, out, _ = cli("score", "set", str(item["posting_id"]), str(path))
    assert code == 0, out
    _, pending, _ = cli("pending")
    assert [p for p in pending["pending"] if p["kind"] == "rescore"] == []
    row = next(a for a in client.get("/api/applications").json()["applications"]
               if a["job_id"] == job)
    assert row["score"]["total"] == 92 and row["score"]["previous_total"] == 86


# ── API ───────────────────────────────────────────────────────────────────

def test_board_api(jobs, client):
    body = client.get("/api/applications").json()
    assert [(f["key"], f["name"], f["ends"], f["count"]) for f in body["funnel"]] == [
        ("new", "New", False, 2)]
    assert len(body["statuses"]) == 10
    assert body["thresholds"] == {"follow_up_after_days": 7, "ghost_after_days": 21}


def test_status_api_with_inline_creation_and_bulk(jobs, client):
    response = client.post("/api/applications/status", json={
        "job_ids": [jobs["altamar"], jobs["finlima"]], "status": "Recruiter call",
        "ends": False})
    assert response.status_code == 200
    rows = {a["job_id"]: (a["status"]["name"], a["ended"], a["applied_on"])
            for a in client.get("/api/applications").json()["applications"]}
    assert rows == {jobs["altamar"]: ("Recruiter call", False, None),
                    jobs["finlima"]: ("Recruiter call", False, None)}
    refused = client.post("/api/applications/status", json={
        "job_ids": [jobs["altamar"]], "status": "Another new one"})
    assert refused.status_code == 404


def test_details_and_tags_api(jobs, client):
    job = jobs["altamar"]
    assert client.post(f"/api/applications/{job}/details",
                       json={"notes": "Called back"}).status_code == 200
    assert client.post(f"/api/applications/{job}/tags",
                       json={"add": ["Referral"]}).json()["tags"] == ["Referral"]
    item = client.get(f"/api/applications/{job}").json()["application"]
    assert item["notes"] == "Called back" and item["tags"] == ["Referral"]
    assert len(item["form_questions"]) == 4


def test_status_edit_api(jobs, client):
    assert client.post("/api/statuses", json={"name": "Paused"}).status_code >= 400
    created = client.post("/api/statuses", json={"name": "Paused", "ends": False}).json()
    assert created["status"]["ends"] is False
    status_id = created["status"]["id"]
    assert client.post(f"/api/statuses/{status_id}", json={"retired": True}).json()[
        "status"]["retired"] is True
    assert client.post(f"/api/statuses/{status_id}", json={}).status_code == 400


def test_applications_counter_counts_open_applications(jobs, client, cli):
    assert client.get("/api/state").json()["header"]["counts"]["applications"] == 2
    cli("applications", "set-status", jobs["finlima"], "--to", "rejected")
    assert client.get("/api/state").json()["header"]["counts"]["applications"] == 1


def test_a_work_mode_correction_is_in_the_applications_history(jobs):
    with db.session(jobs["home"]) as conn:
        from jobtracker.core import search

        search.set_work_mode(conn, jobs["postings"]["A-101"], "hybrid", "Fridays from home")
    item = detail(jobs["home"], jobs["finlima"])
    events = [e for e in item["history"] if e["kind"] == "work_mode"]
    assert events and events[0]["data"]["to"] == {"mode": "hybrid", "detail": "Fridays from home"}
    assert item["posting"]["work_mode_detail"] == "Fridays from home"


# ── migration 0012: stages become "ends" ──────────────────────────────────

def test_migration_turns_stages_into_ends(jobs, cli):
    import sqlite3
    from contextlib import closing

    from tests.migrations import rewind

    home, job = jobs["home"], jobs["altamar"]
    cli("applications", "set-status", job, "--to", "applied")
    stages = ("to_apply", "applied", "interview", "offer", "closed_positive", "closed_negative")
    for stage in stages:
        cli("applications", "statuses", "create", f"Custom {stage}", "--ends", "no")
    rewind(home.database, 11)
    with closing(sqlite3.connect(home.database)) as conn:
        assert "stage" in [r[1] for r in conn.execute("PRAGMA table_info(statuses)")]
        for stage in stages:
            conn.execute("UPDATE statuses SET stage = ? WHERE name_en = ?",
                         (stage, f"Custom {stage}"))
        conn.execute(  # an event written before this change, with stages and no names
            "INSERT INTO events (entity_type, entity_id, kind, data, created_at) VALUES"
            " ('application', ?, 'status_changed', ?, '2026-11-02T10:00:00Z')",
            (job, json.dumps({"from": "applied", "to": "Custom closed_negative",
                              "from_stage": "applied", "to_stage": "closed_negative"})))
        conn.commit()
    with db.session(home) as conn:
        columns = [r[1] for r in conn.execute("PRAGMA table_info(statuses)")]
        assert "stage" not in columns and "ends" in columns
        ends = {r["name_en"]: bool(r["ends"]) for r in conn.execute(
            "SELECT name_en, ends FROM statuses WHERE key IS NULL")}
        assert ends == {f"Custom {s}": s.startswith("closed") for s in stages}
        builtin = {r["key"]: bool(r["ends"]) for r in conn.execute(
            "SELECT key, ends FROM statuses WHERE key IS NOT NULL")}
        assert [k for k, v in builtin.items() if v] == [
            "accepted", "rejected", "ghosted", "offer_declined", "no_economic_alignment",
            "withdrawn"]
        old = next(h for h in applications.history(conn, job)
                   if h["kind"] == "status_changed" and "to_stage" in h["data"])
        assert (old["data"]["from_name"], old["data"]["to_name"]) == (
            "Applied", "Custom closed_negative")
