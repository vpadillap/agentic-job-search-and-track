"""The learning loop: insights, history, lessons, refresh, prediction, fit, recommendations."""
from __future__ import annotations

import io
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jobtracker.core import (
    applications,
    db,
    demo,
    insights,
    learning,
    predict,
    recommend,
    scoring,
    search,
)
from jobtracker.core.paths import HOME_ENV, Paths
from jobtracker.web.app import create_app

TODAY = datetime.now().date()
NO_SKILLS = {"matched": [], "missing": []}


# ── fixtures: one fictional history per level, copied for each test ───────

@pytest.fixture(scope="session")
def templates(tmp_path_factory):
    import os

    made: dict[str, Path] = {}

    def make(level: str) -> Path:
        if level not in made:
            root = tmp_path_factory.mktemp(f"template-{level}") / "home"
            previous = os.environ.get(HOME_ENV)
            os.environ[HOME_ENV] = str(root)
            try:
                demo.seed(Paths(root.resolve()), learning=level)
            finally:
                if previous is None:
                    os.environ.pop(HOME_ENV, None)
                else:
                    os.environ[HOME_ENV] = previous
            made[level] = root
        return made[level]

    return make


@pytest.fixture
def history(home, templates):
    def load(level: str) -> Paths:
        shutil.copytree(templates(level), home.home)
        return home

    return load


@pytest.fixture
def send(cli, monkeypatch):
    def run(payload: object, *args: str):
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        return cli(*args)

    return run


def lesson(key: str, cases: int = 7, **extra) -> dict:
    return {"text": "Fictional lesson.", "evidence": f"{cases} cases (demo).",
            "candidate_key": key, "cases": cases, "area": "score", **extra}


# ── outcome insights ──────────────────────────────────────────────────────

def test_headline_indicators_with_counts(history, cli):
    history("descriptive")
    _, out, _ = cli("insights", "summary", "--period", "all")
    s = out["summary"]
    assert s["resolved"] == s["interview"]["of"] == s["response"]["of"]
    assert s["interview"]["pct"] == round(s["interview"]["count"] * 100 / s["resolved"])
    assert s["decisions"]["dismissed"] > 0 and s["corrections"] > 0


def test_recent_application_is_unresolved(workspace, cli):
    demo.seed(workspace)
    _, before, _ = cli("insights", "summary", "--period", "all")
    with db.session(workspace) as conn:
        job = conn.execute("SELECT job_id FROM applications a JOIN statuses s ON s.id ="
                           " a.status_id WHERE s.stage = 'to_apply' LIMIT 1").fetchone()[0]
        applications.set_status(conn, [job], "applied")
    _, after, _ = cli("insights", "summary", "--period", "all")
    assert after["summary"]["unresolved"] == before["summary"]["unresolved"] + 1
    assert after["summary"]["resolved"] == before["summary"]["resolved"]


def test_score_ranges_use_the_score_at_application(history, cli):
    paths = history("descriptive")
    _, out, _ = cli("insights", "breakdown", "score_band", "--period", "all")
    groups = {g["group"]: g for g in out["breakdown"]["groups"]}
    assert sum(g["cases"] for g in groups.values()) == out["breakdown"]["resolved"]
    with db.session(paths) as conn:  # a later score change does not move the application
        item = next(i for i in insights.outcomes(conn) if i["resolved"])
        scoring.set_score(conn, item["posting_id"], {"components": {
            "title": {"points": 0, "note": "x"}, "skills": {"points": 0, "note": "x", **NO_SKILLS},
            "seniority": {"points": 0, "note": "x"}, "conditions": {"points": 0, "note": "x"}}})
    _, again, _ = cli("insights", "breakdown", "score_band", "--period", "all")
    assert again["breakdown"]["groups"] == out["breakdown"]["groups"]


def test_corrected_work_mode_and_not_stated(history, cli):
    paths = history("descriptive")
    with db.session(paths) as conn:
        item = next(i for i in insights.outcomes(conn) if i["resolved"])
        search.set_work_mode(conn, item["posting_id"], "remote", None)
        corrected = next(i for i in insights.outcomes(conn) if i["job_id"] == item["job_id"])
        assert insights.features_of(corrected, [])["work_mode"] == "remote"
        conn.execute("UPDATE postings SET work_mode = NULL WHERE id = ?", (item["posting_id"],))
        stated = next(i for i in insights.outcomes(conn) if i["job_id"] == item["job_id"])
        assert insights.features_of(stated, [])["work_mode"] == "not_stated"
    _, out, _ = cli("insights", "breakdown", "work_mode", "--period", "all")
    assert "not_stated" in {g["group"] for g in out["breakdown"]["groups"]}


def test_language_is_a_breakdown(history, cli):
    history("descriptive")
    _, out, _ = cli("insights", "breakdown", "language", "--period", "all")
    assert {g["group"] for g in out["breakdown"]["groups"]} <= {"es", "en"}


def test_small_groups_are_marked(history, cli):
    history("descriptive")
    _, out, _ = cli("insights", "breakdown", "channel", "--period", "all")
    for group in out["breakdown"]["groups"]:
        assert group["insufficient"] == (group["cases"] < 5)
        assert group["low"] <= group["rate"] <= group["high"]


def test_period_selection(history, cli):
    history("descriptive")
    _, all_time, _ = cli("insights", "summary", "--period", "all")
    _, recent, _ = cli("insights", "summary", "--period", "30")
    assert recent["summary"]["applied"] < all_time["summary"]["applied"]


def test_agent_and_panel_see_the_same_numbers(history, cli):
    history("descriptive")
    _, out, _ = cli("insights", "summary", "--period", "season")
    body = TestClient(create_app(), base_url="http://127.0.0.1:8000").get(
        "/api/learning?period=season").json()
    assert body["summary"]["interview"] == out["summary"]["interview"]


# ── full history for the agent ────────────────────────────────────────────

def read_history(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def test_history_contains_every_record_in_the_private_home(history, cli):
    paths = history("descriptive")
    _, out, _ = cli("learning", "refresh")
    file = Path(out["history"]["path"])
    assert file.is_relative_to(paths.home) and file.parent.name == "learning"
    records = read_history(out["history"]["path"])
    with db.session(paths) as conn:
        applied = len(insights.outcomes(conn))
        decided = len(insights.decisions(conn))
        corrected = len(insights.corrections(conn))
    kinds = [r["type"] for r in records]
    assert kinds.count("application") == applied
    assert kinds.count("dismissal") + kinds.count("tracked_not_applied") == decided - applied
    assert kinds.count("correction") == corrected
    application = next(r for r in records if r["type"] == "application")
    assert application["status"] and isinstance(application["status_path"], list)


def test_first_outcomes_are_all_there(workspace, cli):
    demo.seed(workspace)
    _, out, _ = cli("learning", "refresh")
    applied = [r for r in read_history(out["history"]["path"]) if r["type"] == "application"]
    with db.session(workspace) as conn:
        assert len(applied) == len(insights.outcomes(conn)) > 0


def test_history_ordered_for_a_posting_is_never_cut(history, cli):
    paths = history("descriptive")
    _, plain, _ = cli("learning", "refresh")
    with db.session(paths) as conn:
        target = insights.outcomes(conn)[0]["posting_id"]
    _, ordered, _ = cli("learning", "refresh", "--posting", str(target))
    records = read_history(ordered["history"]["path"])
    assert ordered["history"]["records"] == plain["history"]["records"] == len(records)
    applications_ = [r for r in records if r["type"] == "application"]
    assert applications_[0]["similarity"] == max(r["similarity"] for r in applications_)


def test_pending_outcomes_are_listed_but_not_counted(history, cli):
    paths = history("descriptive")
    with db.session(paths) as conn:
        job = conn.execute("SELECT job_id FROM applications a JOIN statuses s ON s.id ="
                           " a.status_id WHERE s.stage = 'to_apply' LIMIT 1").fetchone()[0]
        applications.set_status(conn, [job], "applied")
    _, out, _ = cli("learning", "refresh")
    record = next(r for r in read_history(out["history"]["path"]) if r.get("job_id") == job)
    assert record["outcome"] == "pending"


# ── rules and lessons ─────────────────────────────────────────────────────

def test_refresh_does_not_refit_without_new_outcomes(history, cli):
    paths = history("predictive")
    with db.session(paths) as conn:
        before = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    _, out, _ = cli("learning", "refresh")
    assert out["refitted"] == {}
    with db.session(paths) as conn:
        assert conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0] == before
    _, context, _ = cli("context")
    assert context["learning"]["last_refresh"] == out["refreshed_at"]


def test_refresh_refits_after_enough_new_outcomes(history, cli):
    paths = history("predictive")
    with db.session(paths) as conn:
        last = learning.analyses(conn, 1)[0]["resolved"]
        conn.execute("UPDATE analyses SET resolved = ? WHERE kind = 'interview'", (last - 12,))
    _, out, _ = cli("learning", "refresh")
    assert "interview" in out["refitted"]


def titles_of(cli) -> dict:
    _, profile, _ = cli("profile", "show")
    return {t["title"]: t["state"] for t in profile["profile"]["titles"]}


def test_title_lesson_changes_only_the_profile_and_reverts(searchable, cli, send):
    paths = searchable
    with db.session(paths) as conn:
        before = search.start_run(conn, paths, 7)
    _, out, _ = send([lesson("title:Data Platform Engineer:worse", area="general",
                             effect={"title_state": {"title": "Data Platform Engineer",
                                                     "state": "under_review"}})],
                     "rules", "propose", "-")
    rule_id = str(out["proposed"][0]["id"])
    assert titles_of(cli)["Data Platform Engineer"] == "included"  # proposed: no change yet
    cli("rules", "apply", rule_id)
    assert titles_of(cli)["Data Platform Engineer"] == "under_review"
    with db.session(paths) as conn:
        after = search.start_run(conn, paths, 7)
    # Searching itself is untouched: the run just reads the (user-approved) profile.
    assert after["titles"] == [t for t in before["titles"] if t != "Data Platform Engineer"]
    assert [p["id"] for p in after["providers"]] == [p["id"] for p in before["providers"]]
    cli("rules", "revert", rule_id)
    assert titles_of(cli)["Data Platform Engineer"] == "included"


def test_search_effects_do_not_exist(workspace, send):
    for removed in ("title_priority", "provider_priority"):
        code, bad, _ = send([lesson(f"x:{removed}", effect={removed: {}})],
                            "rules", "propose", "-")
        assert code == 1 and bad["error"]["code"] == "invalid_rule"


def test_lessons_need_five_cases(workspace, send):
    code, out, _ = send([lesson("x", cases=3)], "rules", "propose", "-")
    assert code == 1 and out["error"]["code"] == "too_few_cases"


def test_title_candidate_is_a_profile_suggestion(history, cli):
    history("descriptive")
    _, out, _ = cli("insights", "lessons", "--period", "all")
    titles = [c for c in out["candidates"] if c["dimension"] == "title"]
    for item in titles:
        assert item["effect"] is None or set(item["effect"]) == {"title_state"}


def test_repeated_dismissals_and_corrections_propose_lessons(history, cli):
    history("collecting")
    _, out, _ = cli("insights", "lessons", "--period", "all")
    kinds = {c["dimension"] for c in out["candidates"]}
    assert "dismissals" in kinds          # available before any outcome conclusion
    dismissals = next(c for c in out["candidates"] if c["dimension"] == "dismissals")
    assert dismissals["evidence"]["dismissals"] >= 5 and dismissals["evidence"]["postings"]
    corrections = [c for c in out["candidates"] if c["dimension"] == "corrections"]
    assert corrections and corrections[0]["group"] == "linkedin"


def test_the_user_decides(workspace, cli, send):
    _, out, _ = send([lesson("a"), lesson("b")], "rules", "propose", "-")
    first, second = (str(r["id"]) for r in out["proposed"])
    assert all(r["status"] == "proposed" for r in out["proposed"])
    _, applied, _ = cli("rules", "apply", first)
    assert applied["rule"]["status"] == "active"
    _, ignored, _ = cli("rules", "ignore", second)
    assert ignored["rule"]["status"] == "ignored"
    _, again, _ = send([lesson("b")], "rules", "propose", "-")          # same evidence
    assert again["proposed"] == [] and again["skipped"][0]["candidate_key"] == "b"
    _, more, _ = send([lesson("b", cases=12)], "rules", "propose", "-")  # 5+ new cases
    assert len(more["proposed"]) == 1
    _, reverted, _ = cli("rules", "revert", first)
    assert reverted["rule"]["status"] == "reverted"


def test_system_rules_cannot_be_overridden(workspace, cli, send):
    code, out, _ = send([lesson("x", effect={"allow_salary_without_evidence": True})],
                        "rules", "propose", "-")
    assert code == 1 and "not an effect" in out["error"]["message"]
    _, rules, _ = cli("rules", "list")
    system = next(r for r in rules["rules"] if r["origin"] == "system")
    code, out, _ = cli("rules", "apply", str(system["id"]))
    assert code == 1 and out["error"]["code"] == "not_a_lesson"


def test_influence_lets_a_lesson_be_checked(history, cli, send):
    paths = history("descriptive")
    _, out, _ = send([lesson("weights-x", area="score")], "rules", "propose", "-")
    rule_id = out["proposed"][0]["id"]
    cli("rules", "apply", str(rule_id))
    with db.session(paths) as conn:
        item = next(i for i in insights.outcomes(conn) if i["resolved"])
        learning.record_influence(conn, "score", item["posting_id"], areas=("score",))
    _, effect, _ = cli("rules", "effect", str(rule_id))
    assert effect["effect"]["with"]["cases"] == 1
    assert effect["effect"]["without"]["cases"] > 0


def test_applying_new_weights_marks_open_postings_for_rescoring(history, cli, send):
    paths = history("descriptive")
    _, out, _ = send([lesson("weights:demo", effect={"weights": {
        "title": 20, "skills": 40, "seniority": 10, "conditions": 20}})],
        "rules", "propose", "-")
    cli("rules", "apply", str(out["proposed"][0]["id"]))
    _, weights, _ = cli("score", "weights")
    assert weights["weights"]["weights"]["skills"] == 40
    _, pending, _ = cli("pending")
    reasons = {i["reason"] for i in pending["pending"] if i["kind"] == "rescore"}
    assert "the score weights changed (a lesson you applied)" in reasons
    with db.session(paths) as conn:
        old = conn.execute("SELECT COUNT(*) FROM scores WHERE weights_version = 1").fetchone()[0]
    assert old > 0                                              # earlier scores keep theirs


def test_weights_candidate_from_a_validated_model(workspace):
    with db.session(workspace) as conn:
        model = {"bias": -1.0, "coef": {"skills=high": 2.5, "skills=low": -1.5,
                                        "seniority=high": 0.0, "seniority=low": 0.0},
                 "base_rate": 0.3, "bootstrap": [], "fitted_on": 50}
        conn.execute("INSERT INTO analyses (kind, created_at, resolved, interviews, passed,"
                     " model) VALUES ('interview', ?, 50, 15, 1, ?)",
                     (datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"), json.dumps(model)))
        candidate = predict.weights_candidate(conn)
    others = [candidate["weights"][n] for n in ("title", "seniority", "conditions")]
    assert candidate["weights"]["skills"] == 45 and max(others) < 45
    judged = [candidate["weights"][n] for n in ("title", "skills", "seniority", "conditions")]
    assert sum(judged) == 90 and all(5 <= w <= 45 for w in judged)


# ── levels, prediction, fit ───────────────────────────────────────────────

def test_levels_go_up_with_evidence(history, cli):
    paths = history("predictive")
    _, out, _ = cli("learning", "level")
    assert out["level"]["name"] == "predictive"
    with db.session(paths) as conn:  # a failed validation brings it back down
        conn.execute("UPDATE analyses SET passed = 0, reason = 'test' WHERE kind = 'interview'")
    _, out, _ = cli("learning", "level")
    assert out["level"]["name"] == "descriptive" and out["level"]["model_reason"] == "test"


def test_checking_again_never_demotes_the_prescriptive_level(history, cli):
    paths = history("prescriptive")
    cli("predict", "fit")                                  # a deeper review re-checks today
    _, out, _ = cli("learning", "level")
    assert out["level"]["name"] == "prescriptive"
    with db.session(paths) as conn:                        # a failed check starts over
        conn.execute("UPDATE analyses SET passed = 0, reason = 'test' WHERE id = (SELECT"
                     " MAX(id) FROM analyses WHERE kind = 'interview')")
        assert learning.level(conn)["name"] == "descriptive"


@pytest.mark.parametrize("level", ["collecting", "descriptive"])
def test_no_estimates_without_enough_validated_data(history, level):
    paths = history(level)
    with db.session(paths) as conn:
        posting = conn.execute("SELECT id FROM postings LIMIT 1").fetchone()[0]
        assert predict.estimate(conn, posting) is None
        current = learning.level(conn)
    assert current["needs"]


def test_estimates_are_honest(history, cli):
    paths = history("predictive")
    with db.session(paths) as conn:
        posting = conn.execute("SELECT id FROM postings WHERE id NOT IN (SELECT posting_id"
                               " FROM applications) LIMIT 1").fetchone()[0]
    _, out, _ = cli("predict", "show", str(posting))
    estimate = out["interview_estimate"]
    assert estimate["low"] <= estimate["probability"] <= estimate["high"]
    assert estimate["label"] in ("low", "medium", "high") and len(estimate["factors"]) <= 2
    assert out["track_record"]["calibration"]


def test_no_signal_means_no_estimates(workspace):
    import random

    rng = random.Random(1)
    with db.session(workspace) as conn:
        from jobtracker.core import demo_learning

        demo_learning.add_history(conn, workspace, "descriptive")
        # Replace every outcome with a coin flip: nothing to learn.
        for item in insights.outcomes(conn):
            conn.execute("UPDATE events SET data = json_set(data, '$.to_stage', ?)"
                         " WHERE entity_type = 'application' AND entity_id = ?"
                         " AND kind = 'status_changed'",
                         ("interview" if rng.random() < 0.3 else "closed_negative",
                          item["job_id"]))
        result = predict.fit(conn)
    assert result["validation"]["passed"] is False
    assert result["level"]["level"] <= 1


def test_history_component_follows_the_estimate(history):
    paths = history("predictive")
    submission = {"components": {
        "title": {"points": 25, "note": "x"}, "skills": {"points": 30, "note": "x", **NO_SKILLS},
        "seniority": {"points": 15, "note": "x"}, "conditions": {"points": 13, "note": "x"}}}
    with db.session(paths) as conn:
        posting = conn.execute("SELECT id FROM postings LIMIT 1").fetchone()[0]
        score = scoring.set_score(conn, posting, submission)
    history_part = next(c for c in score["components"] if c["component"] == "history")
    assert history_part.get("neutral") is False and "%" in history_part["note"]


def test_history_component_is_neutral_before_predictions(history):
    paths = history("descriptive")
    with db.session(paths) as conn:
        posting = conn.execute("SELECT id FROM postings LIMIT 1").fetchone()[0]
        score = scoring.set_score(conn, posting, {"components": {
            "title": {"points": 25, "note": "x"},
            "skills": {"points": 30, "note": "x", **NO_SKILLS},
            "seniority": {"points": 15, "note": "x"}, "conditions": {"points": 13, "note": "x"}}})
    history_part = next(c for c in score["components"] if c["component"] == "history")
    assert history_part["neutral"] is True and history_part["points"] == 5


def test_reset_withdraws_estimates(history, cli):
    paths = history("predictive")
    code, out, _ = cli("learning", "reset")
    assert code == 1 and out["error"]["code"] == "confirmation_required"
    code, out, _ = cli("learning", "reset", "--confirm", "RESET")
    assert code == 0
    with db.session(paths) as conn:
        posting = conn.execute("SELECT id FROM postings LIMIT 1").fetchone()[0]
        assert predict.estimate(conn, posting) is None
        assert learning.level(conn)["level"] <= 1


def test_fit_to_your_choices(history, cli):
    paths = history("predictive")
    with db.session(paths) as conn:
        posting = conn.execute("SELECT id FROM postings WHERE id NOT IN (SELECT posting_id"
                               " FROM applications) LIMIT 1").fetchone()[0]
        before = scoring.current(conn, posting)["total"]
    _, out, _ = cli("predict", "show", str(posting))
    assert out["fit"]["label"] in ("low", "medium", "high")
    assert "not a chance of success" in out["fit"]["meaning"]
    with db.session(paths) as conn:
        assert scoring.current(conn, posting)["total"] == before   # never changes the score


def test_too_few_decisions_for_fit(history, cli):
    history("collecting")
    _, out, _ = cli("predict", "fit")
    assert out["fit"]["validation"]["passed"] is False
    assert "needs" in out["fit"]["validation"]["reason"]


# ── recommendations ───────────────────────────────────────────────────────

def test_recommendations_need_two_validations(history, cli):
    history("predictive")
    _, out, _ = cli("recommend")
    assert out["recommendations"] is None


def test_recommendations_at_the_prescriptive_level(history, cli):
    paths = history("prescriptive")
    _, out, _ = cli("recommend")
    recs = out["recommendations"]
    estimates = [r["estimate"]["probability"] for r in recs["apply_next"] if r["estimate"]]
    assert estimates == sorted(estimates, reverse=True)
    assert "correlation" in recs["note"]
    assert recs["timing"]["ghost_after_days"] == recs["timing"]["latest_day"] + 2
    with db.session(paths) as conn:
        no_data = conn.execute("SELECT id FROM postings WHERE id NOT IN (SELECT posting_id"
                               " FROM salary_suggestions WHERE status = 'suggested')"
                               " LIMIT 1").fetchone()[0]
        assert recommend.salary_guidance(conn, no_data) is None


def test_salary_guidance_stays_within_the_evidence(history):
    paths = history("prescriptive")
    with db.session(paths) as conn:
        row = conn.execute("SELECT posting_id, range_min, range_max FROM salary_suggestions"
                           " WHERE status = 'suggested' AND is_current = 1 LIMIT 1").fetchone()
        guidance = recommend.salary_guidance(conn, row["posting_id"])
    assert row["range_min"] <= guidance["amount"] <= row["range_max"]


def test_resume_emphasis_only_names_resume_content(history, tmp_path):
    from jobtracker.core import resume as resume_service
    from tests.test_documents import make_formatted_docx

    paths = history("prescriptive")
    with db.session(paths) as conn:
        resume_service.import_resume(conn, paths, make_formatted_docx(tmp_path / "cv.docx"),
                                     language="en")
        result = recommend.resume_emphasis(conn, paths)
        text = Path(resume_service.list_current(conn, paths)[0]["text_path"]).read_text(
            encoding="utf-8").casefold()
    assert all(item["term"] in text for item in result["emphasis"])
    assert all(item["term"] not in insights.terms(text) for item in result["gaps"])


def test_experiments_propose_accept_and_conclude(history, cli):
    paths = history("prescriptive")
    _, out, _ = cli("experiments", "propose", "cover_letter", "--question",
                    "Does a cover letter help?", "--planned", "2")
    experiment_id = str(out["experiment"]["id"])
    _, accepted, _ = cli("experiments", "accept", experiment_id)
    assert accepted["experiment"]["status"] == "active"
    with db.session(paths) as conn:
        # Two applications after acceptance, resolved: the experiment concludes.
        conn.execute("UPDATE experiments SET accepted_at = ?",
                     ((TODAY - timedelta(days=200)).isoformat() + "T00:00:00Z",))
        result = recommend.experiment(conn, int(experiment_id))
    assert result["status"] == "concluded" and result["result"]["counts"]


def test_learning_board_api_gates_by_level(history):
    history("descriptive")
    client = TestClient(create_app(), base_url="http://127.0.0.1:8000")
    body = client.get("/api/learning?period=all").json()
    assert body["level"]["name"] == "descriptive"
    assert body["track_record"] is None and body["recommendations"] is None
    assert body["breakdowns"]["score_band"]["groups"]
    search_board = client.get("/api/search").json()
    assert all(r["estimate"] is None for r in search_board["results"])


def test_demo_clear_removes_the_learning_history(history, cli):
    paths = history("predictive")
    cli("demo", "clear")
    with db.session(paths) as conn:
        assert conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM postings").fetchone()[0] == 0


def test_an_applied_salary_cap_limits_the_ask(history, cli, send):
    paths = history("prescriptive")
    _, out, _ = send([lesson("salary_cap:demo", area="salary", effect={"salary_cap_pct": 0})],
                     "rules", "propose", "-")
    cli("rules", "apply", str(out["proposed"][0]["id"]))
    with db.session(paths) as conn:
        row = conn.execute("SELECT posting_id, amount FROM salary_suggestions"
                           " WHERE status = 'suggested' AND is_current = 1 LIMIT 1").fetchone()
        guidance = recommend.salary_guidance(conn, row["posting_id"])
    assert guidance["amount"] <= row["amount"]
