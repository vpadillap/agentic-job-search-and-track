"""Read models for the panel: everything a board shows, loaded in one request."""
from __future__ import annotations

import json
import sqlite3

from . import profile as profile_service
from . import salary, scoring, search, tracking


def default_min_score(conn: sqlite3.Connection) -> int | None:
    """The minimum score shown by default, from the latest active rule that sets one."""
    for row in conn.execute(
        "SELECT effect FROM rules WHERE status = 'active' AND effect IS NOT NULL"
        " ORDER BY updated_at DESC, id DESC"
    ):
        effect = json.loads(row["effect"])
        value = effect.get("min_score_shown")
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100:
            return value
    return None


def _row(conn: sqlite3.Connection, posting_id: int, run_id: int) -> dict:
    item = search.posting(conn, posting_id)
    item["score"] = scoring.current(conn, posting_id)
    item["salary"] = salary.current(conn, posting_id)
    item["application"] = tracking.application(conn, posting_id)
    item["dismissal"] = tracking.dismissal(conn, posting_id)
    item["possible_duplicates"] = search.possible_duplicates(conn, posting_id, run_id)
    return item


def search_board(conn: sqlite3.Connection, run_id: int | None = None) -> dict:
    """The Search board: a run's summary, its new postings, and what was filtered out."""
    runs = search.list_runs(conn)
    run_id = run_id or search.latest_run_id(conn)
    if run_id is None:
        return {"run": None, "runs": runs, "results": [], "filtered": [],
                "default_min_score": default_min_score(conn)}
    results, filtered = [], []
    for row in conn.execute(
        "SELECT posting_id, outcome, reason, reason_detail, provider FROM run_results"
        " WHERE run_id = ? AND outcome IN ('new', 'filtered') ORDER BY id", (run_id,),
    ):
        if row["outcome"] == "new":
            results.append(_row(conn, row["posting_id"], run_id))
        else:
            item = search.posting(conn, row["posting_id"], detail=False)
            item.update(reason=row["reason"], reason_detail=row["reason_detail"])
            filtered.append(item)
    return {
        "run": search.summary(conn, run_id),
        "runs": runs,
        "results": results,
        "filtered": filtered,
        "default_min_score": default_min_score(conn),
    }


def counts(conn: sqlite3.Connection) -> dict:
    """Tab counters: untriaged new results of the latest run, and tracked applications."""
    run_id = search.latest_run_id(conn)
    new = 0
    if run_id is not None:
        new = conn.execute(
            "SELECT COUNT(*) FROM run_results r WHERE r.run_id = ? AND r.outcome = 'new'"
            " AND NOT EXISTS (SELECT 1 FROM dismissals d WHERE d.posting_id = r.posting_id)"
            " AND NOT EXISTS (SELECT 1 FROM applications a WHERE a.posting_id = r.posting_id)",
            (run_id,),
        ).fetchone()[0]
    active = conn.execute(
        "SELECT COUNT(*) FROM applications a JOIN statuses s ON s.id = a.status_id"
        " WHERE s.stage IN ('to_apply', 'applied', 'interview', 'offer')").fetchone()[0]
    return {"search": new, "applications": active}


def pending(conn: sqlite3.Connection) -> list[dict]:
    """Work items for the agent, derived from the data (nothing is stored)."""
    from . import resume

    items: list[dict] = []
    # A score judged against an earlier base resume (the base resume import
    # records `rescore_since`) needs a new score for every open posting.
    base = conn.execute("SELECT version FROM base_resumes WHERE is_current = 1").fetchone()
    if resume.rescore_since(conn) and base is not None:
        run_id = search.latest_run_id(conn)
        for row in conn.execute(
            "SELECT s.posting_id, p.title, p.company, a.job_id FROM scores s"
            " JOIN postings p ON p.id = s.posting_id"
            " LEFT JOIN applications a ON a.posting_id = s.posting_id"
            " WHERE s.is_current = 1 AND s.resume_kind = 'base'"
            " AND NOT EXISTS (SELECT 1 FROM documents d WHERE d.application_id = a.id"
            "      AND d.kind = 'resume_sent' AND d.is_current = 1)"
            " AND (s.resume_ref IS NULL OR s.resume_ref != ?)"
            " AND NOT EXISTS (SELECT 1 FROM dismissals d WHERE d.posting_id = s.posting_id)"
            " AND (a.job_id IS NOT NULL OR EXISTS (SELECT 1 FROM run_results r"
            "      WHERE r.posting_id = s.posting_id AND r.run_id = ? AND r.outcome = 'new'))"
            " ORDER BY s.posting_id", (str(base["version"]), run_id),
        ):
            items.append({"kind": "rescore", "posting_id": row["posting_id"],
                          "job_id": row["job_id"], "title": row["title"],
                          "company": row["company"],
                          "reason": "the base resume changed after this score"})
    # The resume the user actually sent replaces whatever the score was judged against.
    for row in conn.execute(
        "SELECT a.job_id, a.posting_id, p.title, p.company, d.file_name, d.version,"
        " sc.resume_kind, sc.resume_ref FROM documents d"
        " JOIN applications a ON a.id = d.application_id JOIN postings p ON p.id = a.posting_id"
        " LEFT JOIN scores sc ON sc.posting_id = a.posting_id AND sc.is_current = 1"
        " WHERE d.kind = 'resume_sent' AND d.is_current = 1 ORDER BY a.id"
    ):
        ref = f"{row['file_name']}#v{row['version']}"
        if row["resume_kind"] != "sent" or row["resume_ref"] != ref:
            items.append({"kind": "rescore", "posting_id": row["posting_id"],
                          "job_id": row["job_id"], "title": row["title"],
                          "company": row["company"], "resume": {"kind": "sent", "ref": ref},
                          "reason": "the user uploaded the resume actually sent"})
    return items


def header(conn: sqlite3.Connection) -> dict:
    active = profile_service.get_active(conn)
    titles = profile_service.included_titles(active)
    return {
        "profile": {"version": active["version"], "title": titles[0] if titles else None}
        if active else None,
        "pending": len(pending(conn)),
        "counts": counts(conn),
    }
