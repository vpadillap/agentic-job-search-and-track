"""Location and naming of everything in the private home.

The contract is documented in docs/workspace-layout.md. Nothing else in the
code base builds private paths by hand.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .errors import JobTrackerError

HOME_ENV = "JOBTRACKER_HOME"
DEFAULT_HOME_NAME = "user-data"
SUBDIRECTORIES = ("profile", "applications", "searches", "exports", "backups", "archive")
JOB_ID_PATTERN = re.compile(r"^J\d{4,}$")
SLUG_MAX_LENGTH = 40


def repo_root() -> Path:
    """The clone's root: next to the source tree, or the working directory."""
    candidate = Path(__file__).resolve().parents[3]
    if (candidate / "pyproject.toml").is_file():
        return candidate
    return Path.cwd()


def home_dir() -> Path:
    override = os.environ.get(HOME_ENV)
    if override:
        return Path(override).expanduser().resolve()
    return repo_root() / DEFAULT_HOME_NAME


@dataclass(frozen=True)
class Paths:
    home: Path

    @property
    def config(self) -> Path:
        return self.home / "config.toml"

    @property
    def database(self) -> Path:
        return self.home / "jobtracker.db"

    @property
    def private_terms(self) -> Path:
        return self.home / ".private-terms"

    @property
    def profile(self) -> Path:
        return self.home / "profile"

    @property
    def applications(self) -> Path:
        return self.home / "applications"

    @property
    def searches(self) -> Path:
        return self.home / "searches"

    @property
    def exports(self) -> Path:
        return self.home / "exports"

    @property
    def backups(self) -> Path:
        return self.home / "backups"

    @property
    def archive(self) -> Path:
        return self.home / "archive"

    def job_folder(self, job_id: str, company: str) -> Path:
        if not JOB_ID_PATTERN.match(job_id):
            raise JobTrackerError("invalid_job_id", f"'{job_id}' is not a job id like J0007")
        slug = slugify(company)
        name = f"{job_id}-{slug}" if slug else job_id
        return self.applications / name

    def search_folder(self, started: datetime) -> Path:
        return self.searches / started.strftime("%Y%m%d-%H%M")

    def as_dict(self) -> dict[str, str]:
        return {
            "home": str(self.home),
            "config": str(self.config),
            "database": str(self.database),
            "private_terms": str(self.private_terms),
            "profile": str(self.profile),
            "applications": str(self.applications),
            "searches": str(self.searches),
            "exports": str(self.exports),
            "backups": str(self.backups),
            "archive": str(self.archive),
        }


def get_paths() -> Paths:
    return Paths(home_dir())


def slugify(text: str, max_length: int = SLUG_MAX_LENGTH) -> str:
    """Lowercase ASCII with hyphens: 'Altamar Retail S.A.' -> 'altamar-retail-s-a'."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:max_length].rstrip("-")


def next_version_path(folder: Path, stem: str, extension: str) -> Path:
    """Path for the next `-v<N>` version of a document; never an existing file.

    Versions are never reused: the next number follows the highest one present,
    whatever its extension.
    """
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", stem):
        raise JobTrackerError("invalid_document_name", f"'{stem}' is not a valid document name")
    extension = extension.lower().lstrip(".")
    if not re.fullmatch(r"[a-z0-9]{1,8}", extension):
        raise JobTrackerError("invalid_extension", f"'{extension}' is not a valid extension")
    pattern = re.compile(rf"^{re.escape(stem)}-v(\d+)\.[^.]+$")
    highest = 0
    if folder.is_dir():
        for entry in folder.iterdir():
            match = pattern.match(entry.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return folder / f"{stem}-v{highest + 1}.{extension}"
