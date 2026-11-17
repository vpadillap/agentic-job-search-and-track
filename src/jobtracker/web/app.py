"""The local panel: a static frontend plus a small JSON API over the core services.

Only loopback host names are served (DNS-rebinding protection). The panel
never runs the agent; it reads and writes data through the same services as
the CLI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from jobtracker import __version__
from jobtracker.core import board, config, db, providers, skills, tracking
from jobtracker.core.errors import JobTrackerError
from jobtracker.core.paths import get_paths
from jobtracker.core.workspace import is_initialized

STATIC = Path(__file__).parent / "static"
LOOPBACK_NAMES = {"127.0.0.1", "localhost", "::1"}
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; "
        "frame-ancestors 'none'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}
STATUS_BY_CODE = {"not_initialized": 409, "not_found": 404}


def host_name(header: str) -> str:
    """The name part of a Host header: '[::1]:8000' -> '::1', 'localhost:8000' -> 'localhost'."""
    value = header.strip().lower()
    if value.startswith("["):
        return value[1:value.find("]")] if "]" in value else value
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


class PostingIds(BaseModel):
    posting_ids: list[int] = Field(min_length=1, max_length=500)


class TrackRequest(PostingIds):
    applied: bool = False


class DismissRequest(PostingIds):
    reason: Literal["industry", "low_salary", "location", "stack", "other"]
    note: str | None = Field(default=None, max_length=500)


class LanguageRequest(BaseModel):
    language: Literal["en", "es"]


class ProviderRequest(BaseModel):
    enabled: bool


def create_app() -> FastAPI:
    app = FastAPI(title="Job Tracker", version=__version__, docs_url="/api/docs", redoc_url=None)

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if host_name(request.headers.get("host", "")) not in LOOPBACK_NAMES:
            return JSONResponse(
                {"ok": False, "error": {"code": "forbidden_host",
                                        "message": "The panel only answers on this machine."}},
                status_code=403,
            )
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    @app.exception_handler(JobTrackerError)
    async def handle_error(request, error: JobTrackerError):
        status = STATUS_BY_CODE.get(error.code, 400)
        return JSONResponse({"ok": False, "error": error.to_dict()}, status_code=status)

    # ── read ──────────────────────────────────────────────────────────────

    @app.get("/api/health")
    def health() -> dict:
        paths = get_paths()
        return {
            "ok": True,
            "version": __version__,
            "initialized": is_initialized(paths),
            "schema_version": db.stored_schema_version(paths.database),
        }

    @app.get("/api/changes")
    def changes() -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True, **db.change_state(conn)}

    @app.get("/api/commands")
    def commands() -> dict:
        language = str(config.load(get_paths().config)["language"])
        return {"ok": True, "language": language, "commands": skills.command_list(language)}

    @app.get("/api/state")
    def state() -> dict:
        """What the header and tabs need, and whether setup is still required."""
        paths = get_paths()
        if not is_initialized(paths):
            return {"ok": True, "initialized": False, "setup_required": True, "language": None,
                    "commands": skills.command_list("en"), "header": None, "changes": None}
        language = str(config.load(paths.config)["language"])
        with db.session(paths) as conn:
            header = board.header(conn)
            return {
                "ok": True, "initialized": True,
                "setup_required": header["profile"] is None,
                "language": language,
                "commands": skills.command_list(language),
                "header": header,
                "changes": db.change_state(conn),
            }

    @app.get("/api/search")
    def search_board(run: int | None = None) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True, **board.search_board(conn, run)}

    @app.get("/api/providers")
    def provider_list() -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True, "providers": providers.with_state(conn)}

    # ── write ─────────────────────────────────────────────────────────────

    @app.post("/api/actions/track")
    def track(body: TrackRequest) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True,
                    "applications": tracking.track(conn, body.posting_ids, body.applied)}

    @app.post("/api/actions/untrack")
    def untrack(body: PostingIds) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True, "posting_ids": tracking.untrack(conn, body.posting_ids)}

    @app.post("/api/actions/dismiss")
    def dismiss(body: DismissRequest) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True,
                    "posting_ids": tracking.dismiss(conn, body.posting_ids, body.reason,
                                                    body.note)}

    @app.post("/api/actions/undismiss")
    def undismiss(body: PostingIds) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True, "posting_ids": tracking.undismiss(conn, body.posting_ids)}

    @app.post("/api/providers/{provider_id}")
    def set_provider(provider_id: str, body: ProviderRequest) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True,
                    "providers": providers.set_enabled(conn, provider_id, body.enabled)}

    @app.post("/api/settings/language")
    def set_language(body: LanguageRequest) -> dict:
        paths = get_paths()
        if not is_initialized(paths):
            raise JobTrackerError("not_initialized", "The workspace is not initialized yet.")
        settings = config.set_value(paths.config, "language", body.language)
        with db.session(paths) as conn:
            db.bump_changes(conn)
        skills.sync(str(settings["language"]))
        return {"ok": True, "language": settings["language"],
                "commands": skills.command_list(str(settings["language"]))}

    # ── frontend ──────────────────────────────────────────────────────────

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
