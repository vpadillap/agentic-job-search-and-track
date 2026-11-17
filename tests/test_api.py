"""Panel API: local-only access, board data, row actions, settings."""
from __future__ import annotations

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from jobtracker.core import config, db, demo
from jobtracker.web.app import create_app, host_name
from tests.test_search import captures


@pytest.fixture
def client():
    return TestClient(create_app(), base_url="http://127.0.0.1:8000")


@pytest.fixture
def seeded(home):
    demo.seed(home)
    return home


def latest(client) -> dict:
    return client.get("/api/search").json()


def row(board: dict, company: str, provider: str | None = None) -> dict:
    return next(r for r in board["results"]
                if r["company"] == company and (provider is None or r["provider"] == provider))


# ── local only ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("host", ["127.0.0.1:8000", "localhost:8000", "[::1]:8000", "localhost"])
def test_loopback_hosts_are_served(home, host):
    response = TestClient(create_app()).get("/api/health", headers={"host": host})
    assert response.status_code == 200


@pytest.mark.parametrize("host", ["evil.example:8000", "192.168.1.20:8000", "127.0.0.1.nip.io",
                                  "testserver", ""])
def test_other_host_names_are_rejected(home, host):
    response = TestClient(create_app()).get("/api/health", headers={"host": host})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_host"


def test_host_name_parsing():
    assert host_name("[::1]:8000") == "::1"
    assert host_name("LOCALHOST:8000") == "localhost"
    assert host_name("::1") == "::1"


def test_security_headers(home, client):
    response = client.get("/")
    assert response.status_code == 200
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_static_files_are_served(home, client):
    assert client.get("/static/vendor/preact-htm.js").status_code == 200
    assert client.get("/static/locales/es.json").json()["brand"] == "Radar de Empleo"


# ── state and board ───────────────────────────────────────────────────────

def test_state_before_setup(home, client):
    body = client.get("/api/state").json()
    assert body["initialized"] is False and body["setup_required"] is True
    assert any(c["command"] == "/setup" for c in body["commands"])


def test_state_with_demo_data(seeded, client):
    body = client.get("/api/state").json()
    assert body["initialized"] is True
    counts = body["header"]["counts"]
    assert counts == {"search": 8, "applications": 2}      # 10 new - 1 tracked - 1 dismissed
    assert body["changes"]["counter"] > 0


def test_search_board_shows_the_latest_run(seeded, client):
    board = latest(client)
    run = board["run"]
    assert run["counts"]["new"] == 10 and run["counts"]["filtered"] == 3
    assert run["counts"]["duplicate_or_seen"] == 2
    assert [s["id"] for s in run["skipped"]] == ["glassdoor"]
    assert len(board["runs"]) == 2
    assert {f["reason"] for f in board["filtered"]} == {"location", "title", "contract_type"}


def test_rows_carry_score_salary_and_detail(seeded, client):
    board = latest(client)
    top = row(board, "Altamar Retail")
    assert top["score"]["total"] == 86
    assert len(top["score"]["components"]) == 5
    assert top["salary"]["status"] == "suggested" and top["salary"]["source_count"] == 3
    assert all(e["url"].startswith("https://example.com/") for e in top["salary"]["evidence"])
    assert top["description"].startswith("Altamar Retail busca")
    assert top["form_question_count"] == 4
    no_data = row(board, "Nortia Seguros")
    assert no_data["salary"]["status"] == "no_data" and no_data["salary"]["amount"] is None
    unresearched = row(board, "Vértiz Salud")
    assert unresearched["salary"] is None and unresearched["flags"]


def test_possible_duplicates_are_marked_on_separate_rows(seeded, client):
    board = latest(client)
    linkedin = row(board, "Altamar Retail", "linkedin")
    indeed = row(board, "Altamar Retail S.A.C.", "indeed")
    assert linkedin["id"] != indeed["id"]
    assert [d["provider"] for d in linkedin["possible_duplicates"]] == ["indeed"]
    assert [d["provider"] for d in indeed["possible_duplicates"]] == ["linkedin"]


def test_earlier_run(seeded, client):
    board = latest(client)
    earlier = board["runs"][-1]["id"]
    old = client.get(f"/api/search?run={earlier}").json()
    assert old["run"]["id"] == earlier
    assert {r["company"] for r in old["results"]} == {"Kallpa Energía", "Inti Bank"}


def test_unknown_run_is_404(seeded, client):
    assert client.get("/api/search?run=999").status_code == 404


def test_default_minimum_score_comes_from_active_rules(seeded, client):
    assert latest(client)["default_min_score"] is None
    with db.session(seeded) as conn:
        conn.execute(
            "INSERT INTO rules (origin, status, area, text, effect, created_at, updated_at)"
            " VALUES ('user', 'active', 'search', 'Hide weak matches', ?, 'x', 'x')",
            (json.dumps({"min_score_shown": 60}),))
    assert latest(client)["default_min_score"] == 60


# ── actions ───────────────────────────────────────────────────────────────

def test_track_creates_the_application_and_marks_the_row(seeded, client):
    target = row(latest(client), "Mistral Pagos")
    body = client.post("/api/actions/track", json={"posting_ids": [target["id"]]}).json()
    assert body["applications"][0]["status"] == "new"
    assert body["applications"][0]["job_id"].startswith("J")
    assert row(latest(client), "Mistral Pagos")["application"]["status"] == "new"


def test_track_and_mark_applied_sets_today(seeded, client):
    target = row(latest(client), "Quena Labs")
    body = client.post("/api/actions/track",
                       json={"posting_ids": [target["id"]], "applied": True}).json()
    application = body["applications"][0]
    assert application["status"] == "applied"
    assert application["applied_on"] == datetime.now().date().isoformat()


def test_bulk_track(seeded, client):
    board = latest(client)
    ids = [row(board, "Mistral Pagos")["id"], row(board, "Cobre Logística")["id"]]
    client.post("/api/actions/track", json={"posting_ids": ids})
    board = latest(client)
    assert all(r["application"] for r in board["results"] if r["id"] in ids)
    with db.session(seeded) as conn:
        job_ids = [r[0] for r in conn.execute("SELECT job_id FROM applications ORDER BY id")]
    assert len(job_ids) == len(set(job_ids)) == 4


def test_undo_track_does_not_reuse_the_job_id(seeded, client):
    target = row(latest(client), "Mistral Pagos")["id"]
    first = client.post("/api/actions/track", json={"posting_ids": [target]}).json()
    client.post("/api/actions/untrack", json={"posting_ids": [target]})
    assert row(latest(client), "Mistral Pagos")["application"] is None
    second = client.post("/api/actions/track", json={"posting_ids": [target]}).json()
    assert first["applications"][0]["job_id"] != second["applications"][0]["job_id"]


def test_dismiss_with_reason_and_undo(seeded, client):
    target = row(latest(client), "Cobre Logística")["id"]
    response = client.post("/api/actions/dismiss",
                           json={"posting_ids": [target], "reason": "location"})
    assert response.status_code == 200
    dismissed = row(latest(client), "Cobre Logística")["dismissal"]
    assert dismissed["reason"] == "location"
    with db.session(seeded) as conn:
        kinds = [r[0] for r in conn.execute(
            "SELECT kind FROM events WHERE entity_type = 'posting' AND entity_id = ?",
            (str(target),))]
    assert "dismissed" in kinds
    client.post("/api/actions/undismiss", json={"posting_ids": [target]})
    assert row(latest(client), "Cobre Logística")["dismissal"] is None


def test_dismissal_reasons_are_validated(seeded, client):
    target = row(latest(client), "Cobre Logística")["id"]
    bad = client.post("/api/actions/dismiss", json={"posting_ids": [target], "reason": "meh"})
    assert bad.status_code == 422
    other = client.post("/api/actions/dismiss", json={"posting_ids": [target], "reason": "other"})
    assert other.status_code == 400
    ok = client.post("/api/actions/dismiss",
                     json={"posting_ids": [target], "reason": "other", "note": "Agency"})
    assert ok.status_code == 200


def test_dismissed_posting_is_not_new_in_a_later_search(searchable, client, cli, tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps(captures()), encoding="utf-8")
    _, run, _ = cli("run", "start")
    cli("postings", "import", str(run["run_id"]), str(path))
    cli("run", "finish", str(run["run_id"]))
    target = row(latest(client), "Finlima S.A.")["id"]
    client.post("/api/actions/dismiss", json={"posting_ids": [target], "reason": "location"})
    _, run2, _ = cli("run", "start")
    _, report, _ = cli("postings", "import", str(run2["run_id"]), str(path))
    assert report["new"] == 0
    assert all(r["company"] != "Finlima S.A." for r in latest(client)["results"])


def test_tracked_rows_cannot_be_dismissed_and_dismissed_cannot_be_tracked(seeded, client):
    board = latest(client)
    tracked = row(board, "Finlima S.A.")["id"]
    dismissed = row(board, "Pukara Foods")["id"]
    assert client.post("/api/actions/dismiss",
                       json={"posting_ids": [tracked], "reason": "stack"}).status_code == 400
    assert client.post("/api/actions/track",
                       json={"posting_ids": [dismissed]}).status_code == 400


def test_actions_bump_the_change_counter(seeded, client):
    before = client.get("/api/changes").json()["counter"]
    target = row(latest(client), "Mistral Pagos")["id"]
    client.post("/api/actions/track", json={"posting_ids": [target]})
    assert client.get("/api/changes").json()["counter"] == before + 1


def test_untrack_after_the_undo_window_is_refused(seeded, client):
    target = row(latest(client), "Mistral Pagos")["id"]
    client.post("/api/actions/track", json={"posting_ids": [target]})
    with db.session(seeded) as conn:
        conn.execute("UPDATE applications SET created_at = '2026-01-01T00:00:00Z'"
                     " WHERE posting_id = ?", (target,))
    response = client.post("/api/actions/untrack", json={"posting_ids": [target]})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "undo_expired"


def test_missing_posting_is_404(seeded, client):
    assert client.post("/api/actions/track", json={"posting_ids": [9999]}).status_code == 404


# ── settings ──────────────────────────────────────────────────────────────

def test_language_switch_is_stored(seeded, client):
    body = client.post("/api/settings/language", json={"language": "es"}).json()
    assert body["language"] == "es"
    assert config.load(seeded.config)["language"] == "es"
    assert client.get("/api/state").json()["language"] == "es"


def test_language_switch_before_setup_is_refused(home, client):
    assert client.post("/api/settings/language", json={"language": "es"}).status_code == 409


def test_provider_toggle(workspace, client, providers_dir):
    body = client.post("/api/providers/alpha", json={"enabled": False}).json()
    alpha = next(p for p in body["providers"] if p["id"] == "alpha")
    assert alpha["enabled"] is False
    assert client.post("/api/providers/nope", json={"enabled": False}).status_code == 404


# ── agent report and panel agree ──────────────────────────────────────────

def test_run_report_matches_the_panel(searchable, client, cli, tmp_path):
    """End to end with fictional captures: what the agent reports is what the board shows."""
    path = tmp_path / "c.json"
    path.write_text(json.dumps(captures()), encoding="utf-8")
    _, run, _ = cli("run", "start")
    run_id = run["run_id"]
    cli("run", "provider", str(run_id), "gamma", "--status", "skipped", "--reason", "live_walk")
    _, report, _ = cli("postings", "import", str(run_id), str(path))
    onsite = next(p["posting_id"] for p in report["postings"] if p["external_id"] == "A-101")
    exclusions = tmp_path / "f.json"
    exclusions.write_text(json.dumps([{"posting_id": onsite, "reason": "work_mode"}]),
                          encoding="utf-8")
    cli("postings", "filter", str(run_id), str(exclusions))
    _, finished, _ = cli("run", "finish", str(run_id))
    agent = finished["run"]
    panel = latest(client)
    assert panel["run"]["counts"] == agent["counts"]
    assert panel["run"]["skipped"] == agent["skipped"]
    assert len(panel["results"]) == agent["counts"]["new"]
    assert len(panel["filtered"]) == agent["counts"]["filtered"]


def test_board_without_runs(workspace, client):
    body = latest(client)
    assert body["run"] is None and body["results"] == []


def test_demo_refuses_to_mix_with_real_data(searchable, cli, tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps(captures()[:1]), encoding="utf-8")
    _, run, _ = cli("run", "start")
    cli("postings", "import", str(run["run_id"]), str(path))
    code, out, _ = cli("demo", "seed")
    assert code == 1 and out["error"]["code"] == "has_real_data"


def test_demo_clear_removes_only_demo_rows(seeded, cli):
    code, out, _ = cli("demo", "clear")
    assert code == 0 and out["postings"] > 0
    with db.session(seeded) as conn:
        assert conn.execute("SELECT COUNT(*) FROM postings").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM search_runs").fetchone()[0] == 0
