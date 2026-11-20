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


def search_board(conn: sqlite3.Connection, group: int | None = None,
                 season: int | None = None, run: int | None = None) -> dict:
    """The Search board: one page per group of runs (the searches of one day, or the
    days the user joined): the summary added up, its new postings once each, and what
    was filtered out. Groups of the active season unless `season` names an earlier one;
    `run` opens the page of that run."""
    groups = search.list_groups(conn, season)
    if group is None and run is not None:
        group = search.group_of_run(conn, run)
    group = group or search.latest_group_id(conn, season)
    if group is None:
        return {"run": None, "runs": groups, "results": [], "filtered": [],
                "default_min_score": default_min_score(conn)}
    run_ids = search.group_run_ids(conn, group)
    if not run_ids:
        raise search.JobTrackerError("not_found", f"There is no search page {group}")
    newest = run_ids[-1]
    marks = ",".join("?" * len(run_ids))
    chosen: dict[int, sqlite3.Row] = {}
    # Each posting once, with the newest run's outcome.
    for row in conn.execute(
        "SELECT r.id, r.posting_id, r.outcome, r.reason, r.reason_detail FROM run_results r"
        f" JOIN search_runs s ON s.id = r.run_id WHERE r.run_id IN ({marks})"
        " AND r.outcome IN ('new', 'filtered') ORDER BY s.started_at DESC, s.id DESC, r.id",
        run_ids,
    ):
        chosen.setdefault(row["posting_id"], row)
    results, filtered = [], []
    for row in sorted(chosen.values(), key=lambda r: r["id"]):
        if row["outcome"] == "new":
            results.append(_row(conn, row["posting_id"], newest))
        else:
            item = search.posting(conn, row["posting_id"], detail=False)
            item.update(reason=row["reason"], reason_detail=row["reason_detail"])
            filtered.append(item)
    from . import learning

    estimates = learning.estimates_for(conn, [r["id"] for r in results])
    for item in results:
        item["estimate"] = estimates[item["id"]]["interview"]
        item["fit"] = estimates[item["id"]]["fit"]
    return {
        "run": search.group_summary(conn, group),
        "runs": groups,
        "results": results,
        "filtered": filtered,
        "default_min_score": default_min_score(conn),
    }


def counts(conn: sqlite3.Connection) -> dict:
    """Tab counters: untriaged new results of the latest run, tracked applications, and
    lessons waiting for the user's decision."""
    group = search.latest_group_id(conn)
    new = 0
    if group is not None:
        new = conn.execute(
            "SELECT COUNT(DISTINCT r.posting_id) FROM run_results r"
            " JOIN search_runs s ON s.id = r.run_id WHERE s.group_id = ? AND r.outcome = 'new'"
            " AND NOT EXISTS (SELECT 1 FROM dismissals d WHERE d.posting_id = r.posting_id)"
            " AND NOT EXISTS (SELECT 1 FROM applications a WHERE a.posting_id = r.posting_id)",
            (group,),
        ).fetchone()[0]
    active = conn.execute(
        "SELECT COUNT(*) FROM applications a JOIN statuses s ON s.id = a.status_id"
        " WHERE s.ends = 0 AND a.season_id = (SELECT id FROM seasons WHERE is_active = 1)"
    ).fetchone()[0]
    proposed = conn.execute("SELECT COUNT(*) FROM rules WHERE origin = 'learned'"
                            " AND status = 'proposed'").fetchone()[0]
    return {"search": new, "applications": active, "learning": proposed}


def _restored_to_score(conn: sqlite3.Connection) -> list[dict]:
    """Postings the user restored from the filtered-out list that still have no score, on
    the latest page, once their search is finished (a running search scores them)."""
    group = search.latest_group_id(conn)
    if group is None:
        return []
    return [{"kind": "score", "posting_id": row["posting_id"], "job_id": row["job_id"],
             "title": row["title"], "company": row["company"],
             "reason": "the user restored it from the filtered-out list"}
            for row in conn.execute(
        "SELECT DISTINCT r.posting_id, p.title, p.company, a.job_id FROM run_results r"
        " JOIN search_runs sr ON sr.id = r.run_id JOIN postings p ON p.id = r.posting_id"
        " LEFT JOIN applications a ON a.posting_id = r.posting_id"
        " WHERE sr.group_id = ? AND sr.status = 'finished' AND r.outcome = 'new'"
        " AND EXISTS (SELECT 1 FROM events e WHERE e.entity_type = 'posting'"
        "      AND e.entity_id = CAST(r.posting_id AS TEXT) AND e.kind = 'filter_restored')"
        " AND NOT EXISTS (SELECT 1 FROM scores sc WHERE sc.posting_id = r.posting_id"
        "      AND sc.is_current = 1)"
        " AND NOT EXISTS (SELECT 1 FROM dismissals d WHERE d.posting_id = r.posting_id)"
        " ORDER BY r.posting_id", (group,))]


def pending(conn: sqlite3.Connection) -> list[dict]:
    """Work items for the agent, derived from the data (nothing is stored)."""
    from . import resume

    items: list[dict] = []
    # A score judged against an earlier base resume (the base resume import
    # records `rescore_since`) needs a new score for every open posting.
    base = conn.execute("SELECT 1 FROM base_resumes WHERE is_current = 1").fetchone()
    if resume.rescore_since(conn) and base is not None:
        group = search.latest_group_id(conn)
        for row in conn.execute(
            "SELECT s.posting_id, p.title, p.company, a.job_id FROM scores s"
            " JOIN postings p ON p.id = s.posting_id"
            " LEFT JOIN applications a ON a.posting_id = s.posting_id"
            " WHERE s.is_current = 1 AND s.resume_kind = 'base'"
            " AND NOT EXISTS (SELECT 1 FROM documents d WHERE d.application_id = a.id"
            "      AND d.kind = 'resume_sent' AND d.is_current = 1)"
            # stale: judged against a version a newer one in its language replaced
            " AND (s.resume_ref IS NULL OR EXISTS (SELECT 1 FROM base_resumes r"
            "      WHERE CAST(r.version AS TEXT) = s.resume_ref AND r.is_current = 0))"
            " AND NOT EXISTS (SELECT 1 FROM dismissals d WHERE d.posting_id = s.posting_id)"
            " AND (a.season_id = (SELECT id FROM seasons WHERE is_active = 1)"
            "      OR (a.id IS NULL AND EXISTS (SELECT 1 FROM run_results r"
            "      JOIN search_runs sr ON sr.id = r.run_id"
            "      WHERE r.posting_id = s.posting_id AND sr.group_id = ? AND r.outcome = 'new')))"
            " ORDER BY s.posting_id", (group,),
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
        " WHERE d.kind = 'resume_sent' AND d.is_current = 1"
        " AND a.season_id = (SELECT id FROM seasons WHERE is_active = 1) ORDER BY a.id"
    ):
        ref = f"{row['file_name']}#v{row['version']}"
        if row["resume_kind"] != "sent" or row["resume_ref"] != ref:
            items.append({"kind": "rescore", "posting_id": row["posting_id"],
                          "job_id": row["job_id"], "title": row["title"],
                          "company": row["company"], "resume": {"kind": "sent", "ref": ref},
                          "reason": "the user uploaded the resume actually sent"})
    # A tailored resume replaces the base one, unless the user uploaded the one they sent.
    for row in conn.execute(
        "SELECT a.job_id, a.posting_id, p.title, p.company, d.file_name, d.version,"
        " sc.resume_kind, sc.resume_ref FROM documents d"
        " JOIN applications a ON a.id = d.application_id JOIN postings p ON p.id = a.posting_id"
        " LEFT JOIN scores sc ON sc.posting_id = a.posting_id AND sc.is_current = 1"
        " WHERE d.kind = 'resume_proposed' AND d.is_current = 1"
        " AND a.season_id = (SELECT id FROM seasons WHERE is_active = 1)"
        " AND NOT EXISTS (SELECT 1 FROM documents s WHERE s.application_id = a.id"
        "      AND s.kind = 'resume_sent' AND s.is_current = 1) ORDER BY a.id"
    ):
        ref = f"{row['file_name']}#v{row['version']}"
        if row["resume_kind"] != "tailored" or row["resume_ref"] != ref:
            items.append({"kind": "rescore", "posting_id": row["posting_id"],
                          "job_id": row["job_id"], "title": row["title"],
                          "company": row["company"], "resume": {"kind": "tailored", "ref": ref},
                          "reason": "a tailored resume was registered"})
    # A weights lesson the user applied: open postings scored with older weights.
    active = conn.execute("SELECT version FROM score_weights WHERE is_active = 1").fetchone()
    group = search.latest_group_id(conn)
    for row in conn.execute(
        "SELECT sc.posting_id, sc.resume_kind, sc.resume_ref, p.title, p.company, a.job_id"
        " FROM scores sc JOIN postings p ON p.id = sc.posting_id"
        " LEFT JOIN applications a ON a.posting_id = sc.posting_id"
        " LEFT JOIN statuses st ON st.id = a.status_id"
        " WHERE sc.is_current = 1 AND sc.weights_version != ?"
        " AND NOT EXISTS (SELECT 1 FROM dismissals d WHERE d.posting_id = sc.posting_id)"
        " AND ((st.ends = 0 AND a.season_id = (SELECT id FROM seasons WHERE is_active = 1))"
        "      OR (a.id IS NULL AND EXISTS (SELECT 1 FROM run_results r"
        "          JOIN search_runs sr ON sr.id = r.run_id"
        "          WHERE r.posting_id = sc.posting_id AND sr.group_id = ? AND r.outcome = 'new')))"
        " ORDER BY sc.posting_id", (active["version"] if active else 0, group),
    ):
        items.append({"kind": "rescore", "posting_id": row["posting_id"],
                      "job_id": row["job_id"], "title": row["title"], "company": row["company"],
                      "resume": {"kind": row["resume_kind"], "ref": row["resume_ref"]},
                      "reason": "the score weights changed (a lesson you applied)"})
    # One rescore per posting, against the most specific resume: sent > tailored > base.
    rank = {"sent": 2, "tailored": 1}
    best: dict[int, dict] = {}
    for item in items:
        kind = rank.get((item.get("resume") or {}).get("kind"), 0)
        held = best.get(item["posting_id"])
        if held is None or kind > rank.get((held.get("resume") or {}).get("kind"), 0):
            best[item["posting_id"]] = item
    items = [item for item in items if best[item["posting_id"]] is item]
    items.extend(_restored_to_score(conn))
    items.extend(_document_items(conn))
    return items


def _document_items(conn: sqlite3.Connection) -> list[dict]:
    """Documents missing on applications not yet applied to, most promising first."""
    items: list[dict] = []
    for row in conn.execute(
        "SELECT a.id, a.job_id, a.posting_id, a.cover_letter_need, p.title, p.company,"
        " sc.total,"
        " (SELECT COUNT(*) FROM form_questions q WHERE q.posting_id = a.posting_id) AS questions,"
        " (SELECT COUNT(*) FROM form_answers f WHERE f.application_id = a.id"
        "    AND f.state = 'current') AS answered,"
        " EXISTS (SELECT 1 FROM documents d WHERE d.application_id = a.id AND d.is_current = 1"
        "    AND d.kind IN ('resume_proposed', 'resume_sent')) AS has_resume,"
        " EXISTS (SELECT 1 FROM documents d WHERE d.application_id = a.id AND d.is_current = 1"
        "    AND d.kind = 'cover_letter') AS has_letter"
        " FROM applications a JOIN statuses s ON s.id = a.status_id"
        " JOIN postings p ON p.id = a.posting_id"
        " LEFT JOIN scores sc ON sc.posting_id = a.posting_id AND sc.is_current = 1"
        " WHERE a.applied_on IS NULL AND s.ends = 0"
        " AND a.season_id = (SELECT id FROM seasons WHERE is_active = 1)"
        " ORDER BY COALESCE(sc.total, -1) DESC, a.id"
    ):
        base = {"posting_id": row["posting_id"], "job_id": row["job_id"],
                "title": row["title"], "company": row["company"], "score": row["total"]}
        if not row["has_resume"]:
            items.append({**base, "kind": "resume", "reason": "no tailored resume yet"})
        if row["cover_letter_need"] is None:
            items.append({**base, "kind": "cover_letter",
                          "reason": "not decided yet whether a cover letter is needed"})
        elif row["cover_letter_need"] == "required" and not row["has_letter"]:
            items.append({**base, "kind": "cover_letter", "reason": "cover letter required"})
        if row["questions"] > row["answered"]:
            items.append({**base, "kind": "form_answers",
                          "reason": f"{row['questions'] - row['answered']} of "
                                    f"{row['questions']} form questions without an answer",
                          "missing": row["questions"] - row["answered"]})
    return items


def header(conn: sqlite3.Connection) -> dict:
    active = profile_service.get_active(conn)
    titles = profile_service.included_titles(active)
    season = conn.execute("SELECT number, label, started_at FROM seasons WHERE is_active = 1"
                          ).fetchone()
    return {
        "season": dict(season) if season else None,
        "profile": {"version": active["version"], "title": titles[0] if titles else None}
        if active else None,
        "pending": len(pending(conn)),
        "counts": counts(conn),
    }
