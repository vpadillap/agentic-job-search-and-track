"""Readers: the fixed, judgment-free part of a provider file as code.

A reader requests a site exactly as its provider file says and writes drafts
(import records with the fields that need no judgment). The agent reads the
drafts and adds its reading. Readers are optional: a provider can still be
added with its file alone.
"""
from __future__ import annotations

from importlib import import_module

from ..errors import JobTrackerError
from ..paths import Paths

READERS = {"linkedin": "jobtracker.core.readers.linkedin",
           "bumeran": "jobtracker.core.readers.bumeran",
           "indeed": "jobtracker.core.readers.indeed"}


def read(provider_id: str, paths: Paths, run_id: int, title: str,
         location: str | None = None) -> dict:
    module = READERS.get(provider_id)
    if module is None:
        raise JobTrackerError(
            "no_reader", f"'{provider_id}' has no reader; follow providers/{provider_id}.md")
    return import_module(module).read(paths, run_id, title, location)
