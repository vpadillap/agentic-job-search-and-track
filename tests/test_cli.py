"""Scenarios of the `agent-data-interface` spec."""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

from jobtracker.core import db, doctor

REPO = Path(__file__).resolve().parent.parent


def _user_version(path: Path) -> int:
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute("PRAGMA user_version").fetchone()[0]


# ── machine-readable output ───────────────────────────────────────────────

def test_successful_command_emits_one_json_document(workspace, cli):
    code, out, _ = cli("context")
    assert code == 0
    assert out["ok"] is True


def test_failed_command_reports_code_and_message(home, cli):
    code, out, err = cli("rules", "list")
    assert code == 1
    assert out["ok"] is False
    assert out["error"]["code"] == "not_initialized"
    assert out["error"]["message"]
    assert "error:" in err


def test_usage_error_is_json_too(home, cli):
    code, out, _ = cli("no-such-command")
    assert code == 2
    assert out["error"]["code"] == "usage"


def test_runs_from_the_clone_without_installation(tmp_path):
    env = {"JOBTRACKER_HOME": str(tmp_path / "home"), "PATH": "", "SYSTEMROOT": "C:\\Windows"}
    result = subprocess.run(
        [sys.executable, "-S", str(REPO / "scripts" / "jt.py"), "doctor"],
        capture_output=True, text=True, env=env, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["ok"] is True
    # -S hides installed packages: the report must name them instead of crashing.
    assert any(c["id"] == "package:fastapi" and c["status"] == "fail" for c in report["checks"])


# ── diagnostics ───────────────────────────────────────────────────────────

def test_doctor_on_a_fresh_clone(home, cli):
    code, out, _ = cli("doctor")
    assert code == 0
    assert out["initialized"] is False
    assert out["healthy"] is False
    failing = {c["id"]: c for c in out["checks"] if c["status"] == "fail"}
    assert "workspace" in failing
    assert all(check.get("fix") for check in failing.values())
    assert not home.home.exists()  # diagnostics change nothing


def test_doctor_on_a_healthy_installation(workspace, cli, monkeypatch):
    monkeypatch.setattr(doctor.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, ".githooks\n", ""))
    _, out, _ = cli("doctor")
    assert [c for c in out["checks"] if c["status"] != "pass"] == []
    assert out["healthy"] is True
    assert out["schema_version"] == db.current_schema_version()


def test_doctor_reports_missing_provider_tools(workspace, cli, tmp_path, monkeypatch):
    providers_dir = tmp_path / "providers"
    providers_dir.mkdir()
    (providers_dir / "demo.md").write_text(
        "---\nid: demo\ndependencies: [surely-not-installed-tool]\n---\n", encoding="utf-8")
    monkeypatch.setattr("jobtracker.core.providers.providers_dir", lambda: providers_dir)
    _, out, _ = cli("doctor")
    check = next(c for c in out["checks"] if c["id"] == "provider:demo")
    assert check["status"] == "fail"
    assert "surely-not-installed-tool" in check["detail"]
    assert "demo.md" in check["fix"]


# ── migrations ────────────────────────────────────────────────────────────

def test_older_database_is_backed_up_then_migrated(workspace, cli, tmp_path, monkeypatch):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    for path in db.MIGRATIONS_DIR.glob("*.sql"):
        (migrations / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    (migrations / "0002_test.sql").write_text("CREATE TABLE extra (id INTEGER);", encoding="utf-8")
    monkeypatch.setattr(db, "MIGRATIONS_DIR", migrations)

    assert list(workspace.backups.iterdir()) == []
    code, _, _ = cli("rules", "list")
    assert code == 0
    assert _user_version(workspace.database) == 2
    backups = list(workspace.backups.glob("jobtracker-v0001-*.db"))
    assert len(backups) == 1
    assert _user_version(backups[0]) == 1


def test_failed_migration_leaves_the_database_unchanged(workspace, cli, tmp_path, monkeypatch):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    for path in db.MIGRATIONS_DIR.glob("*.sql"):
        (migrations / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    (migrations / "0002_bad.sql").write_text(
        "CREATE TABLE half (id INTEGER);\nTHIS IS NOT SQL;", encoding="utf-8")
    monkeypatch.setattr(db, "MIGRATIONS_DIR", migrations)

    code, out, _ = cli("rules", "list")
    assert code == 1
    assert out["ok"] is False
    assert _user_version(workspace.database) == 1
    with closing(sqlite3.connect(workspace.database)) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "half" not in tables


def test_newer_database_is_refused_untouched(workspace, cli):
    with closing(sqlite3.connect(workspace.database)) as conn:
        conn.execute("PRAGMA user_version = 999")
        conn.commit()
    code, out, _ = cli("rules", "list")
    assert code == 1
    assert out["error"]["code"] == "schema_too_new"
    assert "update" in out["error"]["message"].lower()
    assert _user_version(workspace.database) == 999
    assert list(workspace.backups.iterdir()) == []


# ── context ───────────────────────────────────────────────────────────────

def test_context_before_setup(home, cli):
    code, out, _ = cli("context")
    assert code == 0
    assert out["setup_required"] is True
    assert out["profile"] is None
    assert not home.home.exists()


def test_context_on_an_initialized_workspace(workspace, cli):
    cli("config", "set", "language", "es")
    _, out, _ = cli("context")
    assert out["initialized"] is True
    assert out["language"] == "es"
    assert out["season"]["number"] == 1
    keys = {rule["key"] for rule in out["rules"] if rule["origin"] == "system"}
    assert {"salary_evidence", "truthful_documents", "no_auto_apply"} <= keys
    assert out["profile"] is None and out["setup_required"] is True


# ── validated writes ──────────────────────────────────────────────────────

def test_user_rule_is_stored_and_listed(workspace, cli):
    code, out, _ = cli("rules", "add", "--text", "No outsourcing consultancies",
                       "--area", "search")
    assert code == 0
    assert out["rules"][0]["origin"] == "user"
    assert out["rules"][0]["status"] == "active"
    _, context, _ = cli("context")
    assert "No outsourcing consultancies" in [r["text"] for r in context["rules"]]


def test_invalid_batch_is_rejected_atomically(workspace, cli, tmp_path):
    batch = tmp_path / "rules.json"
    batch.write_text(json.dumps([
        {"text": "Prefer product companies", "area": "search"},
        {"text": "", "area": "search"},
        {"text": "Cover letter only when asked", "area": "cover_letter"},
    ]), encoding="utf-8")
    _, before, _ = cli("rules", "list", "--status", "all")

    code, out, _ = cli("rules", "import", str(batch))
    assert code == 1
    assert out["error"]["code"] == "invalid_rule"
    assert out["error"]["details"]["index"] == 1
    _, after, _ = cli("rules", "list", "--status", "all")
    assert after["rules"] == before["rules"]


def test_valid_batch_is_stored(workspace, cli, tmp_path):
    batch = tmp_path / "rules.json"
    batch.write_text(json.dumps([
        {"text": "Prefer product companies", "area": "search"},
        {"text": "Lower priority of BI titles", "area": "score", "origin": "learned",
         "evidence": "7 applications, 0 interviews", "effect": {"title_priority": -1}},
    ]), encoding="utf-8")
    code, out, _ = cli("rules", "import", str(batch))
    assert code == 0
    assert [r["status"] for r in out["rules"]] == ["active", "proposed"]
    assert out["rules"][1]["effect"] == {"title_priority": -1}


def test_learned_rules_cannot_be_created_active(workspace, cli):
    code, out, _ = cli("rules", "add", "--text", "x", "--origin", "learned")
    assert code == 0 and out["rules"][0]["status"] == "proposed"
    code, out, _ = cli("rules", "add", "--text", "x", "--origin", "system")
    assert code == 1


def test_system_rules_are_not_duplicated_on_reinit(workspace, cli):
    _, first, _ = cli("rules", "list")
    cli("init")
    _, second, _ = cli("rules", "list")
    assert first["rules"] == second["rules"]


def test_invalid_config_is_rejected(workspace, cli):
    code, out, _ = cli("config", "set", "host", "0.0.0.0")
    assert code == 1
    assert out["error"]["code"] == "invalid_config"
    _, shown, _ = cli("config", "show")
    assert shown["config"]["host"] == "127.0.0.1"
