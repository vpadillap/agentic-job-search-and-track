"""One-time offers for existing users, declared by the change that needs them.

An offer is presented only while it is unanswered and applies to the user's data;
it is applied only when the user accepts it, and never presented again once answered.
To declare one, add an `Offer` to `REGISTRY`.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

from .db import now_iso
from .errors import JobTrackerError
from .paths import Paths


@dataclass(frozen=True)
class Offer:
    id: str
    text: dict[str, str]  # language -> one or two sentences for the user
    applies: Callable[[sqlite3.Connection, Paths], bool]
    apply: Callable[[sqlite3.Connection, Paths], dict]


REGISTRY: list[Offer] = []


def _answered(conn: sqlite3.Connection) -> dict[str, str]:
    return {row[0]: row[1] for row in conn.execute("SELECT id, answer FROM offers")}


def pending(conn: sqlite3.Connection, paths: Paths, language: str | None = None) -> list[dict]:
    answered = _answered(conn)
    found = []
    for offer in REGISTRY:
        if offer.id in answered or not offer.applies(conn, paths):
            continue
        found.append({"id": offer.id,
                      "text": offer.text.get(language or "en") or offer.text.get("en", "")})
    return found


def _find(conn: sqlite3.Connection, offer_id: str) -> Offer:
    offer = next((o for o in REGISTRY if o.id == offer_id), None)
    if offer is None:
        raise JobTrackerError("not_found", f"There is no offer '{offer_id}'")
    answer = _answered(conn).get(offer_id)
    if answer:
        raise JobTrackerError("already_answered", f"The offer '{offer_id}' was already {answer}")
    return offer


def accept(conn: sqlite3.Connection, paths: Paths, offer_id: str) -> dict:
    offer = _find(conn, offer_id)
    result = offer.apply(conn, paths)
    conn.execute("INSERT INTO offers (id, answer, answered_at, result) VALUES (?, ?, ?, ?)",
                 (offer_id, "accepted", now_iso(), json.dumps(result, ensure_ascii=False)))
    return {"id": offer_id, "answer": "accepted", "result": result}


def decline(conn: sqlite3.Connection, paths: Paths, offer_id: str) -> dict:
    _find(conn, offer_id)
    conn.execute("INSERT INTO offers (id, answer, answered_at) VALUES (?, ?, ?)",
                 (offer_id, "declined", now_iso()))
    return {"id": offer_id, "answer": "declined"}
