"""Scenarios of the `user-workspace` spec (except the privacy guard)."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from jobtracker.core import paths as paths_module
from jobtracker.core.errors import JobTrackerError
from jobtracker.core.paths import next_version_path, slugify


def _fingerprint(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and not p.name.endswith(("-wal", "-shm"))
    }


def test_default_location_is_user_data_in_the_repo(monkeypatch):
    monkeypatch.delenv(paths_module.HOME_ENV, raising=False)
    assert paths_module.home_dir() == paths_module.repo_root() / "user-data"


def test_overridden_location(home, cli):
    code, out, _ = cli("init")
    assert code == 0
    assert Path(out["home"]) == home.home
    assert home.database.is_file()
    assert not (paths_module.repo_root() / "user-data" / "jobtracker.db").exists()


def test_initialization_creates_the_documented_structure(workspace):
    assert workspace.config.is_file()
    assert workspace.database.is_file()
    for name in ("profile", "applications", "searches", "exports", "backups", "archive"):
        assert (workspace.home / name).is_dir()


def test_initialization_is_repeatable(workspace, cli):
    (workspace.profile / "resume-base.md").write_text("kept", encoding="utf-8")
    before = _fingerprint(workspace.home)
    code, out, _ = cli("init", "--language", "es")
    assert code == 0
    assert out["already_initialized"] is True
    assert out["created"] == []
    assert out["language"] == "en"  # an existing workspace keeps its settings
    assert _fingerprint(workspace.home) == before


def test_init_with_language(home, cli):
    _, out, _ = cli("init", "--language", "es")
    assert out["language"] == "es"


def test_application_folder_naming(workspace, cli):
    code, out, _ = cli("paths", "--job", "J0007", "--company", "Altamar Retail S.A.")
    assert code == 0
    expected = workspace.home / "applications" / "J0007-altamar-retail-s-a"
    assert Path(out["job_folder"]) == expected


def test_invalid_job_id_is_rejected(workspace, cli):
    code, out, _ = cli("paths", "--job", "7", "--company", "X")
    assert code == 1
    assert out["error"]["code"] == "invalid_job_id"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Altamar Retail S.A.", "altamar-retail-s-a"),
        ("Cobre Logística", "cobre-logistica"),
        ("  ¡Ñandú & Cía!  ", "nandu-cia"),
        ("x" * 60, "x" * 40),
        ("///", ""),
    ],
)
def test_slugify(text, expected):
    assert slugify(text) == expected


def test_versioned_documents_are_never_overwritten(tmp_path):
    folder = tmp_path / "J0001-acme"
    folder.mkdir()
    first = next_version_path(folder, "resume-proposed", "docx")
    assert first.name == "resume-proposed-v1.docx"
    first.write_text("one", encoding="utf-8")

    second = next_version_path(folder, "resume-proposed", ".PDF")
    assert second.name == "resume-proposed-v2.pdf"
    assert first.read_text(encoding="utf-8") == "one"

    # A removed middle version is never reused.
    second.write_text("two", encoding="utf-8")
    first.unlink()
    assert next_version_path(folder, "resume-proposed", "docx").name == "resume-proposed-v3.docx"


def test_document_names_cannot_escape_the_folder(tmp_path):
    with pytest.raises(JobTrackerError):
        next_version_path(tmp_path, "../evil", "md")
    with pytest.raises(JobTrackerError):
        next_version_path(tmp_path, "resume", "m/d")


def test_document_path_through_cli(workspace, cli):
    _, out, _ = cli("paths", "--job", "J0001", "--company", "Acme", "--document",
                    "cover-letter", "--ext", "md")
    assert Path(out["document"]).name == "cover-letter-v1.md"


def test_full_reset_requires_confirmation(workspace, cli):
    marker = workspace.profile / "resume-base.md"
    marker.write_text("mine", encoding="utf-8")
    code, out, _ = cli("reset")
    assert code == 1
    assert out["error"]["code"] == "confirmation_required"
    assert marker.read_text(encoding="utf-8") == "mine"
    assert list(workspace.archive.iterdir()) == []


def test_full_reset_archives_and_starts_empty(workspace, cli):
    (workspace.profile / "resume-base.md").write_text("mine", encoding="utf-8")
    cli("rules", "add", "--text", "Never change my resume layout", "--area", "resume")

    code, out, _ = cli("reset", "--confirm", "RESET", "--label", "Fresh Start")
    assert code == 0
    archived = Path(out["archived_to"])
    assert archived.parent == workspace.archive
    assert archived.name.endswith("-fresh-start")
    assert (archived / "profile" / "resume-base.md").read_text(encoding="utf-8") == "mine"
    assert (archived / "jobtracker.db").is_file()

    # Fresh workspace: initialized, no personal files, no user rules.
    assert workspace.database.is_file()
    assert list(workspace.profile.iterdir()) == []
    _, rules_out, _ = cli("rules", "list")
    assert all(rule["origin"] == "system" for rule in rules_out["rules"])


def test_second_reset_on_the_same_day_does_not_overwrite(workspace, cli):
    _, first, _ = cli("reset", "--confirm", "RESET")
    _, second, _ = cli("reset", "--confirm", "RESET")
    assert first["archived_to"] != second["archived_to"]
    assert Path(first["archived_to"]).is_dir()
