"""Read-only environment diagnostics. Must run with the standard library only."""
from __future__ import annotations

import importlib.util
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing

from . import db, providers
from .paths import Paths, cli_name, repo_root
from .workspace import is_initialized

MIN_PYTHON = (3, 11)
REQUIRED_PACKAGES = {  # import name -> distribution name
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "pydantic": "pydantic",
    "multipart": "python-multipart",
    "pypdf": "pypdf",
    "docx": "python-docx",
}
INSTALL_HINT = "Run `uv sync --extra dev`, or `pip install -e .` inside a virtual environment."


def _check(check_id: str, status: str, detail: str, fix: str | None = None) -> dict:
    result = {"id": check_id, "status": status, "detail": detail}
    if fix:
        result["fix"] = fix
    return result


def _where(provider: dict) -> str:
    """How to name a provider's file: `providers/<file>`, or its path when private."""
    if provider.get("origin") == "private":
        return str(provider.get("path") or provider["file"])
    return f"providers/{provider['file']}"


def _tool_available(name: str) -> bool:
    module = name.replace("-", "_")
    try:
        if importlib.util.find_spec(module) is not None:
            return True
    except (ImportError, ValueError):
        pass
    return shutil.which(name) is not None


def _enabled_provider_ids(paths: Paths) -> set[str]:
    """Providers the user turned on. A provider never chosen is off, so it is not
    checked; without a database nothing is on yet."""
    if not paths.database.is_file():
        return set()
    try:
        with closing(sqlite3.connect(paths.database)) as conn:
            rows = conn.execute("SELECT provider_id FROM providers_state WHERE enabled = 1")
            return {row[0] for row in rows}
    except sqlite3.Error:
        return set()


def run(paths: Paths) -> dict:
    checks: list[dict] = []

    version = sys.version_info
    version_text = f"{version.major}.{version.minor}.{version.micro}"
    if (version.major, version.minor) >= MIN_PYTHON:
        checks.append(_check("python", "pass", f"Python {version_text}"))
    else:
        checks.append(_check(
            "python", "fail", f"Python {version_text} is too old",
            f"Install Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer.",
        ))

    for module, distribution in REQUIRED_PACKAGES.items():
        if importlib.util.find_spec(module) is not None:
            checks.append(_check(f"package:{distribution}", "pass", "installed"))
        else:
            checks.append(_check(f"package:{distribution}", "fail", "not installed", INSTALL_HINT))

    try:
        hooks = subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            cwd=repo_root(), capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        hooks = ""
    if hooks == ".githooks":
        checks.append(_check("privacy_guard", "pass", "pre-commit privacy guard enabled"))
    else:
        checks.append(_check(
            "privacy_guard", "warn", "pre-commit privacy guard is not enabled",
            "Run `git config core.hooksPath .githooks`.",
        ))

    if is_initialized(paths):
        checks.append(_check("workspace", "pass", f"initialized at {paths.home}"))
    else:
        checks.append(_check(
            "workspace", "fail", f"not initialized (expected at {paths.home})",
            f"Run /setup in Claude Code (or `{cli_name()} init`).",
        ))

    stored = db.stored_schema_version(paths.database)
    target = db.current_schema_version()
    if stored is None:
        checks.append(_check("schema", "fail", "no database yet", "Run /setup."))
    elif stored == target:
        checks.append(_check("schema", "pass", f"schema version {stored}"))
    elif stored < target:
        checks.append(_check(
            "schema", "warn", f"schema version {stored}, current is {target}",
            "It is upgraded automatically (with a backup) by the next command that uses it.",
        ))
    else:
        checks.append(_check(
            "schema", "fail", f"schema version {stored} is newer than this code ({target})",
            "Update the project (git pull).",
        ))

    enabled = _enabled_provider_ids(paths)
    for provider in providers.list_providers():
        provider_id = str(provider["id"])
        if provider_id not in enabled:
            continue
        if not provider.get("valid", True):
            checks.append(_check(
                f"provider:{provider_id}", "warn",
                f"invalid provider file: {'; '.join(map(str, provider['problems']))}",  # type: ignore[call-overload]
                f"Fix {_where(provider)} (see providers/_template.md). Searches skip "
                f"it until then.",
            ))
            continue
        dependencies = provider.get("dependencies") or []
        missing = [str(d) for d in dependencies if not _tool_available(str(d))]  # type: ignore[union-attr]
        if missing:
            how = "; ".join(
                f"{tool}: {providers.install_hint(tool, str(provider['file']))}" for tool in missing
            )
            checks.append(_check(
                f"provider:{provider_id}", "fail",
                f"{provider.get('name', provider_id)} needs {', '.join(missing)}, which is not "
                f"installed",
                f"Install it ({how}), or disable the provider.",
            ))
        else:
            checks.append(_check(f"provider:{provider_id}", "pass", "requirements available"))

    return {
        "healthy": all(check["status"] != "fail" for check in checks),
        "python": version_text,
        "home": str(paths.home),
        "initialized": is_initialized(paths),
        "schema_version": stored,
        "checks": checks,
    }
