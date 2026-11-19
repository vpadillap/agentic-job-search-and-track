"""Readers: the fixed, judgment-free part of a provider file as code.

A reader requests a site exactly as its provider file says and writes drafts
(import records with the fields that need no judgment). The agent reads the
drafts and adds its reading. Readers are optional: a provider can still be
added with its file alone. A provider that is also a salary source may have a
salary reader, which returns an evidence draft for the agent to check.
"""
from __future__ import annotations

import importlib.util
import re
from importlib import import_module
from types import ModuleType

from .. import providers
from ..errors import JobTrackerError
from ..paths import Paths

READERS = {"linkedin": "jobtracker.core.readers.linkedin",
           "bumeran": "jobtracker.core.readers.bumeran",
           "indeed": "jobtracker.core.readers.indeed",
           "glassdoor": "jobtracker.core.readers.glassdoor",
           "greenhouse": "jobtracker.core.readers.greenhouse",
           "getonbrd": "jobtracker.core.readers.getonbrd",
           "agentic-search": "jobtracker.core.readers.agentic_search"}
SALARY_READERS = {"glassdoor": "jobtracker.core.readers.glassdoor"}
# Options a reader takes besides the title and location: CLI flag -> keyword argument.
OPTIONS = {"glassdoor": {"search_url": "search_url_given"},
           "greenhouse": {"found": "found", "place_words": "place_words"},
           "agentic-search": {"found": "found"}}


def _private_reader(provider_id: str, paths: Paths) -> ModuleType | None:
    """A private provider's own reader: `<home>/providers/<id>.py`, next to its file.
    It is the user's own code, run on the user's request."""
    item = next((p for p in providers.list_providers() if p["id"] == provider_id), None)
    path = paths.home / "providers" / f"{provider_id}.py"
    if item is None or item.get("origin") != "private" or not path.is_file():
        return None
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", provider_id):
        raise JobTrackerError("invalid_provider", f"'{provider_id}' is not a valid provider id")
    spec = importlib.util.spec_from_file_location(
        f"jobtracker_private_reader_{provider_id.replace('-', '_')}", path)
    if spec is None or spec.loader is None:
        raise JobTrackerError("no_reader", f"cannot load the private reader {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "read", None)):
        raise JobTrackerError("no_reader", f"{path} has no read(paths, run_id, title, "
                              "location=None) function")
    return module


def read(provider_id: str, paths: Paths, run_id: int, title: str,
         location: str | None = None, **options: str | None) -> dict:
    """Run a provider's reader: a built-in one, else the user's private reader."""
    given = {name: value for name, value in options.items() if value}
    module_name = READERS.get(provider_id)
    if module_name is None:
        private = _private_reader(provider_id, paths)
        if private is None:
            raise JobTrackerError(
                "no_reader", f"'{provider_id}' has no reader; follow its provider file")
        if given:
            raise JobTrackerError("invalid_option", f"'{provider_id}' (a private reader) takes "
                                  "only --title and --location")
        return private.read(paths, run_id, title, location)
    allowed = OPTIONS.get(provider_id, {})
    for name in given:
        if name not in allowed:
            raise JobTrackerError(
                "invalid_option", f"'{provider_id}' does not take --{name.replace('_', '-')}")
    return import_module(module_name).read(
        paths, run_id, title, location, **{allowed[name]: value for name, value in given.items()})


def salary(provider_id: str, paths: Paths, title: str | list[str],
           search_url: str | None = None) -> dict:
    module = SALARY_READERS.get(provider_id)
    if module is None:
        raise JobTrackerError(
            "no_reader", f"'{provider_id}' has no salary reader; follow "
            f"providers/{provider_id}.md")
    return import_module(module).salary(paths, title, search_url_given=search_url)
