"""Companies the agentic-search provider found, remembered per season.

Each run revisits the known companies' careers pages for the titles they were
found for, then discovers new ones. When the user asks for different companies,
the agent leaves every known company out of discovery. A company the user excluded
is never explored again in the season.
"""
from __future__ import annotations

import json
import sqlite3

from . import normalize
from .db import bump_changes, now_iso
from .errors import JobTrackerError


def _fail(message: str, **details: object):
    raise JobTrackerError("invalid_company", message, **details)


def _season(conn: sqlite3.Connection) -> int | None:
    row = conn.execute("SELECT id FROM seasons WHERE is_active = 1").fetchone()
    return row["id"] if row else None


def _dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "name": row["name"], "careers_url": row["careers_url"],
        "found_via": row["found_via"], "titles": json.loads(row["titles"]),
        "first_seen_at": row["first_seen_at"], "last_checked_at": row["last_checked_at"],
        "last_matches": row["last_matches"], "excluded": bool(row["excluded"]),
        "excluded_reason": row["excluded_reason"],
    }


def list_companies(conn: sqlite3.Connection, *, excluded: bool | None = None) -> list[dict]:
    """The active season's companies; `excluded` True/False filters, None lists all."""
    query = "SELECT * FROM companies WHERE season_id IS ?"
    params: list[object] = [_season(conn)]
    if excluded is not None:
        query += " AND excluded = ?"
        params.append(int(excluded))
    return [_dict(row) for row in conn.execute(query + " ORDER BY name COLLATE NOCASE, id",
                                               params)]


def _validate(record: object, index: int) -> dict:
    where = f"company {index + 1}"
    if not isinstance(record, dict):
        _fail(f"{where}: must be an object")
    name = record.get("name")  # type: ignore[union-attr]
    if not isinstance(name, str) or not name.strip():
        _fail(f"{where}: 'name' is required", field="name")
    url = normalize.safe_url(record.get("careers_url"), f"{where}: careers_url")  # type: ignore[union-attr]
    via = record.get("found_via")  # type: ignore[union-attr]
    if via is not None and (not isinstance(via, str) or not via.strip()):
        _fail(f"{where}: 'found_via' must be text or omitted", field="found_via")
    title = record.get("title")  # type: ignore[union-attr]
    if title is not None and (not isinstance(title, str) or not title.strip()):
        _fail(f"{where}: 'title' must be text or omitted", field="title")
    matches = record.get("matches")  # type: ignore[union-attr]
    if matches is not None and (isinstance(matches, bool) or not isinstance(matches, int)
                                or matches < 0):
        _fail(f"{where}: 'matches' must be a whole number from 0", field="matches")
    return {"name": normalize.clean_text(name), "careers_url": url,  # type: ignore[union-attr]
            "url_key": normalize.url_key(url),
            "found_via": via.strip() if isinstance(via, str) else None,
            "title": normalize.clean_text(title) if isinstance(title, str) else None,
            "matches": matches}


def record(conn: sqlite3.Connection, records: object) -> dict:
    """Create or update companies the agent found or revisited in this run. Every record
    is validated before anything is stored."""
    if not isinstance(records, list):
        _fail("expected a list of companies")
    items = [_validate(item, index) for index, item in enumerate(records)]
    season, now = _season(conn), now_iso()
    created, updated, excluded = [], [], []
    for item in items:
        row = conn.execute("SELECT * FROM companies WHERE season_id IS ? AND url_key = ?",
                           (season, item["url_key"])).fetchone()
        if row is None:
            titles = [item["title"]] if item["title"] else []
            cursor = conn.execute(
                "INSERT INTO companies (season_id, name, careers_url, url_key, found_via, titles,"
                " first_seen_at, last_checked_at, last_matches) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (season, item["name"], item["careers_url"], item["url_key"], item["found_via"],
                 json.dumps(titles, ensure_ascii=False), now, now, item["matches"]))
            created.append(int(cursor.lastrowid))  # type: ignore[arg-type]
            continue
        titles = json.loads(row["titles"])
        if item["title"] and item["title"] not in titles:
            titles.append(item["title"])
        conn.execute(
            "UPDATE companies SET name = ?, titles = ?, last_checked_at = ?,"
            " last_matches = COALESCE(?, last_matches) WHERE id = ?",
            (item["name"], json.dumps(titles, ensure_ascii=False), now, item["matches"],
             row["id"]))
        (excluded if row["excluded"] else updated).append(row["id"])
    bump_changes(conn)
    return {"created": created, "updated": updated, "excluded": excluded,
            "companies": list_companies(conn)}


def _find(conn: sqlite3.Connection, ref: str) -> sqlite3.Row:
    season = _season(conn)
    ref = (ref or "").strip()
    if ref.isdigit():
        row = conn.execute("SELECT * FROM companies WHERE season_id IS ? AND id = ?",
                           (season, int(ref))).fetchone()
    else:
        row = conn.execute("SELECT * FROM companies WHERE season_id IS ? AND url_key = ?",
                           (season, normalize.url_key(ref))).fetchone()
    if row is None:
        raise JobTrackerError("not_found", f"There is no company '{ref}' in this season")
    return row


def exclude(conn: sqlite3.Connection, ref: str, reason: str | None) -> dict:
    row = _find(conn, ref)
    conn.execute("UPDATE companies SET excluded = 1, excluded_reason = ? WHERE id = ?",
                 ((reason or "").strip() or None, row["id"]))
    bump_changes(conn)
    return _dict(conn.execute("SELECT * FROM companies WHERE id = ?", (row["id"],)).fetchone())


def include(conn: sqlite3.Connection, ref: str) -> dict:
    row = _find(conn, ref)
    conn.execute("UPDATE companies SET excluded = 0, excluded_reason = NULL WHERE id = ?",
                 (row["id"],))
    bump_changes(conn)
    return _dict(conn.execute("SELECT * FROM companies WHERE id = ?", (row["id"],)).fetchone())


def summary(conn: sqlite3.Connection) -> dict:
    """Counts for `jt context`."""
    rows = conn.execute("SELECT excluded, COUNT(*) AS n FROM companies WHERE season_id IS ?"
                        " GROUP BY excluded", (_season(conn),)).fetchall()
    counts = {bool(r["excluded"]): r["n"] for r in rows}
    return {"known": counts.get(False, 0), "excluded": counts.get(True, 0)}
