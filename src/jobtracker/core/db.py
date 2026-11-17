"""SQLite access: connection settings, forward-only migrations, change counter."""
from __future__ import annotations

import re
import sqlite3
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .errors import JobTrackerError
from .paths import Paths

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
BUSY_TIMEOUT_MS = 5000


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def available_migrations() -> list[tuple[int, Path]]:
    found = []
    for path in MIGRATIONS_DIR.glob("*.sql"):
        match = re.match(r"^(\d{4})_", path.name)
        if match:
            found.append((int(match.group(1)), path))
    return sorted(found)


def current_schema_version() -> int:
    migrations = available_migrations()
    return migrations[-1][0] if migrations else 0


def _open(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    return conn


def stored_schema_version(path: Path) -> int | None:
    """Schema version of the database file, or None when there is no database."""
    if not path.is_file():
        return None
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute("PRAGMA user_version").fetchone()[0]


def _backup(conn: sqlite3.Connection, paths: Paths, version: int) -> Path:
    paths.backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = paths.backups / f"jobtracker-v{version:04d}-{stamp}.db"
    with closing(sqlite3.connect(target)) as copy:
        conn.backup(copy)
    return target


def migrate(conn: sqlite3.Connection, paths: Paths) -> list[int]:
    """Bring the database to the current schema; returns the versions applied."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    target = current_schema_version()
    if version > target:
        raise JobTrackerError(
            "schema_too_new",
            f"The database is at schema version {version} but this code supports up to "
            f"{target}. Update the project (git pull) and try again.",
        )
    pending = [(number, path) for number, path in available_migrations() if number > version]
    if not pending:
        return []
    if version > 0:
        _backup(conn, paths, version)
    applied = []
    for number, path in pending:
        script = path.read_text(encoding="utf-8")
        try:
            conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {number};\nCOMMIT;")
        except sqlite3.Error:
            conn.execute("ROLLBACK") if conn.in_transaction else None
            raise
        applied.append(number)
    return applied


def connect(paths: Paths, *, create: bool = False) -> sqlite3.Connection:
    """Open the database, migrated to the current schema.

    Raises `not_initialized` when the workspace has no database, unless
    `create` is set (used only by workspace initialization).
    """
    if not paths.database.is_file() and not create:
        raise JobTrackerError(
            "not_initialized",
            "The workspace is not initialized. Run /setup (or `jobtracker init`).",
        )
    conn = _open(paths.database)
    try:
        migrate(conn, paths)
    except Exception:
        conn.close()
        raise
    return conn


@contextmanager
def session(paths: Paths, *, create: bool = False):
    """A connection that commits on success and rolls back on any error."""
    conn = connect(paths, create=create)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def bump_changes(conn: sqlite3.Connection) -> None:
    conn.execute(
        "UPDATE change_log SET counter = counter + 1, updated_at = ? WHERE id = 1", (now_iso(),)
    )


def change_state(conn: sqlite3.Connection) -> dict:
    row = conn.execute("SELECT counter, updated_at FROM change_log WHERE id = 1").fetchone()
    return {"counter": row["counter"], "updated_at": row["updated_at"]}
