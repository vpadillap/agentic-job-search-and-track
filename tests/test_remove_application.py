"""Removing an application from tracking (application-tracking, applications-board)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from jobtracker.core import db, tracking
from jobtracker.web.app import create_app
from tests.test_applications import jobs  # noqa: F401  (fixture)


@pytest.fixture
def client():
    return TestClient(create_app(), base_url="http://127.0.0.1:8000")


def _folder(home, job_id):
    return next(home.applications.glob(f"{job_id}-*"))


def _with_files(home, cli, job_id):
    _, made, _ = cli("documents", "path", job_id, "--kind", "cover-letter", "--ext", "md")
    from pathlib import Path

    Path(made["path"]).write_text("Fictional letter.", encoding="utf-8")
    return _folder(home, job_id)


def test_removal_drops_the_application_and_deletes_its_folder(jobs, cli):  # noqa: F811
    home, job = jobs["home"], jobs["altamar"]
    cli("applications", "tag", job, "--add", "priority")
    cli("applications", "set-status", job, "--to", "applied")
    folder = _with_files(home, cli, job)
    other = _with_files(home, cli, jobs["finlima"])
    (home.profile / "keep.txt").write_text("base", encoding="utf-8")

    code, out, _ = cli("applications", "remove", job)
    assert code == 0, out
    assert out == {"ok": True, "job_ids": [job], "folders_deleted": 1}
    assert not folder.exists()
    assert other.is_dir() and (home.profile / "keep.txt").is_file()
    code, out, _ = cli("applications", "show", job)
    assert code == 1 and out["error"]["code"] == "not_found"
    with db.session(home) as conn:
        assert conn.execute("SELECT COUNT(*) FROM application_tags").fetchone()[0] == 0
        assert tracking.application(conn, jobs["postings"]["A-100"]) is None
        kinds = [r[0] for r in conn.execute(
            "SELECT kind FROM events WHERE entity_type = 'posting' AND entity_id = ?",
            (str(jobs["postings"]["A-100"]),))]
    assert kinds[-1] == "untracked"


def test_a_missing_folder_is_not_an_error(jobs, cli):  # noqa: F811
    code, out, _ = cli("applications", "remove", jobs["finlima"])
    assert code == 0 and out["folders_deleted"] == 0


def test_tracking_again_gives_a_new_job_id(jobs, cli):  # noqa: F811
    home, job = jobs["home"], jobs["altamar"]
    cli("applications", "remove", job)
    with db.session(home) as conn:
        again = tracking.track(conn, [jobs["postings"]["A-100"]])[0]
        assert again["job_id"] != job and again["job_id"] != jobs["finlima"]
        assert again["status"] == "new"


def test_unknown_job_id(jobs, cli):  # noqa: F811
    code, out, _ = cli("applications", "remove", "J9999")
    assert code == 1 and out["error"]["code"] == "not_found"


def test_removal_through_the_api(jobs, cli, client):  # noqa: F811
    home, job = jobs["home"], jobs["altamar"]
    folder = _with_files(home, cli, job)
    response = client.post("/api/applications/remove", json={"job_ids": [job]})
    assert response.json() == {"ok": True, "job_ids": [job], "folders_deleted": 1}
    assert not folder.exists()
    listed = client.get("/api/applications").json()
    assert job not in {a["job_id"] for a in listed["applications"]}


def test_a_folder_outside_applications_is_never_deleted(jobs):  # noqa: F811
    home = jobs["home"]
    outside = home.profile
    outside.mkdir(parents=True, exist_ok=True)
    with pytest.raises(Exception) as error:
        tracking.delete_folders(home, [str(outside)])
    assert getattr(error.value, "code", None) == "forbidden_path"
    assert outside.is_dir()
