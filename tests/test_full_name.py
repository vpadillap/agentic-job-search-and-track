"""Scenarios of the `setup-onboarding` spec: recording the user's full name."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from jobtracker.core import config

REPO = Path(__file__).resolve().parent.parent
PERSONA = json.loads((REPO / "tests" / "fixtures" / "persona.json").read_text(encoding="utf-8"))


def test_recording_the_full_name_registers_it_without_echoing_it(workspace, cli):
    code, out, err = cli("privacy", "name", "set", "  " + PERSONA["name"] + " ")
    assert code == 0
    assert out == {"ok": True, "full_name_recorded": True, "private_term_added": True}
    assert PERSONA["name"] not in json.dumps(out) + err
    _, terms, _ = cli("privacy", "terms", "list")
    assert PERSONA["name"] in terms["terms"]
    _, shown, _ = cli("privacy", "name", "show")
    assert shown["full_name"] == PERSONA["name"]


def test_changing_the_name_keeps_the_earlier_term(workspace, cli):
    cli("privacy", "name", "set", PERSONA["name"])
    cli("privacy", "name", "set", "Marisol Quispe")
    _, shown, _ = cli("privacy", "name", "show")
    assert shown["full_name"] == "Marisol Quispe"
    _, terms, _ = cli("privacy", "terms", "list")
    assert {PERSONA["name"], "Marisol Quispe"} <= set(terms["terms"])


@pytest.mark.parametrize("name", ['Marisol "Mari" O\'Quispe', "Back\slash Ñandú"])
def test_names_with_quotes_round_trip(workspace, cli, name):
    cli("privacy", "name", "set", name)
    assert config.load_full_name(workspace.config) == name
    with workspace.config.open("rb") as handle:
        assert tomllib.load(handle)["full_name"] == name


def test_other_settings_keep_the_name(workspace, cli):
    cli("privacy", "name", "set", PERSONA["name"])
    code, _, _ = cli("config", "set", "language", "es")
    assert code == 0
    assert config.load_full_name(workspace.config) == PERSONA["name"]
    assert config.load(workspace.config)["language"] == "es"


@pytest.mark.parametrize("name", ["", "   ", "x" * 101, "Mari\nsol"])
def test_invalid_names_are_refused(workspace, cli, name):
    code, out, _ = cli("privacy", "name", "set", name)
    assert code == 1 and out["error"]["code"] == "invalid_config"
    assert config.load_full_name(workspace.config) is None


def test_the_name_is_not_a_config_set_key(workspace, cli):
    code, out, _ = cli("config", "set", "full_name", PERSONA["name"])
    assert code != 0 and out["ok"] is False
    assert config.load_full_name(workspace.config) is None


def test_recording_needs_a_workspace(home, cli):
    code, out, _ = cli("privacy", "name", "set", PERSONA["name"])
    assert code == 1 and out["error"]["code"] == "not_initialized"


def test_the_privacy_guard_refuses_a_commit_with_the_recorded_name(workspace, cli, tmp_path):
    cli("privacy", "name", "set", PERSONA["name"])
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    shutil.copy(REPO / "scripts" / "check_private.py", root / "scripts" / "check_private.py")
    shutil.copy(REPO / ".gitignore", root / ".gitignore")
    for command in (["init", "-q"], ["config", "user.email", "t@example.test"],
                    ["config", "user.name", "Test"]):
        subprocess.run(["git", *command], cwd=root, check=True)
    shutil.copytree(workspace.home, root / "user-data")
    (root / "notes.md").write_text(f"Written by {PERSONA['name']}\n", encoding="utf-8")
    subprocess.run(["git", "add", "notes.md"], cwd=root, check=True)
    env = {k: v for k, v in os.environ.items() if k != "JOBTRACKER_HOME"}
    result = subprocess.run([sys.executable, str(root / "scripts" / "check_private.py")],
                            cwd=root, capture_output=True, text=True, env=env)
    assert result.returncode == 1
    assert "notes.md" in result.stderr
