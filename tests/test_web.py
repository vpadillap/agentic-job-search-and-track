"""The panel sees what the CLI writes, while both use the same database."""
from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

from jobtracker.core import db, rules
from jobtracker.web.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app(), base_url="http://127.0.0.1:8000")


def test_health_before_setup(home, client):
    body = client.get("/api/health").json()
    assert body["initialized"] is False
    assert body["schema_version"] is None


def test_changes_before_setup_is_a_clear_error(home, client):
    response = client.get("/api/changes")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_initialized"


def test_cli_write_is_visible_to_the_running_panel(workspace, cli, client):
    assert client.get("/api/health").json()["initialized"] is True
    before = client.get("/api/changes").json()["counter"]
    code, _, _ = cli("rules", "add", "--text", "Prefer remote roles", "--area", "search")
    assert code == 0
    assert client.get("/api/changes").json()["counter"] == before + 1


def test_concurrent_writers_do_not_lose_data(workspace):
    errors: list[Exception] = []

    def writer(index: int) -> None:
        try:
            for step in range(5):
                with db.session(workspace) as conn:
                    rules.add_rules(conn, [{"text": f"rule {index}-{step}"}])
        except Exception as error:  # pragma: no cover - reported below
            errors.append(error)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    with db.session(workspace) as conn:
        assert len(rules.list_rules(conn, "active")) == len(rules.SYSTEM_RULES) + 20
        assert db.change_state(conn)["counter"] == 20
