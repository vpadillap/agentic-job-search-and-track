"""The bundle an agent loads before doing anything."""
from __future__ import annotations

import json

from . import config, db, providers, rules
from .paths import Paths
from .workspace import is_initialized


def build(paths: Paths) -> dict:
    if not is_initialized(paths):
        return {
            "initialized": False,
            "setup_required": True,
            "message": "Setup is required. Run /setup.",
            "home": str(paths.home),
            "language": None,
            "season": None,
            "profile": None,
            "rules": [],
            "pending": [],
            "providers": [],
        }

    settings = config.load(paths.config)
    with db.session(paths) as conn:
        season = conn.execute("SELECT * FROM seasons WHERE is_active = 1").fetchone()
        profile = conn.execute("SELECT * FROM profile_versions WHERE is_active = 1").fetchone()
        active_rules = rules.list_rules(conn, "active")
        state = {row["provider_id"]: row for row in conn.execute("SELECT * FROM providers_state")}
        changes = db.change_state(conn)

    provider_list = []
    for provider in providers.list_providers():
        row = state.get(str(provider["id"]))
        provider_list.append({
            **provider,
            "enabled": bool(row["enabled"]) if row else True,
            "last_status": row["last_status"] if row else None,
        })

    return {
        "initialized": True,
        "setup_required": profile is None,
        "home": str(paths.home),
        "language": settings["language"],
        "season": {
            "number": season["number"], "label": season["label"],
            "started_at": season["started_at"],
        } if season else None,
        "profile": {
            "version": profile["version"], "created_at": profile["created_at"],
            **json.loads(profile["data"]),
        } if profile else None,
        "rules": active_rules,
        "pending": [],
        "providers": provider_list,
        "changes": changes,
    }
