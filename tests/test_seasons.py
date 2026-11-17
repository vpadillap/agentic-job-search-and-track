"""seasons: one active season, new seasons, earlier seasons, learning carry-over,
open applications, full reset, export (fictional persona only)."""
# ruff: noqa: F811  (pytest fixtures imported from other test modules)
from __future__ import annotations

import csv
import json
from pathlib import Path

from jobtracker.core import applications, board, db, insights, learning, rules
from tests.helpers import RESUME_TEXT, make_docx
from tests.test_applications import jobs  # noqa: F401  (fixture)
from tests.test_search import captures


def _apply_lesson(home, effect=None) -> int:
    with db.session(home) as conn:
        record = {"origin": "learned", "area": "search", "text": "Prefer remote postings",
                  "evidence": "6 of 8 cases"}
        if effect:
            record["effect"] = effect
        rule = rules.add_rules(conn, [record])[0]
        learning.apply(conn, rule["id"])
        return rule["id"]


# ── one active season ─────────────────────────────────────────────────────

def test_default_views_show_only_the_active_season(jobs, cli):
    code, out, _ = cli("season", "new", "--learning", "keep", "--leave-open")
    assert code == 0, out
    assert out["season"]["number"] == 2 and out["previous"]["active"] is False

    _, listed, _ = cli("applications", "list")
    assert listed["applications"] == []
    _, earlier, _ = cli("applications", "list", "--season", "1")
    assert {a["job_id"] for a in earlier["applications"]} == {jobs["altamar"], jobs["finlima"]}
    assert all(a["earlier_season"] for a in earlier["applications"])

    with db.session(jobs["home"]) as conn:
        assert board.counts(conn)["applications"] == 0
        assert board.search_board(conn)["run"] is None          # no search in season 2 yet
        assert board.search_board(conn, season=1)["run"] is not None
        assert board.pending(conn) == []

    _, seasons_out, _ = cli("season", "list")
    assert [(s["number"], s["active"]) for s in seasons_out["seasons"]] == [(1, False), (2, True)]


def test_new_applications_belong_to_the_active_season(jobs, cli, tmp_path):
    cli("season", "new", "--learning", "keep", "--leave-open")
    path = tmp_path / "again.json"
    records = captures()
    for record in records:
        record["external_id"] = "S2-" + record["external_id"]
        record["url"] = record["url"] + "-season-2"
    path.write_text(json.dumps(records), encoding="utf-8")
    _, run, _ = cli("run", "start")
    _, imported, _ = cli("postings", "import", str(run["run_id"]), str(path))
    cli("run", "finish", str(run["run_id"]))
    posting_id = next(p["posting_id"] for p in imported["postings"] if p.get("posting_id"))
    with db.session(jobs["home"]) as conn:
        from jobtracker.core import tracking

        job = tracking.track(conn, [posting_id])[0]["job_id"]
        listed = applications.list_applications(conn)
        assert [a["job_id"] for a in listed] == [job]
        assert listed[0]["season"] == 2


# ── starting a new season ─────────────────────────────────────────────────

def test_new_season_with_an_updated_resume(searchable, cli, tmp_path):
    first = make_docx(tmp_path / "first.docx")
    _, imported, _ = cli("resume", "import", str(first), "--language", "en")
    old_id = imported["resume"]["id"]
    cli("season", "new", "--learning", "keep")
    _, season2, _ = cli("season", "show")
    assert season2["season"]["profile"]["version"] == 1           # previous answers as defaults
    assert season2["season"]["profile"]["titles"]

    second = make_docx(tmp_path / "second.docx", RESUME_TEXT + "\nCertifications\nFictional")
    _, newer, _ = cli("resume", "import", str(second), "--language", "en")
    _, season2, _ = cli("season", "show")
    _, season1, _ = cli("season", "show", "1")
    assert [r["id"] for r in season2["season"]["base_resumes"]] == [newer["resume"]["id"]]
    assert [r["id"] for r in season1["season"]["base_resumes"]] == [old_id]
    assert Path(season1["season"]["base_resumes"][0]["path"]).is_file()
    assert season1["season"]["profile"]["titles"] == season2["season"]["profile"]["titles"]


def test_profile_changes_in_the_new_season_leave_the_earlier_one(searchable, cli, tmp_path):
    cli("season", "new", "--learning", "keep")
    cli("profile", "title", "Fictional Platform Lead", "--state", "included")
    _, season1, _ = cli("season", "show", "1")
    titles = [t["title"] for t in season1["season"]["profile"]["titles"]]
    assert "Fictional Platform Lead" not in titles


# ── earlier seasons remain available ──────────────────────────────────────

def test_late_reply_on_an_earlier_season(jobs, cli):
    cli("applications", "set-status", jobs["altamar"], "--to", "applied")
    cli("season", "new", "--learning", "keep", "--leave-open")
    code, out, _ = cli("applications", "set-status", jobs["altamar"], "--to", "interview")
    assert code == 0, out
    assert out["applications"][0]["status"]["key"] == "interview"
    assert out["applications"][0]["season"] == 1


def test_earlier_season_is_read_only_except_status(jobs, cli, tmp_path):
    cli("season", "new", "--learning", "keep", "--leave-open")
    path = tmp_path / "details.json"
    path.write_text(json.dumps({"notes": "fictional note"}), encoding="utf-8")
    code, out, _ = cli("applications", "update", jobs["altamar"], str(path))
    assert code == 1 and out["error"]["code"] == "earlier_season"
    code, out, _ = cli("applications", "tag", jobs["altamar"], "--add", "late")
    assert code == 1 and out["error"]["code"] == "earlier_season"
    _, shown, _ = cli("applications", "show", jobs["altamar"])
    assert shown["application"]["notes"] is None


def test_late_offer_on_an_earlier_season(jobs, cli, tmp_path):
    cli("applications", "set-status", jobs["altamar"], "--to", "applied")
    cli("season", "new", "--learning", "keep", "--leave-open")
    path = tmp_path / "offer.json"
    path.write_text(json.dumps({"offered_salary": {"amount": 14000, "currency": "PEN"}}),
                    encoding="utf-8")
    code, out, _ = cli("applications", "update", jobs["altamar"], str(path))
    assert code == 0, out
    assert out["application"]["offered_salary"]["amount"] == 14000
    path.write_text(json.dumps({"offered_salary": None, "notes": "x"}), encoding="utf-8")
    code, out, _ = cli("applications", "update", jobs["altamar"], str(path))
    assert code == 1 and out["error"]["code"] == "earlier_season"


# ── choice of what carries over ───────────────────────────────────────────

def test_keeping_learning_marks_lessons_from_an_earlier_season(searchable, cli):
    rule_id = _apply_lesson(searchable)
    cli("rules", "add", "--text", "No outsourcing firms", "--area", "search")
    code, out, _ = cli("season", "new", "--learning", "keep")
    assert code == 0, out
    _, listed, _ = cli("rules", "list")
    by_id = {r["id"]: r for r in listed["rules"]}
    assert by_id[rule_id]["status"] == "active" and by_id[rule_id]["earlier_season"] is True
    user_rule = next(r for r in listed["rules"] if r["origin"] == "user")
    assert user_rule["earlier_season"] is False


def test_resetting_learning_keeps_preferences(searchable, cli):
    rule_id = _apply_lesson(searchable, {"min_score_shown": 70})
    cli("rules", "add", "--text", "No outsourcing firms", "--area", "search")
    code, out, _ = cli("season", "new", "--learning", "reset")
    assert code == 0, out
    assert out["retired_lessons"] == [rule_id]
    _, listed, _ = cli("rules", "list")
    assert all(r["origin"] != "learned" for r in listed["rules"])
    assert any(r["origin"] == "user" and r["text"] == "No outsourcing firms"
               for r in listed["rules"])
    with db.session(searchable) as conn:
        assert learning.reset_at(conn) is not None
        assert learning.effects(conn).get("min_score_shown") is None
        assert board.default_min_score(conn) is None


def test_learning_choice_is_required(searchable, cli):
    code, out, _ = cli("season", "new")
    assert code == 2
    _, seasons_out, _ = cli("season", "list")
    assert len(seasons_out["seasons"]) == 1


# ── open applications ─────────────────────────────────────────────────────

def test_open_applications_need_a_decision(jobs, cli):
    code, out, _ = cli("season", "new", "--learning", "keep")
    assert code == 1 and out["error"]["code"] == "open_applications"
    open_ids = {i["job_id"] for i in out["error"]["details"]["open"]}
    assert open_ids == {jobs["altamar"], jobs["finlima"]}
    _, seasons_out, _ = cli("season", "list")
    assert len(seasons_out["seasons"]) == 1


def test_interview_in_progress_is_carried_with_its_history(jobs, cli):
    cli("applications", "set-status", jobs["altamar"], "--to", "interview")
    _, before, _ = cli("applications", "show", jobs["altamar"])
    code, out, _ = cli("season", "new", "--learning", "keep", "--carry", jobs["altamar"],
                       "--leave-open")
    assert code == 0, out
    assert out["carried"] == [jobs["altamar"]] and out["left_in_previous"] == [jobs["finlima"]]
    _, listed, _ = cli("applications", "list")
    assert [a["job_id"] for a in listed["applications"]] == [jobs["altamar"]]
    _, after, _ = cli("applications", "show", jobs["altamar"])
    kinds = [h["kind"] for h in after["application"]["history"]]
    assert [h for h in before["application"]["history"]] == \
        [h for h in after["application"]["history"] if h["kind"] != "carried_over"]
    assert "carried_over" in kinds and after["application"]["status"]["key"] == "interview"
    # A carried application is editable again in the new season.
    code, _, _ = cli("applications", "tag", jobs["altamar"], "--add", "round-2")
    assert code == 0


def test_carried_applications_count_in_the_new_season_insights(jobs, cli):
    cli("applications", "set-status", jobs["altamar"], "--to", "interview")
    cli("season", "new", "--learning", "keep", "--carry-all-open")
    with db.session(jobs["home"]) as conn:
        assert insights.summary(conn, "season")["applied"] == 1
        assert insights.summary(conn, "all")["applied"] == 1


# ── full reset ────────────────────────────────────────────────────────────

def test_confirmed_full_reset_archives_and_requires_setup(searchable, cli):
    (searchable.home / ".private-terms").write_text("Fictional Name\n", encoding="utf-8")
    code, out, _ = cli("reset", "--confirm", "RESET", "--label", "new direction")
    assert code == 0, out
    archived = Path(out["archived_to"])
    assert archived.parent == searchable.archive and archived.name.endswith("-new-direction")
    assert (archived / "jobtracker.db").is_file() and (archived / "config.toml").is_file()
    _, context, _ = cli("context")
    assert context["setup_required"] is True and context["profile"] is None
    # The privacy guard keeps the user's terms.
    assert (searchable.home / ".private-terms").read_text(encoding="utf-8") == "Fictional Name\n"


def test_unconfirmed_full_reset_changes_nothing(searchable, cli):
    for confirmation in ([], ["--confirm", "yes"]):
        code, out, _ = cli("reset", *confirmation)
        assert code == 1 and out["error"]["code"] == "confirmation_required"
    assert list(searchable.archive.iterdir()) == []
    _, context, _ = cli("context")
    assert context["profile"] is not None


# ── export ────────────────────────────────────────────────────────────────

def test_export_writes_json_and_csv_in_the_exports_folder(jobs, cli):
    cli("applications", "tag", jobs["altamar"], "--add", "dream job")
    code, out, _ = cli("export")
    assert code == 0, out
    folder = Path(out["folder"])
    assert folder.parent == jobs["home"].exports
    names = sorted(p.name for p in folder.iterdir())
    assert names == ["applications.csv", "applications.json", "events.csv", "events.json",
                     "rules.csv", "rules.json"]
    exported = json.loads((folder / "applications.json").read_text(encoding="utf-8"))
    assert {a["job_id"] for a in exported} == {jobs["altamar"], jobs["finlima"]}
    with (folder / "applications.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2 and "dream job" in "".join(r["tags"] for r in rows)
    _, again, _ = cli("export")
    assert again["folder"] != out["folder"]
