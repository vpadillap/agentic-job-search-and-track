"""Creating, inspecting, and resetting the private home."""
from __future__ import annotations

import shutil
from datetime import datetime

from . import config, db, rules
from .errors import JobTrackerError
from .paths import SUBDIRECTORIES, Paths, slugify

RESET_CONFIRMATION = "RESET"


def is_initialized(paths: Paths) -> bool:
    return paths.database.is_file() and paths.config.is_file()


def initialize(paths: Paths, language: str | None = None) -> dict:
    """Create the documented layout. Safe to repeat: existing files are left alone."""
    already = is_initialized(paths)
    created: list[str] = []

    if not paths.home.exists():
        paths.home.mkdir(parents=True)
        created.append(str(paths.home))
    for name in SUBDIRECTORIES:
        folder = paths.home / name
        if not folder.exists():
            folder.mkdir()
            created.append(str(folder))

    if not paths.config.exists():
        settings = dict(config.DEFAULTS)
        if language is not None:
            settings["language"] = config.validate("language", language)
        config.save(paths.config, settings)
        created.append(str(paths.config))
    elif language is not None and not already:
        config.set_value(paths.config, "language", language)

    database_existed = paths.database.exists()
    with db.session(paths, create=True) as conn:
        rules.seed_system_rules(conn)
        if conn.execute("SELECT COUNT(*) FROM seasons").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO seasons (number, started_at, is_active) VALUES (1, ?, 1)",
                (db.now_iso(),),
            )
    if not database_existed:
        created.append(str(paths.database))

    return {
        "already_initialized": already,
        "created": created,
        "home": str(paths.home),
        "language": config.load(paths.config)["language"],
        "schema_version": db.current_schema_version(),
    }


def reset(paths: Paths, confirmation: str | None, label: str = "reset") -> dict:
    """Full reset: move everything into a dated archive folder, then start empty.

    Nothing is deleted. Moving the archive folder's contents back restores it.
    """
    if confirmation != RESET_CONFIRMATION:
        raise JobTrackerError(
            "confirmation_required",
            f"A full reset archives all data and starts empty. Confirm with "
            f"--confirm {RESET_CONFIRMATION}. Nothing was changed.",
        )
    if not paths.home.is_dir():
        raise JobTrackerError("not_initialized", "There is no workspace to reset.")

    entries = [entry for entry in paths.home.iterdir() if entry.name != "archive"]
    name = f"{datetime.now():%Y%m%d}-{slugify(label) or 'reset'}"
    target = paths.archive / name
    suffix = 2
    while target.exists():
        target = paths.archive / f"{name}-{suffix}"
        suffix += 1
    target.mkdir(parents=True)
    for entry in entries:
        shutil.move(str(entry), str(target / entry.name))

    result = initialize(paths)
    return {"archived_to": str(target), "archived_entries": len(entries), **result}
