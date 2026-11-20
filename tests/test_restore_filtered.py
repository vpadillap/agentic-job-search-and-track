"""Restoring a filtered-out posting (job-search-location-filter): it returns to the
results unscored, is never filtered again, waits for its score as pending work, and is
a correction of the filter in the agent's history. Fictional data only."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jobtracker.core import db, insights, refresh, search
from jobtracker.web.app import create_app
from tests.test_scoring import submission
from tests.test_search import captures


@pytest.fixture
def write_json(tmp_path):
    def write(data, name="input.json") -> str:
        path = tmp_path / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return str(path)
    return write


@pytest.fixture
def client():
    return TestClient(create_app(), base_url="http://127.0.0.1:8000")


@pytest.fixture
def filtered(searchable, cli, write_json):
    """A run with one posting filtered out for its location; the run still open."""
    _, run, _ = cli("run", "start")
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    posting = next(p["posting_id"] for p in report["postings"] if p["outcome"] == "new")
    code, out, _ = cli("postings", "filter", str(run["run_id"]), write_json(
        [{"posting_id": posting, "reason": "location", "detail": "Onsite in Arequipa"}],
        "filter.json"))
    assert code == 0, out
    return {"run_id": run["run_id"], "posting_id": posting}


def _outcome(cli, run_id: int, posting_id: int) -> dict:
    _, out, _ = cli("postings", "list", "--run", str(run_id))
    return next(p for p in out["postings"] if p["id"] == posting_id)


def test_restore_returns_the_posting_unscored(filtered, cli):
    code, out, _ = cli("postings", "restore", str(filtered["posting_id"]))
    assert code == 0, out
    assert out["restored"] == [filtered["posting_id"]]
    item = _outcome(cli, filtered["run_id"], filtered["posting_id"])
    assert item["outcome"] == "new" and item["reason"] is None and item["score"] is None
    assert item["restored"] is True


def test_a_restored_posting_is_never_filtered_again(filtered, cli, write_json):
    cli("postings", "restore", str(filtered["posting_id"]))
    code, out, _ = cli("postings", "filter", str(filtered["run_id"]), write_json(
        [{"posting_id": filtered["posting_id"], "reason": "location"}], "again.json"))
    assert code != 0 and out["error"]["code"] == "restored_by_user"


def test_only_filtered_postings_can_be_restored(filtered, cli):
    cli("postings", "restore", str(filtered["posting_id"]))
    code, out, _ = cli("postings", "restore", str(filtered["posting_id"]))
    assert code != 0 and out["error"]["code"] == "not_filtered"


def test_other_postings_are_not_marked_restored(filtered, cli):
    _, out, _ = cli("postings", "list", "--run", str(filtered["run_id"]), "--outcome", "new")
    assert out["postings"] and all(p["restored"] is False for p in out["postings"])


def test_restore_from_the_panel(filtered, client):
    answer = client.post("/api/actions/restore-filtered",
                         json={"posting_ids": [filtered["posting_id"]]})
    assert answer.status_code == 200 and answer.json()["posting_ids"] == [filtered["posting_id"]]
    board = client.get("/api/search").json()
    assert filtered["posting_id"] in [r["id"] for r in board["results"]]
    assert filtered["posting_id"] not in [p["id"] for p in board["filtered"]]


def _score_items(cli) -> list[dict]:
    _, out, _ = cli("pending")
    return [i for i in out["pending"] if i["kind"] == "score"]


def test_restored_posting_is_pending_only_once_the_search_is_finished(filtered, cli,
                                                                     write_json):
    cli("postings", "restore", str(filtered["posting_id"]))
    assert _score_items(cli) == []                          # the running search scores it
    cli("run", "finish", str(filtered["run_id"]))
    items = _score_items(cli)
    assert [i["posting_id"] for i in items] == [filtered["posting_id"]]
    code, out, _ = cli("score", "set", str(filtered["posting_id"]),
                       write_json(submission(), "score.json"))
    assert code == 0, out
    assert _score_items(cli) == []


def test_restore_is_a_filter_correction_in_the_history(filtered, cli, searchable):
    cli("postings", "restore", str(filtered["posting_id"]))
    with db.session(searchable) as conn:
        found = [c for c in insights.corrections(conn) if c["field"] == "filter"]
        assert found == [{
            "posting_id": filtered["posting_id"], "field": "filter",
            "provider": found[0]["provider"], "title": found[0]["title"],
            "company": found[0]["company"], "agent_value": None,
            "from": {"outcome": "filtered", "reason": "location",
                     "detail": "Onsite in Arequipa"},
            "to": {"outcome": "new"}, "on": found[0]["on"]}]
        assert search.is_restored(conn, filtered["posting_id"])
        written = refresh.write_history(conn, searchable)
    lines = Path(written["path"]).read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert any(r["type"] == "correction" and r["field"] == "filter"
               and r["from"]["reason"] == "location" for r in records)
