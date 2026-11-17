"""The versioned profile: job needs and target titles.

Every change creates a new version inside the active season; earlier versions
stay readable for analysis.
"""
from __future__ import annotations

import json
import re
import sqlite3

from .db import bump_changes, now_iso
from .errors import JobTrackerError

WORK_MODES = ("remote", "hybrid", "onsite")
CONTRACT_TYPES = ("full-time", "part-time", "contractor")
REMOTE_SCOPES = ("country", "region", "worldwide")
TITLE_STATES = ("included", "excluded", "suggested", "under_review")
SALARY_BASES = ("gross", "net")

DEFAULTS: dict[str, object] = {
    "work_modes": [],
    "contract_types": [],
    "country": None,
    "locations": [],
    "remote_scope": None,
    "remote_region": None,
    "minimum_salary": None,
    "languages": [],
    "seniority": None,
    "industries_preferred": [],
    "industries_avoided": [],
    "companies_excluded": [],
    "availability": None,
    "work_authorization": None,
    "posting_age_days": 7,
    "additional_facts": [],
    "titles": [],
}


def _fail(field: str, message: str):
    raise JobTrackerError("invalid_profile", f"{field}: {message}", field=field)


def _choices(field: str, value: object, allowed: tuple[str, ...]) -> list[str]:
    if not isinstance(value, list) or any(item not in allowed for item in value):
        _fail(field, f"must be a list with values from: {', '.join(allowed)}")
    return list(dict.fromkeys(value))  # type: ignore[arg-type]


def _strings(field: str, value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(i, str) or not i.strip() for i in value):
        _fail(field, "must be a list of non-empty texts")
    return [item.strip() for item in value]  # type: ignore[union-attr]


def _optional_text(field: str, value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        _fail(field, "must be text or null")
    return value.strip()  # type: ignore[union-attr]


def _salary(value: object) -> dict | None:
    field = "minimum_salary"
    if value is None:
        return None
    if not isinstance(value, dict):
        _fail(field, "must be an object or null")
    amount = value.get("amount")  # type: ignore[union-attr]
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        _fail(field, "'amount' must be a positive whole number")
    currency = value.get("currency")  # type: ignore[union-attr]
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        _fail(field, "'currency' must be a 3-letter ISO code such as PEN or USD")
    basis = value.get("basis", "gross")  # type: ignore[union-attr]
    if basis not in SALARY_BASES:
        _fail(field, "'basis' must be gross or net")
    return {"amount": amount, "currency": currency, "period": "month", "basis": basis}


def _languages(value: object) -> list[dict]:
    field = "languages"
    if not isinstance(value, list):
        _fail(field, "must be a list")
    result = []
    for item in value:  # type: ignore[union-attr]
        if not isinstance(item, dict) or not isinstance(item.get("language"), str):
            _fail(field, "each entry needs a 'language'")
        entry = {"language": item["language"].strip()}
        if item.get("level") is not None:
            entry["level"] = str(item["level"]).strip()
        result.append(entry)
    return result


def _titles(value: object) -> list[dict]:
    field = "titles"
    if not isinstance(value, list):
        _fail(field, "must be a list")
    seen: set[str] = set()
    result = []
    for item in value:  # type: ignore[union-attr]
        if not isinstance(item, dict):
            _fail(field, "each entry must be an object")
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            _fail(field, "each entry needs a 'title'")
        title = " ".join(title.split())
        if title.casefold() in seen:
            _fail(field, f"'{title}' appears more than once")
        seen.add(title.casefold())
        state = item.get("state", "suggested")
        if state not in TITLE_STATES:
            _fail(field, f"state of '{title}' must be one of: {', '.join(TITLE_STATES)}")
        entry = {"title": title, "state": state}
        if item.get("reason"):
            entry["reason"] = str(item["reason"]).strip()
        result.append(entry)
    return result


def validate(data: object) -> dict:
    """Return a complete, normalized profile or raise `invalid_profile`."""
    if not isinstance(data, dict):
        raise JobTrackerError("invalid_profile", "the profile must be an object")
    unknown = sorted(set(data) - set(DEFAULTS))
    if unknown:
        _fail(unknown[0], "is not a profile field")
    merged = {**DEFAULTS, **data}

    country = merged["country"]
    if country is not None and (
        not isinstance(country, str) or not re.fullmatch(r"[A-Z]{2}", country)
    ):
        _fail("country", "must be a 2-letter ISO country code such as PE, or null")
    scope = merged["remote_scope"]
    if scope is not None and scope not in REMOTE_SCOPES:
        _fail("remote_scope", f"must be one of: {', '.join(REMOTE_SCOPES)}, or null")
    age = merged["posting_age_days"]
    if isinstance(age, bool) or not isinstance(age, int) or not 1 <= age <= 90:
        _fail("posting_age_days", "must be a whole number from 1 to 90")

    return {
        "work_modes": _choices("work_modes", merged["work_modes"], WORK_MODES),
        "contract_types": _choices("contract_types", merged["contract_types"], CONTRACT_TYPES),
        "country": country,
        "locations": _strings("locations", merged["locations"]),
        "remote_scope": scope,
        "remote_region": _optional_text("remote_region", merged["remote_region"]),
        "minimum_salary": _salary(merged["minimum_salary"]),
        "languages": _languages(merged["languages"]),
        "seniority": _optional_text("seniority", merged["seniority"]),
        "industries_preferred": _strings("industries_preferred", merged["industries_preferred"]),
        "industries_avoided": _strings("industries_avoided", merged["industries_avoided"]),
        "companies_excluded": _strings("companies_excluded", merged["companies_excluded"]),
        "availability": _optional_text("availability", merged["availability"]),
        "work_authorization": _optional_text("work_authorization", merged["work_authorization"]),
        "posting_age_days": age,
        "additional_facts": _strings("additional_facts", merged["additional_facts"]),
        "titles": _titles(merged["titles"]),
    }


# ── storage ───────────────────────────────────────────────────────────────

def _base_resumes(conn: sqlite3.Connection) -> list[dict]:
    """The user's current resume in each language."""
    return [{
        "language": row["language"], "version": row["version"],
        "file_name": row["file_name"], "text_name": row["text_name"],
        "original_name": row["original_name"], "imported_at": row["imported_at"],
        "text_source": row["text_source"], "translated_from": row["translated_from"],
    } for row in conn.execute("SELECT * FROM base_resumes WHERE is_current = 1"
                              " ORDER BY COALESCE(language, ''), id")]


def _to_dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    season = conn.execute("SELECT number FROM seasons WHERE id = ?", (row["season_id"],)).fetchone()
    return {
        "version": row["version"],
        "season": season["number"],
        "active": bool(row["is_active"]),
        "created_at": row["created_at"],
        **json.loads(row["data"]),
        "base_resumes": _base_resumes(conn),
    }


def get_active(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT * FROM profile_versions WHERE is_active = 1").fetchone()
    return _to_dict(conn, row) if row else None


def get_version(conn: sqlite3.Connection, version: int) -> dict:
    row = conn.execute(
        "SELECT p.* FROM profile_versions p JOIN seasons s ON s.id = p.season_id"
        " WHERE s.is_active = 1 AND p.version = ?", (version,),
    ).fetchone()
    if row is None:
        raise JobTrackerError("not_found", f"There is no profile version {version}")
    return _to_dict(conn, row)


def history(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT p.version, p.created_at, p.is_active, s.number AS season FROM profile_versions p"
        " JOIN seasons s ON s.id = p.season_id ORDER BY s.number, p.version"
    )
    return [
        {"season": r["season"], "version": r["version"], "created_at": r["created_at"],
         "active": bool(r["is_active"])}
        for r in rows
    ]


def _stored_data(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT data FROM profile_versions WHERE is_active = 1").fetchone()
    return json.loads(row["data"]) if row else None


def _create_version(conn: sqlite3.Connection, data: dict, change: str) -> dict:
    season = conn.execute("SELECT id FROM seasons WHERE is_active = 1").fetchone()
    if season is None:
        raise JobTrackerError("no_active_season", "There is no active season")
    latest = conn.execute(
        "SELECT COALESCE(MAX(version), 0) FROM profile_versions WHERE season_id = ?",
        (season["id"],),
    ).fetchone()[0]
    now = now_iso()
    conn.execute("UPDATE profile_versions SET is_active = 0 WHERE is_active = 1")
    conn.execute(
        "INSERT INTO profile_versions (season_id, version, data, created_at, is_active)"
        " VALUES (?, ?, ?, ?, 1)",
        (season["id"], latest + 1, json.dumps(data, ensure_ascii=False), now),
    )
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
        " VALUES ('profile', ?, 'version_created', ?, ?)",
        (str(latest + 1), json.dumps({"change": change}), now),
    )
    bump_changes(conn)
    return get_active(conn)  # type: ignore[return-value]


def update(conn: sqlite3.Connection, changes: object) -> dict:
    """Apply `changes` over the active profile and store the result as a new version.

    Fields that are not mentioned keep their value. Nothing is stored when the
    result is invalid or identical to the active version.
    """
    if not isinstance(changes, dict) or not changes:
        raise JobTrackerError("invalid_profile", "expected an object with the fields to change")
    current = _stored_data(conn)
    data = validate({**(current or {}), **changes})
    if current is not None and data == current:
        return get_active(conn)  # type: ignore[return-value]
    return _create_version(conn, data, "fields: " + ", ".join(sorted(changes)))


def _require_profile(conn: sqlite3.Connection) -> dict:
    current = _stored_data(conn)
    if current is None:
        raise JobTrackerError(
            "no_profile", "There is no profile yet. Store the job needs first (profile set)."
        )
    return current


def set_titles(conn: sqlite3.Connection, changes: object) -> dict:
    """Set the state of several target titles at once, as one new profile version.

    Each change is {"title", "state", "reason"?}. New titles are added. A
    reason belongs to a state: changing the state drops the old reason unless
    a new one is given.
    """
    current = _require_profile(conn)
    if not isinstance(changes, list) or not changes:
        raise JobTrackerError(
            "invalid_profile", "expected a non-empty list of title changes", field="titles"
        )
    titles = [dict(item) for item in current["titles"]]
    index = {item["title"].casefold(): item for item in titles}
    for change in changes:
        if not isinstance(change, dict) or not isinstance(change.get("title"), str):
            raise JobTrackerError(
                "invalid_profile", "each change needs a 'title' and a 'state'", field="titles"
            )
        name = " ".join(change["title"].split())
        state = change.get("state")
        if not name or state not in TITLE_STATES:
            raise JobTrackerError(
                "invalid_profile",
                f"state of '{name}' must be one of: {', '.join(TITLE_STATES)}", field="titles",
            )
        reason = change.get("reason")
        item = index.get(name.casefold())
        if item is None:
            item = {"title": name, "state": state}
            titles.append(item)
            index[name.casefold()] = item
        elif item["state"] != state:
            item["state"] = state
            item.pop("reason", None)
        if reason:
            item["reason"] = str(reason).strip()
    data = validate({**current, "titles": titles})
    if data == current:
        return get_active(conn)  # type: ignore[return-value]
    return _create_version(conn, data, f"{len(changes)} title change(s)")


def set_title_state(
    conn: sqlite3.Connection, title: str, state: str, reason: str | None = None
) -> dict:
    """Set the state of one target title (adding it if new) as a new profile version."""
    return set_titles(conn, [{"title": title, "state": state, "reason": reason}])


def remove_title(conn: sqlite3.Connection, title: str) -> dict:
    """Take a title out of the profile entirely (for example a mistyped one)."""
    current = _require_profile(conn)
    name = " ".join(title.split()).casefold()
    titles = [item for item in current["titles"] if item["title"].casefold() != name]
    if len(titles) == len(current["titles"]):
        raise JobTrackerError("not_found", f"'{title}' is not among the profile's titles")
    return _create_version(conn, validate({**current, "titles": titles}), "title removed")


def included_titles(profile: dict | None) -> list[str]:
    if not profile:
        return []
    return [item["title"] for item in profile["titles"] if item["state"] == "included"]
