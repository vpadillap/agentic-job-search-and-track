"""Readers: the fixed, judgment-free part of a provider file as code.

A reader requests a site exactly as its provider file says and writes drafts
(import records with the fields that need no judgment). The agent reads the
drafts and adds its reading. Readers are optional: a provider can still be
added with its file alone. A provider that is also a salary source may have a
salary reader, which returns an evidence draft for the agent to check.
"""
from __future__ import annotations

from importlib import import_module

from ..errors import JobTrackerError
from ..paths import Paths

READERS = {"linkedin": "jobtracker.core.readers.linkedin",
           "bumeran": "jobtracker.core.readers.bumeran",
           "indeed": "jobtracker.core.readers.indeed",
           "glassdoor": "jobtracker.core.readers.glassdoor",
           "greenhouse": "jobtracker.core.readers.greenhouse"}
SALARY_READERS = {"glassdoor": "jobtracker.core.readers.glassdoor"}
# Options a reader takes besides the title and location: CLI flag -> keyword argument.
OPTIONS = {"glassdoor": {"search_url": "search_url_given"},
           "greenhouse": {"found": "found", "place_words": "place_words"}}


def read(provider_id: str, paths: Paths, run_id: int, title: str,
         location: str | None = None, **options: str | None) -> dict:
    module = READERS.get(provider_id)
    if module is None:
        raise JobTrackerError(
            "no_reader", f"'{provider_id}' has no reader; follow providers/{provider_id}.md")
    allowed = OPTIONS.get(provider_id, {})
    given = {name: value for name, value in options.items() if value}
    for name in given:
        if name not in allowed:
            raise JobTrackerError(
                "invalid_option", f"'{provider_id}' does not take --{name.replace('_', '-')}")
    return import_module(module).read(paths, run_id, title, location,
                                      **{allowed[name]: value for name, value in given.items()})


def salary(provider_id: str, paths: Paths, title: str, search_url: str | None = None) -> dict:
    module = SALARY_READERS.get(provider_id)
    if module is None:
        raise JobTrackerError(
            "no_reader", f"'{provider_id}' has no salary reader; follow "
            f"providers/{provider_id}.md")
    return import_module(module).salary(paths, title, search_url_given=search_url)
