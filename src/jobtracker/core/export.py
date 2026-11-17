"""Export applications, their history, and rules to JSON and CSV in the private home."""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime

from .paths import Paths


def _applications(conn: sqlite3.Connection) -> list[dict]:
    return [{
        "job_id": r["job_id"], "season": r["season"], "status": r["status"],
        "status_ends": bool(r["ends"]), "applied_on": r["applied_on"],
        "title": r["title"], "company": r["company"], "provider": r["provider"],
        "url": r["url"], "location": r["location"], "work_mode": r["work_mode"],
        "asked_salary_amount": r["asked_salary_amount"],
        "asked_salary_currency": r["asked_salary_currency"],
        "asked_salary_basis": r["asked_salary_basis"],
        "offered_salary_amount": r["offered_salary_amount"],
        "offered_salary_currency": r["offered_salary_currency"],
        "offered_salary_basis": r["offered_salary_basis"],
        "channel": r["channel"], "contact": r["contact"], "notes": r["notes"],
        "next_step_on": r["next_step_on"], "next_step_note": r["next_step_note"],
        "tags": [t["tag"] for t in conn.execute(
            "SELECT tag FROM application_tags WHERE application_id = ? ORDER BY tag",
            (r["id"],))],
        "created_at": r["created_at"], "updated_at": r["updated_at"],
    } for r in conn.execute(
        "SELECT a.*, COALESCE(s.key, s.name_en) AS status, s.ends, se.number AS season,"
        " p.title, p.company, p.provider, p.url, p.location, p.work_mode"
        " FROM applications a JOIN statuses s ON s.id = a.status_id"
        " JOIN postings p ON p.id = a.posting_id LEFT JOIN seasons se ON se.id = a.season_id"
        " ORDER BY a.id").fetchall()]


def _events(conn: sqlite3.Connection) -> list[dict]:
    return [{"id": r["id"], "entity_type": r["entity_type"], "entity_id": r["entity_id"],
             "kind": r["kind"], "data": json.loads(r["data"]) if r["data"] else None,
             "created_at": r["created_at"]}
            for r in conn.execute("SELECT * FROM events ORDER BY id")]


def _rules(conn: sqlite3.Connection) -> list[dict]:
    return [{"id": r["id"], "origin": r["origin"], "status": r["status"], "area": r["area"],
             "text": r["text"], "evidence": r["evidence"],
             "effect": json.loads(r["effect"]) if r["effect"] else None,
             "created_at": r["created_at"], "updated_at": r["updated_at"]}
            for r in conn.execute("SELECT * FROM rules ORDER BY id")]


def _csv_value(value: object) -> object:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def export(conn: sqlite3.Connection, paths: Paths) -> dict:
    """Write applications, events, and rules as JSON and CSV into a new folder of
    `exports/` named by local time (YYYYMMDD-HHMM). Nothing existing is replaced."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    target = paths.exports / stamp
    suffix = 2
    while target.exists():
        target = paths.exports / f"{stamp}-{suffix}"
        suffix += 1
    target.mkdir(parents=True)
    tables = {"applications": _applications(conn), "events": _events(conn),
              "rules": _rules(conn)}
    files = []
    for name, rows in tables.items():
        json_path = target / f"{name}.json"
        json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        csv_path = target / f"{name}.csv"
        # utf-8-sig: Excel on Windows opens accented text correctly.
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            fields = list(rows[0]) if rows else ["empty"]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: _csv_value(v) for k, v in row.items()})
        files += [str(json_path), str(csv_path)]
    return {"folder": str(target), "files": files,
            "counts": {name: len(rows) for name, rows in tables.items()}}
