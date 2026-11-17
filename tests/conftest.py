from __future__ import annotations

import json
from pathlib import Path

import pytest

from jobtracker.cli.main import main
from jobtracker.core.paths import HOME_ENV, Paths


@pytest.fixture(autouse=True)
def skills_target(tmp_path, monkeypatch):
    """Alias installation goes to a temporary folder, never into the real repo."""
    target = tmp_path / "installed-skills"
    monkeypatch.setenv("JOBTRACKER_SKILLS_DIR", str(target))
    return target


@pytest.fixture
def home(tmp_path, monkeypatch) -> Paths:
    """An empty private home in a temporary directory."""
    root = tmp_path / "home"
    monkeypatch.setenv(HOME_ENV, str(root))
    return Paths(root.resolve())


@pytest.fixture
def cli(capsys):
    """Run a CLI command; returns (exit code, parsed JSON output, stderr)."""

    def run(*args: str):
        code = main(list(args))
        captured = capsys.readouterr()
        return code, json.loads(captured.out), captured.err

    return run


@pytest.fixture
def workspace(home, cli) -> Paths:
    """An initialized private home."""
    code, _, _ = cli("init")
    assert code == 0
    return home


@pytest.fixture
def providers_dir(tmp_path, monkeypatch):
    """Fictional provider files in a temporary folder (the repo ships none)."""
    from tests.helpers import provider_text

    folder = tmp_path / "providers"
    folder.mkdir()
    for provider_id in ("alpha", "beta"):
        (folder / f"{provider_id}.md").write_text(provider_text(provider_id), encoding="utf-8")
    (folder / "gamma.md").write_text(provider_text("gamma", live_walk="true"), encoding="utf-8")
    monkeypatch.setenv("JOBTRACKER_PROVIDERS_DIR", str(folder))
    return folder


@pytest.fixture
def searchable(workspace, cli, providers_dir) -> Paths:
    """A workspace with the fictional persona's profile and three providers."""
    persona = json.loads(
        (Path(__file__).parent / "fixtures" / "persona.json").read_text(encoding="utf-8"))
    needs = dict(persona["job_needs"])
    needs["titles"] = persona["target_titles"]
    needs["seniority"] = "Senior"
    path = workspace.home / "profile-input.json"
    path.write_text(json.dumps(needs), encoding="utf-8")
    code, out, _ = cli("profile", "set", str(path))
    assert code == 0, out
    path.unlink()
    for provider_id in ("alpha", "beta", "gamma"):  # job sites start switched off
        code, out, _ = cli("providers", "enable", provider_id)
        assert code == 0, out
    return workspace
