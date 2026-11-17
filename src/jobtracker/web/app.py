"""Panel application. For now: health and the change counter the panel polls."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from jobtracker import __version__
from jobtracker.core import config, db, skills
from jobtracker.core.errors import JobTrackerError
from jobtracker.core.paths import get_paths
from jobtracker.core.workspace import is_initialized


def create_app() -> FastAPI:
    app = FastAPI(title="Job Tracker", version=__version__, docs_url="/api/docs", redoc_url=None)

    @app.exception_handler(JobTrackerError)
    async def handle_error(request, error: JobTrackerError):
        status = 409 if error.code == "not_initialized" else 400
        return JSONResponse({"ok": False, "error": error.to_dict()}, status_code=status)

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

    return app
