"""The local panel: a static frontend plus a small JSON API over the core services.

Only loopback host names are served (DNS-rebinding protection). The panel
never runs the agent; it reads and writes data through the same services as
the CLI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from jobtracker import __version__
from jobtracker.core import (
    answers,
    applications,
    board,
    config,
    db,
    documents,
    providers,
    search,
    skills,
    tracking,
)
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


class WorkModeRequest(BaseModel):
    work_mode: Literal["remote", "hybrid", "onsite"] | None
    detail: str | None = Field(default=None, max_length=search.WORK_MODE_DETAIL_MAX)


class ProviderRequest(BaseModel):
    enabled: bool


class StatusChange(BaseModel):
    job_ids: list[str] = Field(min_length=1, max_length=500)
    status: str | int
    stage: Literal["to_apply", "applied", "interview", "offer", "closed_positive",
                   "closed_negative"] | None = None


class TagChange(BaseModel):
    add: list[str] = Field(default_factory=list, max_length=50)
    remove: list[str] = Field(default_factory=list, max_length=50)


class NewStatus(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    stage: Literal["to_apply", "applied", "interview", "offer", "closed_positive",
                   "closed_negative"]


class AnswerEdit(BaseModel):
    text: str = Field(max_length=5000)


class AnswerPick(BaseModel):
    answer_id: int


class StatusEdit(BaseModel):
    name: str | None = Field(default=None, max_length=40)
    retired: bool | None = None


def _language() -> str:
    return str(config.load(get_paths().config)["language"])


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

    @app.post("/api/postings/{posting_id}/work-mode")
    def set_work_mode(posting_id: int, body: WorkModeRequest) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True, "posting": search.set_work_mode(
                conn, posting_id, body.work_mode, body.detail, source="user")}

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

    # ── applications ──────────────────────────────────────────────────────

    @app.get("/api/applications")
    def application_board() -> dict:
        language = _language()
        with db.session(get_paths()) as conn:
            items = applications.list_applications(conn, language)
            return {"ok": True, "applications": items, "funnel": applications.funnel(items),
                    "attention": applications.attention(items),
                    "statuses": applications.list_statuses(conn, language),
                    "thresholds": applications.thresholds(conn)}

    @app.get("/api/applications/{job_id}")
    def application_detail(job_id: str) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True, "application": applications.detail(conn, job_id, _language())}

    @app.post("/api/applications/status")
    def change_status(body: StatusChange) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True, "job_ids": applications.set_status(
                conn, body.job_ids, body.status, stage=body.stage)}

    @app.post("/api/applications/{job_id}/details")
    def change_details(job_id: str, body: dict) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True,
                    "application": applications.update_details(conn, job_id, body)}

    @app.post("/api/applications/{job_id}/tags")
    def change_tags(job_id: str, body: TagChange) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True, "tags": applications.set_tags(conn, job_id, body.add,
                                                               body.remove)}

    @app.post("/api/statuses")
    def new_status(body: NewStatus) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True, "status": applications.create_status(conn, body.name,
                                                                      body.stage)}

    @app.post("/api/statuses/{status_id}")
    def edit_status(status_id: int, body: StatusEdit) -> dict:
        with db.session(get_paths()) as conn:
            result = None
            if body.name is not None:
                result = applications.rename_status(conn, status_id, body.name)
            if body.retired is not None:
                result = applications.retire_status(conn, status_id, body.retired)
            if result is None:
                raise JobTrackerError("invalid_status", "nothing to change")
            return {"ok": True, "status": result}

    @app.post("/api/applications/{job_id}/resume-sent")
    def upload_resume(job_id: str, file: Annotated[UploadFile, File()]) -> dict:
        data = file.file.read(applications.MAX_UPLOAD_BYTES + 1)
        paths = get_paths()
        with db.session(paths) as conn:
            return {"ok": True, "document": applications.upload_sent_resume(
                conn, paths, job_id, file.filename or "", data)}

    @app.get("/api/applications/{job_id}/documents/{document_id}")
    def download(job_id: str, document_id: int) -> FileResponse:
        paths = get_paths()
        with db.session(paths) as conn:
            path = applications.document_path(conn, paths, job_id, document_id)
        return FileResponse(path, media_type="application/octet-stream", filename=path.name,
                            content_disposition_type="attachment")

    @app.get("/api/applications/{job_id}/documents/{document_id}/text")
    def document_text(job_id: str, document_id: int) -> dict:
        paths = get_paths()
        with db.session(paths) as conn:
            path = applications.document_path(conn, paths, job_id, document_id)
        if path.suffix.lower() not in (".md", ".txt"):
            raise JobTrackerError("not_text", "Only text documents can be copied")
        return {"ok": True, "text": path.read_text(encoding="utf-8")}

    @app.get("/api/applications/{job_id}/documents/{document_id}/diff")
    def document_diff(job_id: str, document_id: int) -> dict:
        paths = get_paths()
        with db.session(paths) as conn:
            return {"ok": True, **documents.diff(conn, paths, job_id, document_id)}

    @app.post("/api/applications/{job_id}/answers/{position}")
    def edit_answer(job_id: str, position: int, body: AnswerEdit) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True, "question": answers.edit(conn, job_id, position, body.text)}

    @app.post("/api/applications/{job_id}/answers-pick")
    def pick_answer(job_id: str, body: AnswerPick) -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True, "question": answers.pick(conn, job_id, body.answer_id)}

    @app.get("/api/pending")
    def pending() -> dict:
        with db.session(get_paths()) as conn:
            return {"ok": True, "pending": board.pending(conn)}

    # ── frontend ──────────────────────────────────────────────────────────

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
