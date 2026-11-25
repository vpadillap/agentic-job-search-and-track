"""Private terms: the user's identifying strings, checked by the privacy guard."""
from __future__ import annotations

from . import config
from .errors import JobTrackerError
from .paths import Paths

MIN_TERM_LENGTH = 4
HEADER = (
    "# Private terms, one per line. scripts/check_private.py refuses to commit any file\n"
    "# that contains one of them. Managed with: jobtracker privacy terms add <term>\n"
)


def _read(paths: Paths) -> list[str]:
    if not paths.private_terms.is_file():
        return []
    lines = paths.private_terms.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def list_terms(paths: Paths) -> list[str]:
    """The registered terms. They are the user's own data, shown only on request."""
    return _read(paths)


def add_terms(paths: Paths, terms: list[str]) -> dict:
    """Register terms. The terms themselves are never echoed back."""
    if not paths.home.is_dir():
        raise JobTrackerError("not_initialized", "The workspace is not initialized. Run /setup.")
    existing = _read(paths)
    known = {term.casefold() for term in existing}
    added, too_short = 0, 0
    for raw in terms:
        term = " ".join(raw.split())
        if len(term) < MIN_TERM_LENGTH:
            too_short += 1
            continue
        if term.casefold() in known:
            continue
        existing.append(term)
        known.add(term.casefold())
        added += 1
    paths.private_terms.write_text(HEADER + "\n".join(existing) + "\n", encoding="utf-8")
    return {"added": added, "skipped_too_short": too_short, "total": len(existing)}


def set_full_name(paths: Paths, name: object) -> dict:
    """Record the user's full name and register it as a private term, in one step.

    The name is never echoed back. An earlier name stays a registered term.
    """
    if not paths.home.is_dir():
        raise JobTrackerError("not_initialized", "The workspace is not initialized. Run /setup.")
    clean = config.clean_full_name(name)
    terms = add_terms(paths, [clean])
    config.save_full_name(paths.config, clean)
    return {"full_name_recorded": True, "private_term_added": terms["added"] == 1}


def full_name(paths: Paths) -> str | None:
    """The recorded full name, or None."""
    return config.load_full_name(paths.config)
