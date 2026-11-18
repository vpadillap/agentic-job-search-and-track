"""Provider instruction files (providers/<id>.md) and each user's provider state.

A provider file has a flat front matter block and a fixed set of sections (see
providers/_template.md). Adding a valid file is all it takes to add a provider.
"""
from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

from .db import bump_changes, now_iso
from .errors import JobTrackerError
from .paths import home_dir, repo_root

PROVIDERS_DIR_ENV = "JOBTRACKER_PROVIDERS_DIR"
SKIPPED_FILES = {"readme.md", "_template.md", "contributing.md"}
KINDS = ("jobs", "salary", "both")
ACCESS_METHODS = ("chrome-extension", "playwright", "scrapling", "http", "web-search")
REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "id": str,
    "name": str,
    "kind": str,
    "regions": list,
    "access": str,
    "requires_login": bool,
    "live_walk": bool,
    "dependencies": list,
    "max_results_per_query": int,
    "min_seconds_between_requests": int,
    "last_verified": str,
}
REQUIRED_SECTIONS = (
    "Access method",
    "Search recipe",
    "Fields to extract",
    "Application form questions",
    "Limits and etiquette",
    "Known pitfalls",
)
SALARY_SECTION = "Salary data"
COUNTRIES_SECTION = "Countries"
COUNTRY_CODE = re.compile(r"[A-Z]{2}")
REGIONS_MESSAGE = ("field 'regions' must be [global] or a list of two-letter country codes"
                   " such as [PE]")

# How to install tools that provider files commonly depend on.
INSTALL_HINTS = {
    "scrapling": "jt providers install <provider> (installs scrapling[fetchers] and its"
                 " browser, about 150 MB, and checks it works)",
    "playwright": "jt providers install <provider> (installs playwright and Chromium and"
                  " checks it works)",
    "chrome-extension": "Install Claude in Chrome and connect it to Claude Code",
}


def providers_dir() -> Path:
    override = os.environ.get(PROVIDERS_DIR_ENV)
    return Path(override) if override else repo_root() / "providers"


def private_dir() -> Path:
    """The user's own provider files (and readers), in the private home."""
    return home_dir() / "providers"


def provider_path(provider_id: str) -> Path | None:
    """The file of a listed provider, repository or private."""
    item = next((p for p in list_providers() if p["id"] == provider_id), None)
    return Path(str(item["path"])) if item else None


def _parse_value(raw: str) -> object:
    value = raw.split(" #", 1)[0].strip()
    if value.startswith("[") and value.endswith("]"):
        return [item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip()]
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value.strip("'\"")


def parse_front_matter(text: str) -> dict[str, object]:
    """The flat `key: value` block between the leading '---' lines."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    data: dict[str, object] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if match:
            data[match.group(1)] = _parse_value(match.group(2))
    return data


def _sections(text: str) -> set[str]:
    return {match.group(1).strip().casefold()
            for match in re.finditer(r"^##\s+(.+?)\s*(?:\(.*\))?\s*$", text, re.M)}


def _coverage(regions: object) -> tuple[str, list[str]] | None:
    """('global', []) or ('local', codes) from `regions`; None when the value is not valid."""
    if not isinstance(regions, list) or not regions:
        return None
    if regions == ["global"]:
        return "global", []
    if all(isinstance(code, str) and COUNTRY_CODE.fullmatch(code) for code in regions):
        return "local", [str(code) for code in regions]
    return None


def _countries_table(text: str) -> dict[str, list[str]] | None:
    """Rows of the '## Countries' section keyed by country code (None without the section)."""
    match = re.search(r"^##\s+Countries\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not match:
        return None
    rows: dict[str, list[str]] = {}
    for line in match.group(1).splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.strip().startswith("|") and cells and COUNTRY_CODE.fullmatch(cells[0]):
            rows[cells[0]] = cells
    return rows


def _country_problems(text: str, countries: list[str]) -> list[str]:
    """Each country of a local provider needs a verified row in '## Countries'."""
    table = _countries_table(text)
    if table is None:
        return [f"missing section '## {COUNTRIES_SECTION}' (one row per country in"
                " 'regions')"] if len(countries) > 1 else []
    problems = []
    for code in countries:
        row = table.get(code)
        if row is None:
            problems.append(f"country '{code}' has no row in '## {COUNTRIES_SECTION}'")
            continue
        try:
            date.fromisoformat(row[-1])
        except ValueError:
            problems.append(
                f"country '{code}' needs a 'Last verified' date like 2026-11-15")
    for code in table:
        if code not in countries:
            problems.append(f"country '{code}' is in '## {COUNTRIES_SECTION}' but not in"
                            " 'regions'")
    return problems


def validate_text(text: str, file_name: str) -> list[str]:
    """Every problem in one provider file, as readable messages (empty when valid)."""
    problems: list[str] = []
    meta = parse_front_matter(text)
    if not meta:
        return ["missing front matter (the block between the leading '---' lines)"]
    for field, expected in REQUIRED_FIELDS.items():
        if field not in meta:
            problems.append(f"missing field '{field}'")
        elif not isinstance(meta[field], expected) or (
            expected is int and isinstance(meta[field], bool)
        ):
            problems.append(f"field '{field}' has the wrong type")
    stem = Path(file_name).stem
    if "id" in meta and meta["id"] != stem:
        problems.append(f"field 'id' must match the file name ('{stem}')")
    if "kind" in meta and meta["kind"] not in KINDS:
        problems.append(f"field 'kind' must be one of: {', '.join(KINDS)}")
    if "access" in meta and meta["access"] not in ACCESS_METHODS:
        problems.append(f"field 'access' must be one of: {', '.join(ACCESS_METHODS)}")
    if isinstance(meta.get("last_verified"), str):
        try:
            date.fromisoformat(str(meta["last_verified"]))
        except ValueError:
            problems.append("field 'last_verified' must be a date like 2026-11-15")
    for field in ("max_results_per_query", "min_seconds_between_requests"):
        value = meta.get(field)
        if isinstance(value, int) and not isinstance(value, bool) and value < 0:
            problems.append(f"field '{field}' must not be negative")
    coverage = _coverage(meta.get("regions"))
    if "regions" in meta and isinstance(meta["regions"], list) and coverage is None:
        problems.append(REGIONS_MESSAGE)
    if coverage and coverage[0] == "local":
        problems.extend(_country_problems(text, coverage[1]))
    found = _sections(text)
    required = list(REQUIRED_SECTIONS)
    if meta.get("kind") in ("salary", "both"):
        required.append(SALARY_SECTION)
    for section in required:
        if section.casefold() not in found:
            problems.append(f"missing section '## {section}'")
    return problems


def _read_folder(directory: Path, origin: str) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    if not directory.is_dir():
        return found
    for path in sorted(directory.glob("*.md")):
        name = path.name.lower()
        if name in SKIPPED_FILES or name.endswith(".study.md"):
            continue
        text = path.read_text(encoding="utf-8")
        meta = parse_front_matter(text)
        meta.setdefault("id", path.stem)
        meta.setdefault("name", path.stem)
        meta["file"] = path.name
        meta["path"] = str(path)
        meta["origin"] = origin
        coverage = _coverage(meta.get("regions"))
        meta["coverage"] = coverage[0] if coverage else None
        meta["countries"] = coverage[1] if coverage else None
        problems = validate_text(text, path.name)
        meta["valid"] = not problems
        meta["problems"] = problems
        found.append(meta)
    return found


def list_providers(directory: Path | None = None) -> list[dict[str, object]]:
    """Every provider file with its front matter and whether it is valid: the
    repository's (`origin: repo`), then the user's own (`origin: private`). A private
    file whose id a repository file already uses is listed as invalid. With
    `directory`, only that folder is read."""
    if directory is not None:
        return _read_folder(directory, "repo")
    found = _read_folder(providers_dir(), "repo")
    taken = {str(p["id"]) for p in found}
    for item in _read_folder(private_dir(), "private"):
        if str(item["id"]) in taken:
            item["valid"] = False
            item["problems"] = [*item["problems"],  # type: ignore[misc]
                                f"id already used by providers/{item['id']}.md; rename the "
                                "private file and its id"]
        found.append(item)
    return found


def validate(directory: Path | None = None, file: Path | None = None) -> dict:
    """Validate one file or every provider file."""
    if file is not None:
        if not file.is_file():
            raise JobTrackerError("not_found", f"There is no file at '{file}'")
        problems = validate_text(file.read_text(encoding="utf-8"), file.name)
        results = [{"file": file.name, "valid": not problems, "problems": problems}]
    else:
        results = [
            {"file": p["file"], "valid": p["valid"], "problems": p["problems"]}
            for p in list_providers(directory)
        ]
    return {"valid": all(r["valid"] for r in results), "files": results}


def install_hint(tool: str, provider_file: str) -> str:
    hint = INSTALL_HINTS.get(tool)
    if hint:
        return hint
    return f"see the dependencies section of providers/{provider_file}"


def with_state(conn) -> list[dict[str, object]]:
    """Every provider file with this user's state.

    A provider is off until the user turns it on, so a site added by an update of the
    repository never runs without the user's choice.
    """
    state = {row["provider_id"]: row for row in conn.execute("SELECT * FROM providers_state")}
    switched = {row["entity_id"]: row["created_at"] for row in conn.execute(
        "SELECT entity_id, MAX(created_at) AS created_at FROM events"
        " WHERE entity_type = 'provider' AND kind IN ('enabled', 'disabled')"
        " GROUP BY entity_id")}
    result = []
    for provider in list_providers():
        row = state.get(str(provider["id"]))
        result.append({
            **provider,
            "enabled": bool(row["enabled"]) if row else False,
            "switched_at": switched.get(str(provider["id"])),
            "last_status": row["last_status"] if row else None,
            "last_error": row["last_error"] if row else None,
            "last_run_at": row["last_run_at"] if row else None,
        })
    return result


def set_enabled(conn, provider_id: str, enabled: bool) -> list[dict[str, object]]:
    if provider_id not in {str(p["id"]) for p in list_providers()}:
        raise JobTrackerError("not_found", f"There is no provider '{provider_id}'")
    now = now_iso()
    conn.execute(
        "INSERT INTO providers_state (provider_id, enabled, updated_at) VALUES (?, ?, ?)"
        " ON CONFLICT(provider_id) DO UPDATE SET enabled = excluded.enabled,"
        " updated_at = excluded.updated_at",
        (provider_id, int(enabled), now),
    )
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, created_at)"
        " VALUES ('provider', ?, ?, ?)", (provider_id, "enabled" if enabled else "disabled", now),
    )
    bump_changes(conn)
    return with_state(conn)


def record_result(conn, provider_id: str, status: str, error: str | None, when: str) -> None:
    """Remember how the last use of a provider went (no change-counter bump).

    Never turns a provider on: a missing row is stored as off.
    """
    conn.execute(
        "INSERT INTO providers_state (provider_id, enabled, last_status, last_error,"
        " last_run_at, updated_at) VALUES (?, 0, ?, ?, ?, ?)"
        " ON CONFLICT(provider_id) DO UPDATE SET last_status = excluded.last_status,"
        " last_error = excluded.last_error, last_run_at = excluded.last_run_at,"
        " updated_at = excluded.updated_at",
        (provider_id, status, error, when, when),
    )
