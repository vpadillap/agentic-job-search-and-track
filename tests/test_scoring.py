"""posting-scoring: breakdown, validation, skills evidence, history, weights versions."""
from __future__ import annotations

import json

import pytest

from jobtracker.core import board, db, resume, scoring, tracking
from tests.helpers import make_docx
from tests.test_search import captures


def submission(**overrides) -> dict:
    components = {
        "title": {"points": 25, "note": "Matches the main target title."},
        "skills": {"points": 27, "note": "Python, SQL, Airflow match. Missing: Kafka.",
                   "matched": ["Python", "SQL", "Airflow"], "missing": ["Kafka"]},
        "seniority": {"points": 15, "note": "Asks for 5+ years; the resume shows 7."},
        "conditions": {"points": 14, "note": "Remote and full-time."},
    }
    for name, value in overrides.items():
        components[name] = {**components[name], **value}
    return {"components": components}


@pytest.fixture
def posting_id(searchable, cli, tmp_path) -> int:
    path = tmp_path / "captures.json"
    path.write_text(json.dumps(captures()[:1]), encoding="utf-8")
    _, run, _ = cli("run", "start")
    _, report, _ = cli("postings", "import", str(run["run_id"]), str(path))
    return report["postings"][0]["posting_id"]


@pytest.fixture
def score(cli, tmp_path):
    def run(posting: int, data: dict):
        path = tmp_path / "score.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return cli("score", "set", str(posting), str(path))
    return run


def test_total_is_the_sum_of_components_each_with_a_note(posting_id, score):
    code, out, _ = score(posting_id, submission())
    assert code == 0, out
    stored = out["score"]
    assert stored["total"] == sum(c["points"] for c in stored["components"]) == 86
    assert [c["component"] for c in stored["components"]] == list(scoring.COMPONENTS)
    assert all(c["note"] for c in stored["components"])


def test_history_is_neutral_until_the_learning_loop(posting_id, score):
    _, out, _ = score(posting_id, submission())
    history = out["score"]["components"][-1]
    assert history["points"] == 5 and history["max"] == 10 and history["neutral"] is True


def test_history_cannot_be_judged_by_the_agent(posting_id, score):
    data = submission()
    data["components"]["history"] = {"points": 10, "note": "great"}
    code, out, _ = score(posting_id, data)
    assert code == 1 and "history" in out["error"]["message"]


def test_points_above_a_maximum_are_rejected_and_nothing_is_stored(searchable, posting_id,
                                                                   score):
    code, out, _ = score(posting_id, submission(skills={"points": 36}))
    assert code == 1 and out["error"]["code"] == "invalid_score"
    with db.session(searchable) as conn:
        assert scoring.current(conn, posting_id) is None


def test_a_wrong_total_is_rejected(posting_id, score):
    data = submission()
    data["total"] = 90
    code, out, _ = score(posting_id, data)
    assert code == 1 and "does not match" in out["error"]["message"]


def test_every_component_needs_a_note(posting_id, score):
    code, _, _ = score(posting_id, submission(title={"note": " "}))
    assert code == 1


def test_missing_skill_must_be_named_in_the_skills_note(posting_id, score):
    code, out, _ = score(posting_id, submission(skills={"note": "Most skills match."}))
    assert code == 1 and "Kafka" in out["error"]["message"]
    code, out, _ = score(posting_id, submission())
    skills = next(c for c in out["score"]["components"] if c["component"] == "skills")
    assert skills["missing"] == ["Kafka"] and "Kafka" in skills["note"]


def test_rescore_against_a_new_resume_keeps_history_and_shows_the_change(
        searchable, posting_id, score, cli, tmp_path):
    with db.session(searchable) as conn:
        resume.import_resume(conn, searchable, make_docx(tmp_path / "cv1.docx"))
    _, first, _ = score(posting_id, submission())
    assert first["score"]["resume_ref"] == "1"
    with db.session(searchable) as conn:
        resume.import_resume(conn, searchable, make_docx(tmp_path / "cv2.docx"))
        assert [p["posting_id"] for p in board.pending(conn)] == [posting_id]
    _, second, _ = score(posting_id, submission(skills={
        "points": 33, "note": "All skills match.", "missing": []}))
    assert second["score"]["total"] == 92
    assert second["score"]["previous_total"] == 86
    assert second["score"]["resume_ref"] == "2"
    _, shown, _ = cli("score", "show", str(posting_id), "--history")
    assert [s["total"] for s in shown["history"]] == [92, 86]
    with db.session(searchable) as conn:
        assert board.pending(conn) == []


def test_the_score_current_when_applying_is_preserved(searchable, posting_id, score, cli):
    score(posting_id, submission())
    with db.session(searchable) as conn:
        tracking.track(conn, [posting_id], applied=True)
    score(posting_id, submission(title={"points": 10}))
    _, shown, _ = cli("score", "show", str(posting_id), "--history")
    assert shown["score"]["total"] == 71
    assert shown["at_application"]["total"] == 86


def test_weights_change_keeps_old_scores_on_their_version(posting_id, score, cli, tmp_path):
    _, before, _ = score(posting_id, submission())
    weights = tmp_path / "w.json"
    weights.write_text(json.dumps({"title": 20, "skills": 40, "seniority": 15,
                                   "conditions": 15, "history": 10}), encoding="utf-8")
    code, out, _ = cli("score", "weights", "--set", str(weights), "--note", "skills matter more")
    assert code == 0 and out["weights"]["version"] == 2
    _, after, _ = score(posting_id, submission(title={"points": 20}, skills={"points": 38}))
    assert before["score"]["weights_version"] == 1
    assert after["score"]["weights_version"] == 2
    _, shown, _ = cli("score", "show", str(posting_id), "--history")
    assert [s["weights_version"] for s in shown["history"]] == [2, 1]


def test_weights_must_add_up_to_100(workspace, cli, tmp_path):
    weights = tmp_path / "w.json"
    weights.write_text(json.dumps({"title": 30, "skills": 40, "seniority": 15,
                                   "conditions": 15, "history": 10}), encoding="utf-8")
    code, out, _ = cli("score", "weights", "--set", str(weights))
    assert code == 1 and "100" in out["error"]["message"]


def test_history_note_follows_the_panel_language(searchable, posting_id, score, cli):
    cli("config", "set", "language", "es")
    _, out, _ = score(posting_id, submission())
    assert out["score"]["components"][-1]["note"].startswith("Neutral hasta")
