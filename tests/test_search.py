"""job-search: runs, posting-age window, providers, identity, filtering, capture."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from jobtracker.core import db, search, tracking

CAPTURES = Path(__file__).parent / "fixtures" / "captures" / "search-run.json"


def captures(today: date | None = None) -> list[dict]:
    today = today or datetime.now().date()
    text = re.sub(r"\{today-(\d+)\}",
                  lambda m: (today - timedelta(days=int(m.group(1)))).isoformat(),
                  CAPTURES.read_text(encoding="utf-8"))
    return json.loads(text)["postings"]


@pytest.fixture
def write_json(tmp_path):
    def write(data, name="input.json") -> str:
        path = tmp_path / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return str(path)
    return write


def start(cli, *args) -> dict:
    code, out, _ = cli("run", "start", *args)
    assert code == 0, out
    return out


def by_external(report: dict) -> dict:
    return {item["external_id"]: item for item in report["postings"]}


# ── window, titles, providers ─────────────────────────────────────────────

def test_run_uses_included_titles_and_creates_the_capture_folder(searchable, cli):
    run = start(cli)
    assert run["posting_age_days"] == 7
    assert run["titles"] == ["Senior Data Engineer", "Data Platform Engineer"]
    assert Path(run["capture_folder"]).is_dir()
    assert Path(run["capture_folder"]).parent == searchable.searches
    assert sorted(run["to_search"]) == ["alpha", "beta", "gamma"]


def test_default_window_keeps_only_the_last_7_days(searchable, cli, write_json):
    run = start(cli)
    code, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    assert code == 0, report
    assert by_external(report)["A-102"]["outcome"] == "outside_window"
    assert report["outside_window"] == 1
    with db.session(searchable) as conn:
        stored = {r[0] for r in conn.execute("SELECT external_id FROM postings")}
    assert "A-102" not in stored


def test_custom_window(searchable, cli, write_json):
    run = start(cli, "--days", "3")
    assert run["posting_age_days"] == 3
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    outcomes = {k: v["outcome"] for k, v in by_external(report).items()}
    assert outcomes["A-101"] == "new"                       # 3 days old: inside
    assert outcomes["A-102"] == "outside_window"
    _, shown, _ = cli("run", "show", str(run["run_id"]))
    assert shown["run"]["posting_age_days"] == 3


def test_disabled_provider_is_not_searched(searchable, cli, write_json):
    cli("providers", "disable", "beta")
    run = start(cli)
    assert "beta" not in run["to_search"]
    code, out, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    assert code == 1 and "disabled" in out["error"]["message"]
    cli("postings", "import", str(run["run_id"]),
        write_json([p for p in captures() if p["provider"] != "beta"]))
    _, finished, _ = cli("run", "finish", str(run["run_id"]))
    beta = next(p for p in finished["run"]["providers"] if p["id"] == "beta")
    assert beta["status"] == "disabled" and beta["found"] == 0


def test_provider_needing_the_user_is_skipped_and_reported(searchable, cli, write_json):
    run = start(cli)
    gamma = next(p for p in run["providers"] if p["id"] == "gamma")
    assert gamma["live_walk"] is True
    code, _, _ = cli("run", "provider", str(run["run_id"]), "gamma", "--status", "skipped",
                     "--reason", "live_walk")
    assert code == 0
    cli("postings", "import", str(run["run_id"]), write_json(captures()))
    _, finished, _ = cli("run", "finish", str(run["run_id"]))
    summary = finished["run"]
    assert summary["status"] == "finished"
    assert [(s["id"], s["reason"]) for s in summary["skipped"]] == [("gamma", "live_walk")]
    assert summary["counts"]["new"] > 0


def test_a_failing_provider_does_not_fail_the_run(searchable, cli, write_json):
    run = start(cli)
    cli("run", "provider", str(run["run_id"]), "beta", "--status", "failed", "--reason", "error",
        "--detail", "timeout")
    cli("postings", "import", str(run["run_id"]),
        write_json([p for p in captures() if p["provider"] == "alpha"]))
    _, finished, _ = cli("run", "finish", str(run["run_id"]))
    assert finished["run"]["counts"]["new"] >= 1
    _, providers, _ = cli("providers", "list")
    beta = next(p for p in providers["providers"] if p["id"] == "beta")
    assert beta["last_status"] == "failed" and beta["last_error"] == "timeout"


# ── identity and memory ───────────────────────────────────────────────────

def test_same_url_twice_in_a_run_is_one_posting(searchable, cli, write_json):
    run = start(cli)
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    items = by_external(report)
    assert items["A-100-again"]["outcome"] == "duplicate"
    assert items["A-100-again"]["posting_id"] == items["A-100"]["posting_id"]
    _, shown, _ = cli("run", "show")
    assert shown["run"]["counts"]["duplicate"] == 1


def test_same_job_on_two_sites_stays_two_postings_marked_as_possible_duplicates(
        searchable, cli, write_json):
    run = start(cli)
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    items = by_external(report)
    alpha_id, beta_id = items["A-100"]["posting_id"], items["B-7"]["posting_id"]
    assert alpha_id != beta_id
    assert items["B-7"]["outcome"] == "new"
    _, listed, _ = cli("postings", "list", "--outcome", "new")
    marks = {p["id"]: p["possible_duplicates"] for p in listed["postings"]}
    assert [d["provider"] for d in marks[alpha_id]] == ["beta"]
    assert [d["provider"] for d in marks[beta_id]] == ["alpha"]
    assert marks[beta_id][0]["where"] == "this_search"


def test_possible_duplicate_needs_close_publication_dates(searchable, write_json, cli):
    run = start(cli)
    far = [p for p in captures() if p["external_id"] in ("A-100", "B-7")]
    far[1] = {**far[1], "posted_at": None, "posted_ago": "6 days ago"}
    far[0] = {**far[0], "posted_ago": "today"}
    cli("postings", "import", str(run["run_id"]), write_json(far))
    with db.session(searchable) as conn:
        first = conn.execute("SELECT id FROM postings WHERE external_id = 'A-100'").fetchone()[0]
        assert len(search.possible_duplicates(conn, first, run["run_id"])) == 1
        search_date = (datetime.now().date() - timedelta(days=30)).isoformat()
        conn.execute("UPDATE postings SET posted_at = ? WHERE external_id = 'B-7'",
                     (search_date,))
        assert search.possible_duplicates(conn, first, run["run_id"]) == []


def test_tracked_posting_from_another_site_is_a_possible_duplicate(searchable, cli,
                                                                   write_json):
    run = start(cli)
    first = [p for p in captures() if p["external_id"] == "A-100"]
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(first))
    cli("run", "finish", str(run["run_id"]))
    with db.session(searchable) as conn:
        tracking.track(conn, [report["postings"][0]["posting_id"]])
    run2 = start(cli)
    second = [p for p in captures() if p["external_id"] == "B-7"]
    _, report2, _ = cli("postings", "import", str(run2["run_id"]), write_json(second))
    _, listed, _ = cli("postings", "list", "--outcome", "new")
    marks = listed["postings"][0]["possible_duplicates"]
    assert report2["new"] == 1
    assert marks[0]["where"] == "tracked" and marks[0]["job_id"] == "J0001"


def test_previously_dismissed_is_seen_not_new(searchable, cli, write_json):
    run = start(cli)
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    cli("run", "finish", str(run["run_id"]))
    dismissed = by_external(report)["A-101"]["posting_id"]
    with db.session(searchable) as conn:
        tracking.dismiss(conn, [dismissed], "location")
    run2 = start(cli)
    _, report2, _ = cli("postings", "import", str(run2["run_id"]), write_json(captures()))
    again = by_external(report2)["A-101"]
    assert again["outcome"] == "seen" and again["reason"] == "dismissed"
    assert report2["new"] == 0


def test_repost_of_a_tracked_posting_adds_a_timeline_event(searchable, cli, write_json):
    run = start(cli)
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()[:1]))
    cli("run", "finish", str(run["run_id"]))
    with db.session(searchable) as conn:
        tracking.track(conn, [report["postings"][0]["posting_id"]])
    run2 = start(cli)
    _, report2, _ = cli("postings", "import", str(run2["run_id"]), write_json(captures()[:1]))
    assert report2["postings"][0]["reason"] == "tracked"
    with db.session(searchable) as conn:
        kinds = [r[0] for r in conn.execute(
            "SELECT kind FROM events WHERE entity_type = 'application' AND entity_id = 'J0001'")]
    assert "reposted" in kinds


# ── filter, flags, capture ────────────────────────────────────────────────

def test_wrong_work_mode_is_filtered_with_its_reason(searchable, cli, write_json):
    run = start(cli)
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    onsite = by_external(report)["A-101"]["posting_id"]
    code, out, _ = cli("postings", "filter", str(run["run_id"]), write_json(
        [{"posting_id": onsite, "reason": "work_mode", "detail": "Onsite only"}], "f.json"))
    assert code == 0, out
    _, filtered, _ = cli("postings", "list", "--outcome", "filtered")
    assert [(p["id"], p["reason"]) for p in filtered["postings"]] == [(onsite, "work_mode")]
    assert out["summary"]["counts"]["filtered"] == 1


def test_filter_needs_a_known_reason(searchable, cli, write_json):
    run = start(cli)
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    posting_id = by_external(report)["A-101"]["posting_id"]
    code, out, _ = cli("postings", "filter", str(run["run_id"]), write_json(
        [{"posting_id": posting_id, "reason": "vibes"}], "f.json"))
    assert code == 1 and out["error"]["code"] == "invalid_filter"


def test_ambiguous_seniority_stays_with_a_flag(searchable, cli, write_json):
    run = start(cli)
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    junior = by_external(report)["B-8"]["posting_id"]
    code, out, _ = cli("postings", "flag", str(junior), "--text",
                       "Seniority appears lower than yours")
    assert code == 0
    assert out["posting"]["flags"] == ["Seniority appears lower than yours"]
    _, listed, _ = cli("postings", "list", "--outcome", "new")
    assert junior in {p["id"] for p in listed["postings"]}


def test_description_is_verbatim_and_relative_dates_become_calendar_dates(
        searchable, cli, write_json):
    run = start(cli)
    records = captures()
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(records))
    posting_id = by_external(report)["A-100"]["posting_id"]
    _, shown, _ = cli("postings", "show", str(posting_id))
    posting = shown["posting"]
    assert posting["description"] == records[0]["description"]
    assert posting["posted_at"] == (datetime.now().date() - timedelta(days=2)).isoformat()
    assert posting["work_mode"] == "remote" and posting["contract_type"] == "full-time"
    assert posting["url"] == "https://example.test/alpha/jobs/100"


def test_visible_form_questions_are_stored_with_the_posting(searchable, cli, write_json):
    run = start(cli)
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    _, shown, _ = cli("postings", "show", str(by_external(report)["A-100"]["posting_id"]))
    questions = shown["posting"]["form_questions"]
    assert len(questions) == 4
    assert questions[2]["options"] == ["Inmediata", "15 días", "30 días"]
    assert shown["posting"]["form_question_count"] == 4


@pytest.mark.parametrize("bad", [
    {"url": "javascript:alert(1)"},
    {"description": "  "},
    {"work_mode": "sometimes"},
    {"posted_ago": "whenever", "posted_at": None},
])
def test_invalid_records_store_nothing(searchable, cli, write_json, bad):
    run = start(cli)
    records = captures()
    records[1] = {**records[1], **bad}
    code, out, _ = cli("postings", "import", str(run["run_id"]), write_json(records))
    assert code == 1, out
    with db.session(searchable) as conn:
        assert conn.execute("SELECT COUNT(*) FROM postings").fetchone()[0] == 0


def test_import_into_a_finished_run_is_refused(searchable, cli, write_json):
    run = start(cli)
    cli("run", "finish", str(run["run_id"]))
    code, out, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    assert code == 1 and out["error"]["code"] == "run_finished"


def test_a_search_needs_a_profile(workspace, cli, providers_dir):
    code, out, _ = cli("run", "start")
    assert code == 1 and out["error"]["code"] == "no_profile"


def test_one_change_bump_per_command(searchable, cli, write_json):
    run = start(cli)
    with db.session(searchable) as conn:
        before = db.change_state(conn)["counter"]
    cli("postings", "import", str(run["run_id"]), write_json(captures()))
    with db.session(searchable) as conn:
        assert db.change_state(conn)["counter"] == before + 1


@pytest.mark.parametrize("shown,days", [
    ("2 days ago", 2), ("hace 3 días", 3), ("yesterday", 1), ("ayer", 1), ("today", 0),
    ("hace 2 horas", 0), ("1 week ago", 7), ("hace 2 semanas", 14), ("30+ days ago", 30),
    ("3d", 3), ("Publicado hace 5 días", 5),
])
def test_relative_dates(shown, days):
    from jobtracker.core.normalize import relative_date

    reference = date(2026, 11, 15)
    assert relative_date(shown, reference) == reference - timedelta(days=days)


# ── work-mode detail ──────────────────────────────────────────────────────

def test_import_stores_the_work_mode_detail_as_the_agents(searchable, cli, write_json):
    records = captures()
    records[0]["work_mode"] = "hybrid"
    records[0]["work_mode_detail"] = "  Híbrido: 2 días presencial por semana "
    run = start(cli)
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(records))
    posting_id = by_external(report)[records[0]["external_id"]]["posting_id"]
    _, shown, _ = cli("postings", "show", str(posting_id))
    posting = shown["posting"]
    assert (posting["work_mode"], posting["work_mode_detail"], posting["work_mode_source"]) == (
        "hybrid", "Híbrido: 2 días presencial por semana", "agent")


def test_a_too_long_work_mode_detail_is_refused(searchable, cli, write_json):
    records = captures()
    records[0]["work_mode_detail"] = "x" * (search.WORK_MODE_DETAIL_MAX + 1)
    run = start(cli)
    code, out, _ = cli("postings", "import", str(run["run_id"]), write_json(records))
    assert code == 1
    assert out["error"]["details"]["field"] == "work_mode_detail"


def test_users_work_mode_is_recorded_and_survives_a_later_search(searchable, cli, write_json):
    run = start(cli)
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    posting_id = by_external(report)["A-101"]["posting_id"]
    cli("run", "finish", str(run["run_id"]))
    with db.session(searchable) as conn:
        before = search.posting(conn, posting_id, detail=False)
        changed = search.set_work_mode(conn, posting_id, "hybrid", "Fridays from home")
        event = conn.execute("SELECT data FROM events WHERE entity_type = 'posting'"
                             " AND entity_id = ? AND kind = 'work_mode'",
                             (str(posting_id),)).fetchone()
    assert (changed["work_mode"], changed["work_mode_detail"], changed["work_mode_source"]) == (
        "hybrid", "Fridays from home", "user")
    assert json.loads(event["data"])["from"]["mode"] == before["work_mode"]

    again = start(cli)
    _, report, _ = cli("postings", "import", str(again["run_id"]), write_json(captures()))
    assert by_external(report)["A-101"]["outcome"] == "seen"
    with db.session(searchable) as conn:
        kept = search.posting(conn, posting_id, detail=False)
    assert (kept["work_mode"], kept["work_mode_detail"], kept["work_mode_source"]) == (
        "hybrid", "Fridays from home", "user")


def test_work_mode_can_be_cleared_and_bad_modes_are_refused(searchable, cli, write_json):
    run = start(cli)
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    posting_id = by_external(report)["A-101"]["posting_id"]
    with db.session(searchable) as conn:
        cleared = search.set_work_mode(conn, posting_id, "none", "")
        assert (cleared["work_mode"], cleared["work_mode_detail"]) == (None, None)
        with pytest.raises(search.JobTrackerError):
            search.set_work_mode(conn, posting_id, "on the moon", None)
        with pytest.raises(search.JobTrackerError):
            search.set_work_mode(conn, 99999, "remote", None)


def test_migration_keeps_existing_postings(searchable, cli, write_json):
    run = start(cli)
    cli("postings", "import", str(run["run_id"]), write_json(captures()))
    from tests.migrations import rewind

    rewind(searchable.database, 9)
    with db.session(searchable) as conn:
        rows = conn.execute("SELECT work_mode, work_mode_detail, work_mode_source"
                            " FROM postings").fetchall()
    assert rows and all(r["work_mode_detail"] is None and r["work_mode_source"] == "agent"
                        for r in rows)
    assert any(r["work_mode"] for r in rows)


def test_work_mode_command(searchable, cli, write_json):
    run = start(cli)
    _, report, _ = cli("postings", "import", str(run["run_id"]), write_json(captures()))
    posting_id = by_external(report)["A-101"]["posting_id"]
    code, out, _ = cli("postings", "work-mode", str(posting_id), "--mode", "remote",
                       "--detail", "Early Friday")
    assert code == 0, out
    assert (out["posting"]["work_mode"], out["posting"]["work_mode_detail"],
            out["posting"]["work_mode_source"]) == ("remote", "Early Friday", "user")
    code, out, _ = cli("postings", "work-mode", str(posting_id), "--mode", "none")
    assert code == 0 and out["posting"]["work_mode"] is None
    assert out["posting"]["work_mode_detail"] is None
    code, out, _ = cli("postings", "work-mode", "99999", "--mode", "remote")
    assert code == 1 and out["error"]["code"] == "not_found"
    code, _, _ = cli("postings", "work-mode", str(posting_id), "--mode", "moon")
    assert code != 0
