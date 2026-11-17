"""The bundle an agent loads before doing anything."""
from __future__ import annotations

from pathlib import Path

from . import board, config, db, profile, providers, resume, rules, scoring, search, setup, skills
from .paths import Paths
from .workspace import is_initialized

PANEL_INDEX = Path(__file__).resolve().parent.parent / "web" / "static" / "index.html"


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
            "base_resume": None,
            "rules": [],
            "pending": [],
            "providers": [],
            "commands": skills.command_list("en"),
            "setup": None,
        }

    settings = config.load(paths.config)
    language = str(settings["language"])
    with db.session(paths) as conn:
        season = conn.execute("SELECT * FROM seasons WHERE is_active = 1").fetchone()
        active_profile = profile.get_active(conn)
        setup_status = setup.status(conn)
        return {
            "initialized": True,
            "setup_required": active_profile is None or not setup_status["complete"],
            "home": str(paths.home),
            "language": language,
            "season": {
                "number": season["number"], "label": season["label"],
                "started_at": season["started_at"],
            } if season else None,
            "profile": active_profile,
            "base_resume": resume.current(conn, paths),
            "rescore_since": resume.rescore_since(conn),
            "rules": rules.list_rules(conn, "active", language),
            "pending": board.pending(conn),
            "providers": providers.with_state(conn),
            "score_weights": scoring.active_weights(conn),
            "latest_run": (
                search.summary(conn, run_id)
                if (run_id := search.latest_run_id(conn)) is not None else None
            ),
            "commands": skills.command_list(language),
            "setup": setup_status,
            "panel": {
                "url": f"http://{settings['host']}:{settings['port']}",
                "interface_ready": PANEL_INDEX.is_file(),
            },
            "changes": db.change_state(conn),
        }
