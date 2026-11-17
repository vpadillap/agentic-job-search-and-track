from __future__ import annotations

import json

import pytest

from jobtracker.cli.main import main
from jobtracker.core.paths import HOME_ENV, Paths


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
