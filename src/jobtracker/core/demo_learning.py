"""A fictional history for trying the learning loop at each maturity level.

Applications with outcomes, dismissals with reasons, and corrections of the
agent's work-mode readings, generated deterministically with a planted,
realistic pattern (higher scores and stronger skills reach interview more often;
one title rarely does; onsite postings outside the user's areas get dismissed for
location). Fictional companies only; removed by `jobtracker demo clear`.
"""
from __future__ import annotations

import json
import random
import sqlite3
from datetime import date, datetime, timedelta

from . import applications, predict, scoring, search, tracking
from .errors import JobTrackerError
from .paths import Paths

LEVELS = ("collecting", "descriptive", "predictive", "prescriptive")
SIZE = {"collecting": 8, "descriptive": 26, "predictive": 72, "prescriptive": 72}
DISMISSALS = {"collecting": 8, "descriptive": 18, "predictive": 40, "prescriptive": 40}
TITLES = ("Senior Data Engineer", "Data Platform Engineer", "Analytics Engineer", "BI Engineer")
COMPANIES = ("Andes Retail", "Pacífico Seguros Demo", "Lúcuma Pagos", "Nazca Logística",
             "Chavín Salud", "Inca Energía Demo", "Vicuña Labs", "Paracas Media",
             "Moche Analytics", "Caral Fintech", "Tambo Foods", "Kuelap Travel")
PROVIDERS = ("linkedin", "bumeran", "indeed")
SKILLS = ("Python", "SQL", "Airflow", "dbt", "BigQuery", "Kafka", "Spark", "Looker")


def _description(title: str, company: str, skills: list[str], mode: str | None,
                 language: str) -> str:
    if language == "en":
        return (f"{company} is hiring a {title}.\n\nRequirements\n"
                + "".join(f"• {s}\n" for s in skills)
                + (f"Work mode: {mode}.\n" if mode else ""))
    return (f"{company} busca un/a {title}.\n\nRequisitos\n"
            + "".join(f"• {s}\n" for s in skills)
            + (f"Modalidad: {mode}.\n" if mode else ""))


def _components(quality: float, title: str) -> dict:
    title_points = 25 if title != "BI Engineer" else 15
    skills = round(12 + 23 * quality)
    seniority = 15 if quality > 0.4 else 11
    conditions = 13
    return {
        "title": {"points": title_points, "note": "Demo: target title."},
        "skills": {"points": skills, "note": "Demo: skills match.", "matched": [], "missing": []},
        "seniority": {"points": seniority, "note": "Demo: seniority."},
        "conditions": {"points": conditions, "note": "Demo: conditions."},
    }


def add_history(conn: sqlite3.Connection, paths: Paths, level: str,
                now: datetime | None = None) -> dict:
    if level not in LEVELS:
        raise JobTrackerError("invalid_level", f"level must be one of: {', '.join(LEVELS)}")
    rng = random.Random(42)
    now = now or datetime.now().astimezone()
    today = now.date()
    started = (now - timedelta(days=170)).astimezone().strftime("%Y-%m-%dT%H:%M:%SZ")
    run = search.start_run(conn, paths, 90, demo=True, started_at=started,
                           demo_providers=[{"id": p, "name": p.title()} for p in PROVIDERS],
                           demo_titles=list(TITLES))
    run_id = run["run_id"]
    count, dismissed = SIZE[level], DISMISSALS[level]
    records, plan = [], []
    for index in range(count + dismissed):
        applies = index < count
        title = TITLES[index % len(TITLES)]
        quality = rng.random()
        language = "en" if rng.random() < 0.3 else "es"
        mode = rng.choice(("remote", "hybrid", "onsite", None))
        if not applies and index % 3 != 2:   # most dismissals: onsite, low fit
            mode, quality = "onsite", quality * 0.5
        provider = PROVIDERS[index % len(PROVIDERS)]
        days_ago = rng.randint(30, 160) if applies else rng.randint(5, 160)
        company = f"{COMPANIES[index % len(COMPANIES)]} {index + 1}"
        skills = rng.sample(SKILLS, 4)
        records.append({
            "provider": provider, "external_id": f"demo-learning-{index}",
            "url": f"https://example.com/demo/learning/{index}", "title": title,
            "company": company, "location": "Lima", "country": "PE", "work_mode": mode,
            "contract_type": "full-time", "seniority": "Senior",
            "posted_at": (today - timedelta(days=days_ago + 2)).isoformat(),
            "description": _description(title, company, skills, mode, language),
            "language": language, "flags": []})
        plan.append({"applies": applies, "quality": quality, "title": title, "mode": mode,
                     "days_ago": days_ago, "provider": provider})
    report = search.import_postings(conn, run_id, records)
    ids = [item.get("posting_id") for item in report["postings"]]
    for provider in PROVIDERS:
        search.record_provider(conn, run_id, provider, "ok")
    search.finish_run(conn, run_id)

    applied = dismissed_count = corrected = 0
    for posting_id, item in zip(ids, plan, strict=True):
        scoring.set_score(conn, posting_id, {"components": _components(item["quality"],
                                                                      item["title"])},
                          run_id=run_id)
        decided = (today - timedelta(days=item["days_ago"]))
        if item["provider"] == "linkedin" and corrected < 6:
            # The user corrects the agent's reading of the work mode on this site.
            right = "onsite" if item["mode"] == "hybrid" else "hybrid"
            search.set_work_mode(conn, posting_id, right,
                                 "2 days at the office (demo)" if right == "hybrid" else None)
            corrected += 1
        if not item["applies"]:
            reason = "location" if item["mode"] == "onsite" else rng.choice(
                ("industry", "low_salary", "stack"))
            tracking.dismiss(conn, [posting_id], reason)
            conn.execute("UPDATE dismissals SET created_at = ? WHERE posting_id = ?",
                         (decided.isoformat() + "T12:00:00Z", posting_id))
            dismissed_count += 1
            continue
        job = tracking.track(conn, [posting_id])[0]["job_id"]
        conn.execute("UPDATE applications SET created_at = ? WHERE job_id = ?",
                     (decided.isoformat() + "T12:00:00Z", job))
        applications.set_status(conn, [job], "applied", today=decided)
        tailored = rng.random() < 0.6
        chance = 0.06 + 0.6 * item["quality"] + (0.08 if tailored else 0)
        if item["title"] == "BI Engineer":
            chance *= 0.15
        outcome = "interview" if rng.random() < chance else (
            "rejected" if rng.random() < 0.45 else "waiting")
        respond_after = rng.randint(2, 18)
        if outcome != "waiting":
            applications.set_status(conn, [job], outcome)
        snapshot = json.loads(conn.execute(
            "SELECT data FROM application_snapshots WHERE application_id = ?",
            (job,)).fetchone()["data"])
        snapshot.update(resume_kind="tailored" if tailored else "base",
                        channel=item["provider"].title(), applied_on=decided.isoformat())
        conn.execute("UPDATE application_snapshots SET data = ?, captured_at = ?"
                     " WHERE application_id = ?",
                     (json.dumps(snapshot), decided.isoformat() + "T12:00:00Z", job))
        conn.execute("UPDATE applications SET channel = ? WHERE job_id = ?",
                     (item["provider"].title(), job))
        # Backdate the status history: applied on the day, the outcome some days later.
        events = conn.execute("SELECT id, data FROM events WHERE entity_type = 'application'"
                              " AND entity_id = ? AND kind = 'status_changed' ORDER BY id",
                              (job,)).fetchall()
        for event in events:
            to = json.loads(event["data"]).get("to")
            when = decided if to == "applied" else decided + timedelta(days=respond_after)
            conn.execute("UPDATE events SET created_at = ? WHERE id = ?",
                         (when.isoformat() + "T12:00:00Z", event["id"]))
        applied += 1

    fitted = {}
    if level in ("predictive", "prescriptive"):
        fitted["interview"] = predict.fit(conn, today)["validation"]["passed"]
        fitted["fit"] = predict.fit_preference(conn, today)["validation"]["passed"]
        if level == "prescriptive":
            earlier = (now - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
            conn.execute("UPDATE analyses SET created_at = ? WHERE kind = 'interview'",
                         (earlier,))
            fitted["interview_again"] = predict.fit(conn, today)["validation"]["passed"]
    return {"level": level, "applications": applied, "dismissals": dismissed_count,
            "corrections": corrected, "fitted": fitted, "run_id": run_id,
            "today": date.isoformat(today)}
