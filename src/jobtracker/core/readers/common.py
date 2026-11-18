"""What every reader shares: the run's context, per-run state and pacing, one call at
a time, postings already stored, the drafts file, and recording a stop."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .. import db, providers, search
from .. import profile as profile_service
from ..errors import JobTrackerError
from ..paths import Paths

MIN_SECONDS = 5          # a provider file may ask for more, never for less
STALE_LOCK_SECONDS = 30 * 60   # longer than any call: requests with pacing and timeouts


class Stop(Exception):
    """Stop the provider for the rest of the run: `blocked` or `error`."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason, self.detail = reason, detail


@dataclass
class Context:
    provider: str
    run_id: int
    folder: Path
    since: str           # oldest publication date inside the run's window
    days: int            # the run's window
    max_results: int     # per title, from the provider file
    min_seconds: int     # between requests or browser actions
    country: str | None  # the profile's ISO country
    known: set[str]      # this site's job ids stored by any run


def context(conn, paths: Paths, run_id: int, provider: str, label: str) -> Context:
    run = conn.execute("SELECT * FROM search_runs WHERE id = ?", (run_id,)).fetchone()
    if run is None:
        raise JobTrackerError("not_found", f"There is no search run {run_id}")
    if run["status"] != "running":
        raise JobTrackerError("run_finished", f"Run {run_id} is already finished")
    if run["is_demo"] or not run["capture_folder"]:
        raise JobTrackerError("invalid_run", f"Run {run_id} has no capture folder")
    item = next((p for p in json.loads(run["providers"]) if p["id"] == provider), None)
    if item is None:
        raise JobTrackerError("not_found", f"'{provider}' is not a job provider of run {run_id}")
    if item["status"] == "failed":
        raise JobTrackerError(
            "provider_stopped", f"{label} is stopped for run {run_id}: "
            f"{item.get('detail') or item.get('reason')}. Do not try it again in this run.")
    if item["status"] not in ("pending", "ok"):
        raise JobTrackerError(
            "provider_not_searched", f"{label} is {item['status']} in run {run_id}")
    meta = next((p for p in providers.list_providers() if p["id"] == provider), None)
    if meta is None or not meta.get("valid"):
        raise JobTrackerError("invalid_file", f"providers/{provider}.md is missing or invalid")
    started = datetime.fromisoformat(run["started_at"].replace("Z", "+00:00")).astimezone().date()
    days = int(run["posting_age_days"])
    active = profile_service.get_active(conn) or {}
    known = {row["external_id"] for row in conn.execute(
        "SELECT external_id FROM postings WHERE provider = ?", (provider,))}
    return Context(
        provider=provider, run_id=run_id, folder=paths.home / run["capture_folder"],
        since=(started - timedelta(days=days)).isoformat(), days=days,
        max_results=int(meta["max_results_per_query"]),
        min_seconds=max(MIN_SECONDS, int(meta["min_seconds_between_requests"])),
        country=active.get("country"), known=known,
    )


def load_state(ctx: Context) -> dict:
    path = ctx.folder / f"{ctx.provider}-state.json"
    state = {"last_request_at": 0.0, "requests": 0, "job_ids": [], "drafts": []}
    if path.is_file():
        state.update(json.loads(path.read_text(encoding="utf-8")))
    return state


def save_state(ctx: Context, state: dict) -> None:
    (ctx.folder / f"{ctx.provider}-state.json").write_text(json.dumps(state, indent=1),
                                                            encoding="utf-8")


def lock(ctx: Context, label: str, now: float) -> Path:
    """One reader call at a time per run: parallel calls would share the pacing state
    and reach the site together. A lock older than any call can last is stale."""
    path = ctx.folder / f"{ctx.provider}.lock"
    for _ in range(2):
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                started = float(path.read_text(encoding="utf-8") or 0)
            except (OSError, ValueError):
                started = 0.0
            if now - started < STALE_LOCK_SECONDS:
                raise JobTrackerError(
                    "reader_busy", f"Another {label} read is running for this run. Read the "
                    "titles one at a time, never in parallel; wait for it to finish.",
                    lock=str(path)) from None
            path.unlink(missing_ok=True)
            continue
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            file.write(str(now))
        return path
    raise JobTrackerError("reader_busy", f"Another {label} read is running for this run.")


def seen_records(conn, provider: str, cards: list[dict]) -> list[dict]:
    """Postings stored by an earlier run, as import records, with this run's date."""
    records = []
    for card in cards:
        row = conn.execute("SELECT * FROM postings WHERE provider = ? AND external_id = ?",
                           (provider, card["external_id"])).fetchone()
        records.append({
            "provider": provider, "external_id": row["external_id"], "url": row["url"],
            "title": row["title"], "company": row["company"], "location": row["location"],
            "country": row["country"], "posted_at": card.get("posted_at") or row["posted_at"],
            "description": row["description"], "seniority": row["seniority"],
            "contract_type": row["contract_type"], "work_mode": row["work_mode"],
            "work_mode_detail": row["work_mode_detail"], "language": row["language"],
            "flags": json.loads(row["flags"]) if row["flags"] else [],
            "published_salary": json.loads(row["published_salary"])
            if row["published_salary"] else None,
        })
    return records


def finish(paths: Paths, ctx: Context, state: dict, summary: dict, drafts: list[dict],
           seen: list[dict]) -> dict:
    """Write the drafts, record postings already stored as seen, and record a stop."""
    if drafts:
        name = f"{ctx.provider}-drafts-{len(state['drafts']) + 1}.json"
        (ctx.folder / name).write_text(json.dumps(drafts, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
        state["drafts"].append(name)
        summary["drafts_path"] = str(ctx.folder / name)
    save_state(ctx, state)
    summary["new"] = len(drafts)
    summary["already_seen"] = len(seen)
    with db.session(paths) as conn:
        if seen:
            search.import_postings(conn, ctx.run_id, seen_records(conn, ctx.provider, seen))
        if summary["stopped"]:
            search.record_provider(conn, ctx.run_id, ctx.provider, "failed",
                                   reason=summary["stopped"]["reason"],
                                   detail=summary["stopped"]["detail"])
    return summary
