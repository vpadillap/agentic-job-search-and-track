"""outcome-insights: learning from results — statuses by name in the agent's history and
the offered salary (learn-from-results)."""
from __future__ import annotations

import json

from jobtracker.core import applications, db, insights, tracking
from tests.test_applications import client, jobs  # noqa: F401  (fixtures)


def details(cli, tmp_path, job, **fields):
    path = tmp_path / f"{job}.json"
    path.write_text(json.dumps(fields), encoding="utf-8")
    code, out, _ = cli("applications", "update", job, str(path))
    assert code == 0, out


def history_record(cli, job) -> dict:
    _, out, _ = cli("learning", "refresh")
    with open(out["history"]["path"], encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    return next(r for r in records if r.get("job_id") == job)


def test_status_path_by_name_in_the_panel_language(jobs, cli):  # noqa: F811
    job = jobs["altamar"]
    cli("applications", "set-status", job, "--to", "applied")
    cli("applications", "set-status", job, "--to", "Technical test sent", "--ends", "no")
    cli("applications", "set-status", job, "--to", "rejected")
    cli("config", "set", "language", "es")
    record = history_record(cli, job)
    assert (record["status"], record["status_key"], record["ended"]) == (
        "Rechazado", "rejected", True)
    assert [(s["status"], s["key"]) for s in record["status_path"]] == [
        ("Postulado", "applied"), ("Technical test sent", None), ("Rechazado", "rejected")]
    assert all(len(s["on"]) == 10 for s in record["status_path"])


def test_an_offered_salary_counts_as_an_offer(jobs, cli, tmp_path):  # noqa: F811
    job = jobs["altamar"]
    cli("applications", "set-status", job, "--to", "applied")
    cli("applications", "set-status", job, "--to", "Proposal received", "--ends", "no")
    with db.session(jobs["home"]) as conn:
        assert insights.summary(conn, "all")["offers"] == 0
    details(cli, tmp_path, job, offered_salary={"amount": 14000, "currency": "PEN"})
    with db.session(jobs["home"]) as conn:
        assert insights.summary(conn, "all")["offers"] == 1
    record = history_record(cli, job)
    assert record["outcome"] == "offer"
    assert record["offered_salary"]["amount"] == 14000
    assert record["applied_at"] and record["score"] == 86


def test_offered_against_asked_and_suggested(jobs, cli, tmp_path):  # noqa: F811
    with db.session(jobs["home"]) as conn:
        third = tracking.track(conn, [jobs["postings"]["B-7"]])[0]["job_id"]
    plan = {jobs["altamar"]: 9500, jobs["finlima"]: 9000, third: 10000}
    for job, offered in plan.items():
        cli("applications", "set-status", job, "--to", "applied")
        details(cli, tmp_path, job, asked_salary={"amount": 10000, "currency": "PEN"},
                offered_salary={"amount": offered, "currency": "PEN"})
    details(cli, tmp_path, third, offered_salary={"amount": 3000, "currency": "USD"})
    with db.session(jobs["home"]) as conn:
        offered = insights.summary(conn, "all")["offered_salary"]
        assert applications.at_application(conn, third)["offered_salary"]["currency"] == "USD"
    assert offered["offers_with_amount"] == 3
    assert offered["vs_asked"] == {"median_pct": -7.5, "cases": 2}    # USD offer not compared
    assert offered["vs_suggested"] == {"median_pct": -36.7, "cases": 1}  # 9500 vs 15000
