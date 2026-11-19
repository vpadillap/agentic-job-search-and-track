"""Searches of the same day on one page (`group-searches-by-day`): joining, the merged
page, and the one-time offer to group earlier searches. Fictional data only."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from jobtracker.core import db, offers, search
from jobtracker.web.app import create_app
from tests.test_search import captures


@pytest.fixture
def client():
    return TestClient(create_app(), base_url="http://127.0.0.1:8000")


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _start(cli, *extra: str) -> dict:
    code, run, _ = cli("run", "start", *extra)
    assert code == 0, run
    return run


def _backdate(paths, run_id: int, days: int) -> None:
    """Move a run (and the page it opened) `days` earlier, as if made on that day."""
    with db.session(paths) as conn:
        row = conn.execute("SELECT started_at FROM search_runs WHERE id = ?", (run_id,)).fetchone()
        moment = datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
        earlier = _iso(moment - timedelta(days=days))
        conn.execute("UPDATE search_runs SET started_at = ?, finished_at = ? WHERE id = ?",
                     (earlier, earlier, run_id))
        conn.execute("UPDATE search_groups SET started_at = ? WHERE id ="
                     " (SELECT group_id FROM search_runs WHERE id = ?)", (earlier, run_id))


# ── joining ───────────────────────────────────────────────────────────────

def test_second_search_the_same_day_joins_the_page(searchable, cli):
    first = _start(cli)
    second = _start(cli)
    assert second["group"]["id"] == first["group"]["id"]
    assert second["group"]["runs"] == [first["run_id"], second["run_id"]]


def test_next_day_starts_a_page_unless_asked_to_join(searchable, cli):
    first = _start(cli)
    _backdate(searchable, first["run_id"], 1)
    today = _start(cli)
    assert today["group"]["id"] != first["group"]["id"]
    joined = _start(cli, "--group", str(first["group"]["id"]))
    assert joined["group"]["id"] == first["group"]["id"]
    assert joined["group"]["first_day"] < joined["group"]["last_day"]


def test_new_group_keeps_the_same_day_apart(searchable, cli):
    first = _start(cli)
    apart = _start(cli, "--new-group")
    assert apart["group"]["id"] != first["group"]["id"]


def test_group_and_new_group_together_are_refused(searchable, cli):
    code, out, _ = cli("run", "start", "--group", "1", "--new-group")
    assert code == 2 and out["error"]["code"] == "usage"


def test_unknown_or_demo_group_is_refused(searchable, cli):
    code, out, _ = cli("run", "start", "--group", "999")
    assert code == 1 and out["error"]["code"] == "not_found"
    with db.session(searchable) as conn:
        demo_run = search.start_run(conn, searchable, 7, demo=True, demo_providers=[],
                                    demo_titles=["Demo"])
    code, out, _ = cli("run", "start", "--group", str(demo_run["group"]["id"]))
    assert code == 1 and out["error"]["code"] == "invalid_group"


def test_demo_runs_stay_apart_from_real_ones(searchable, cli):
    real = _start(cli)
    with db.session(searchable) as conn:
        demo_run = search.start_run(conn, searchable, 7, demo=True, demo_providers=[],
                                    demo_titles=["Demo"])
    assert demo_run["group"]["id"] != real["group"]["id"]


# ── one page ──────────────────────────────────────────────────────────────

def _import(cli, tmp_path, run: dict, records: list[dict], name: str) -> None:
    path = tmp_path / name
    path.write_text(json.dumps(records), encoding="utf-8")
    code, out, _ = cli("postings", "import", str(run["run_id"]), str(path))
    assert code == 0, out
    cli("run", "finish", str(run["run_id"]))


def test_two_searches_of_one_day_show_on_one_page(searchable, cli, client, tmp_path):
    records = captures()
    first = _start(cli)
    _import(cli, tmp_path, first, records[:2], "a.json")
    second = _start(cli)
    _import(cli, tmp_path, second, records, "b.json")            # the first two again
    board = client.get("/api/search").json()
    ids = [r["id"] for r in board["results"]]
    assert len(ids) == len(set(ids))                               # each posting once
    with db.session(searchable) as conn:
        one = search.summary(conn, first["run_id"])
        two = search.summary(conn, second["run_id"])
    page = board["run"]
    assert page["run_count"] == 2 and [r["id"] for r in page["runs"]] == [
        first["run_id"], second["run_id"]]
    for key in ("found", "new", "filtered", "duplicate_or_seen"):
        assert page["counts"][key] == one["counts"][key] + two["counts"][key]
    assert len(ids) == one["counts"]["new"] + two["counts"]["new"]
    for item in page["providers"]:
        assert item["found"] == sum(p["found"] for s in (one, two) for p in s["providers"]
                                    if p["id"] == item["id"])
    assert board["runs"][0]["run_count"] == 2 and len(board["runs"]) == 1


def test_earlier_page_and_run_parameter(searchable, cli, client, tmp_path):
    first = _start(cli)
    _import(cli, tmp_path, first, captures()[:1], "a.json")
    _backdate(searchable, first["run_id"], 2)
    second = _start(cli)
    _import(cli, tmp_path, second, captures()[1:2], "b.json")
    board = client.get("/api/search").json()
    assert board["run"]["id"] == second["group"]["id"] and len(board["runs"]) == 2
    earlier = client.get(f"/api/search?group={first['group']['id']}").json()
    assert [r["id"] for r in earlier["run"]["runs"]] == [first["run_id"]]
    by_run = client.get(f"/api/search?run={first['run_id']}").json()
    assert by_run["run"]["id"] == first["group"]["id"]


# ── the one-time offer ────────────────────────────────────────────────────

def _offer():
    return next(o for o in offers.REGISTRY if o.id == "group-searches-by-day")


def _pages_by_day(searchable, cli, layout: list[int]) -> list[dict]:
    """Runs on separate pages (as before this change); `layout` gives each run's age in
    days."""
    runs = []
    for age in layout:
        run = _start(cli, "--new-group")
        if age:
            _backdate(searchable, run["run_id"], age)
        runs.append(run)
    return runs


def test_offer_applies_only_when_a_day_has_several_pages(searchable, cli):
    _pages_by_day(searchable, cli, [2, 1])
    with db.session(searchable) as conn:
        assert not _offer().applies(conn, searchable)
    _pages_by_day(searchable, cli, [0, 0])
    with db.session(searchable) as conn:
        assert _offer().applies(conn, searchable)


def test_accepting_groups_each_day_and_removes_empty_pages(searchable, cli):
    runs = _pages_by_day(searchable, cli, [3, 3, 1, 0, 0])
    code, out, _ = cli("offers", "accept", "group-searches-by-day")
    assert code == 0 and out["result"] == {"days_grouped": 2, "pages_removed": 2}
    with db.session(searchable) as conn:
        group = {r["id"]: r["group_id"] for r in conn.execute(
            "SELECT id, group_id FROM search_runs")}
        assert conn.execute("SELECT COUNT(*) FROM search_groups").fetchone()[0] == 3
    ids = [r["run_id"] for r in runs]
    assert group[ids[0]] == group[ids[1]] != group[ids[2]]
    assert group[ids[3]] == group[ids[4]] != group[ids[2]]
    _, out, _ = cli("offers", "list")
    assert out["offers"] == []                                     # answered: not again


def test_accepting_keeps_demo_runs_and_seasons_apart(searchable, cli):
    real = _start(cli, "--new-group")
    with db.session(searchable) as conn:
        demo_run = search.start_run(conn, searchable, 7, demo=True, demo_providers=[],
                                    demo_titles=["Demo"])
        search.group_past_by_day(conn)
        row = {r["id"]: r["group_id"] for r in conn.execute("SELECT id, group_id FROM search_runs")}
    assert row[real["run_id"]] != row[demo_run["run_id"]]


def test_accepting_never_splits_days_the_user_joined(searchable, cli):
    first = _start(cli)
    _backdate(searchable, first["run_id"], 1)
    joined = _start(cli, "--group", str(first["group"]["id"]))
    with db.session(searchable) as conn:
        search.group_past_by_day(conn)
        groups = {r["group_id"] for r in conn.execute("SELECT group_id FROM search_runs")}
    assert groups == {joined["group"]["id"]}


def test_existing_runs_keep_their_own_pages_after_the_migration(searchable, cli, tmp_path):
    from tests.migrations import rewind

    _start(cli)
    _start(cli)
    rewind(searchable.database, 16)
    with db.session(searchable) as conn:                            # migrates again
        pages = conn.execute("SELECT COUNT(*) FROM search_groups").fetchone()[0]
        runs = conn.execute("SELECT COUNT(*) FROM search_runs").fetchone()[0]
        assert pages == runs == 2
        assert _offer().applies(conn, searchable)
