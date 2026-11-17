"""Scenarios of the `setup-onboarding` and `skill-localization` specs (CLI side)."""
from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jobtracker.core import skills
from jobtracker.core.setup import STEP_IDS
from jobtracker.web.app import create_app
from tests.helpers import make_docx

REPO = Path(__file__).resolve().parent.parent
PERSONA = json.loads((REPO / "tests" / "fixtures" / "persona.json").read_text(encoding="utf-8"))
SPANISH_ALIASES = ["configurar", "buscar-empleos", "preparar-documentos", "formulario",
                   "analizar-resultados", "nueva-temporada"]


def _git_status() -> str:
    return subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True,
                          text=True).stdout


# ── setup progress ────────────────────────────────────────────────────────

def test_setup_starts_at_the_first_step(workspace, cli):
    _, out, _ = cli("setup", "status")
    assert out["next_step"] == "environment"
    assert out["complete"] is False
    assert [s["step"] for s in out["steps"]] == list(STEP_IDS)


def test_interrupted_setup_resumes_after_the_last_completed_step(workspace, cli):
    _, done, _ = cli("setup", "done", "environment", "language", "workspace")
    assert done["done"] == ["environment", "language", "workspace"]
    assert done["next_step"] == "privacy"
    cli("setup", "done", "privacy", "resume")
    _, out, _ = cli("setup", "status")
    assert out["next_step"] == "questionnaire"
    _, context, _ = cli("context")
    assert context["setup"]["next_step"] == "questionnaire"
    assert context["setup_required"] is True


def test_a_completed_step_can_be_revised_without_losing_data(workspace, cli, tmp_path):
    cli("resume", "import", str(make_docx(tmp_path / "cv.docx")), "--language", "en")
    for step in STEP_IDS:
        cli("setup", "done", step)
    _, out, _ = cli("setup", "redo", "titles")
    assert out["next_step"] == "titles" and out["complete"] is False
    _, resume, _ = cli("resume", "show")
    assert resume["by_language"][0]["version"] == 1


def test_unknown_step_is_rejected(workspace, cli):
    code, out, _ = cli("setup", "done", "coffee")
    assert code == 2 and out["error"]["code"] == "usage"


# ── privacy registration ──────────────────────────────────────────────────

def test_private_terms_are_registered_without_being_echoed(workspace, cli, capsys):
    code, out, err = cli("privacy", "terms", "add", PERSONA["name"], PERSONA["email"],
                         PERSONA["phone"], "ab")
    assert code == 0
    assert out == {"ok": True, "added": 3, "skipped_too_short": 1, "total": 3}
    assert PERSONA["name"] not in json.dumps(out) + err
    _, listed, _ = cli("privacy", "terms", "list")
    assert listed["terms"] == [PERSONA["name"], PERSONA["email"], PERSONA["phone"]]
    stored = workspace.private_terms.read_text(encoding="utf-8")
    assert PERSONA["email"] in stored

    _, again, _ = cli("privacy", "terms", "add", PERSONA["name"].upper())
    assert again["added"] == 0 and again["total"] == 3


def test_private_terms_need_a_workspace(home, cli):
    code, out, _ = cli("privacy", "terms", "add", "Someone Private")
    assert code == 1 and out["error"]["code"] == "not_initialized"


def test_setup_commands_leave_the_repository_untouched(home, cli, tmp_path, monkeypatch):
    before = _git_status()
    cli("init", "--language", "es")
    cli("skills", "sync")
    cli("privacy", "terms", "add", PERSONA["name"], PERSONA["email"])
    cli("resume", "import", str(make_docx(tmp_path / "cv.docx")), "--language", "en")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(
        {"work_modes": ["remote"], "titles": PERSONA["target_titles"]})))
    cli("profile", "set", "-")
    cli("profile", "title", "Analytics Engineer", "included")
    cli("rules", "add", "--text", "No cambiar el diseño del CV", "--area", "resume")
    for step in STEP_IDS:
        cli("setup", "done", step)

    assert _git_status() == before
    assert home.private_terms.is_file()
    _, context, _ = cli("context")
    assert context["setup_required"] is False
    assert context["language"] == "es"


# ── aliases ───────────────────────────────────────────────────────────────

def test_every_command_with_a_spanish_name_has_a_template():
    for command in skills.COMMANDS:
        alias = command["aliases"].get("es")
        if alias:
            template = skills.templates_dir("es") / alias / "SKILL.md"
            text = template.read_text(encoding="utf-8")
            assert f"name: {alias}\n" in text
            assert f".claude/skills/{command['id']}/SKILL.md" in text
    assert sorted(a for c in skills.COMMANDS for a in c["aliases"].values()) == sorted(
        SPANISH_ALIASES)


def test_alias_templates_map_spanish_arguments():
    text = (skills.templates_dir("es") / "buscar-empleos" / "SKILL.md").read_text(
        encoding="utf-8")
    assert "`dias=N` means `days=N`" in text


def test_spanish_user_gets_aliases_of_built_skills(workspace, cli, skills_target):
    _, out, _ = cli("config", "set", "language", "es")
    synced = out["skills"]
    assert "configurar" in synced["installed"]
    assert (skills_target / "configurar" / "SKILL.md").is_file()
    built = {c["id"] for c in skills.COMMANDS if (skills.canonical_dir() / c["id"]).is_dir()}
    for command in skills.COMMANDS:
        alias = command["aliases"].get("es")
        if alias:
            assert (skills_target / alias).is_dir() == (command["id"] in built)


def test_switching_to_english_removes_aliases_and_nothing_else(workspace, cli, skills_target):
    cli("config", "set", "language", "es")
    other = skills_target / "someone-elses-skill"
    other.mkdir(parents=True)
    (other / "SKILL.md").write_text("keep me", encoding="utf-8")

    _, out, _ = cli("config", "set", "language", "en")
    assert "configurar" in out["skills"]["removed"]
    assert not (skills_target / "configurar").exists()
    assert (other / "SKILL.md").read_text(encoding="utf-8") == "keep me"


def test_sync_is_repeatable(workspace, cli):
    cli("config", "set", "language", "es")
    _, first, _ = cli("skills", "sync")
    _, second, _ = cli("skills", "sync")
    assert first == second


@pytest.mark.parametrize("alias", SPANISH_ALIASES)
def test_installed_aliases_are_ignored_by_git(alias):
    result = subprocess.run(["git", "check-ignore", "-q", f".claude/skills/{alias}/SKILL.md"],
                            cwd=REPO)
    assert result.returncode == 0


def test_canonical_skills_are_not_ignored_by_git():
    result = subprocess.run(["git", "check-ignore", "-q", ".claude/skills/setup/SKILL.md"],
                            cwd=REPO)
    assert result.returncode == 1


# ── command display ───────────────────────────────────────────────────────

def _commands(cli) -> dict[str, dict]:
    _, out, _ = cli("skills", "list")
    return {c["id"]: c for c in out["commands"]}


def test_english_panel_shows_canonical_names(workspace, cli):
    commands = _commands(cli)
    assert commands["setup"]["command"] == "/setup"
    assert commands["job-search"]["example"] == "/job-search days=7"
    assert commands["setup"]["available"] is True


def test_spanish_panel_with_aliases_shows_spanish_names(workspace, cli):
    cli("config", "set", "language", "es")
    commands = _commands(cli)
    assert commands["setup"]["command"] == "/configurar"
    assert "idioma" in commands["setup"]["description"]


def test_spanish_panel_without_aliases_shows_canonical_names(workspace, cli, skills_target):
    cli("config", "set", "language", "es")
    for alias in SPANISH_ALIASES:  # e.g. the user removed them
        folder = skills_target / alias
        if folder.exists():
            (folder / "SKILL.md").unlink()
    commands = _commands(cli)
    assert commands["setup"]["command"] == "/setup"
    assert "idioma" in commands["setup"]["description"]  # description stays localized


def test_planned_commands_are_shown_under_the_name_they_will_have(workspace, cli):
    cli("config", "set", "language", "es")
    names = {c["id"]: c["aliases"].get("es", c["id"]) for c in skills.COMMANDS}
    for command in _commands(cli).values():
        if not command["available"]:
            assert command["command"] == f"/{names[command['id']]}"
    cli("config", "set", "language", "en")
    for command in _commands(cli).values():
        assert command["command"] == f"/{command['id']}"


def test_commands_through_the_api_and_context(workspace, cli):
    cli("config", "set", "language", "es")
    body = TestClient(create_app(), base_url="http://127.0.0.1:8000").get("/api/commands").json()
    assert body["language"] == "es"
    assert body["commands"][0]["command"] == "/configurar"
    _, context, _ = cli("context")
    assert context["commands"] == body["commands"]


# ── providers ─────────────────────────────────────────────────────────────

def test_provider_selection(workspace, cli, tmp_path, monkeypatch):
    folder = tmp_path / "providers"
    folder.mkdir()
    (folder / "demo.md").write_text("---\nid: demo\nregions: [PE]\naccess: playwright\n---\n",
                                    encoding="utf-8")
    (folder / "_template.md").write_text("---\nid: example\n---\n", encoding="utf-8")
    monkeypatch.setattr("jobtracker.core.providers.providers_dir", lambda: folder)

    _, out, _ = cli("providers", "list")
    assert [(p["id"], p["enabled"]) for p in out["providers"]] == [("demo", False)]
    _, out, _ = cli("providers", "enable", "demo")
    assert out["providers"][0]["enabled"] is True
    _, out, _ = cli("providers", "disable", "demo")
    assert out["providers"][0]["enabled"] is False
    _, context, _ = cli("context")
    assert context["providers"][0]["enabled"] is False
    code, out, _ = cli("providers", "enable", "nope")
    assert code == 1 and out["error"]["code"] == "not_found"


# ── the skill itself ──────────────────────────────────────────────────────

def _subcommands(parser) -> dict | None:
    import argparse

    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    return None


def test_setup_skill_only_uses_commands_that_exist():
    """Every `jt …` command named in the skill files exists in the real CLI."""
    import re

    from jobtracker.cli.main import build_parser

    folder = REPO / ".claude" / "skills" / "setup"
    found = set()
    for path in folder.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        found |= set(re.findall(
            r"(?:`jt|python scripts/jt\.py) ([a-z]+(?:[ ][a-z-]+)?(?:[ ][a-z-]+)?)", text))
    assert len(found) >= 15

    top_level = _subcommands(build_parser())
    checked = set()
    for command in found:
        choices = top_level
        for word in command.split():
            if choices is None:
                break  # the remaining words are arguments
            assert word in choices, f"`{command}` is not a jobtracker command"
            checked.add(word)
            choices = _subcommands(choices[word])
    assert {"doctor", "init", "context", "resume", "profile", "titles", "privacy", "terms",
            "skills", "sync", "providers", "rules", "edit", "retire", "setup", "done",
            "redo", "panel"} <= checked


def test_readme_cli_examples_run(workspace, cli):
    """Every `python scripts/jt.py …` line in the README is a real command."""
    import re
    import shlex

    text = (REPO / "README.md").read_text(encoding="utf-8")
    examples = set(re.findall(r"python scripts/jt\.py ([^`#\n|]+)", text))
    assert len(examples) >= 6
    for example in sorted(examples):
        arguments = shlex.split(example.strip())
        if arguments == ["--help"]:
            continue
        if arguments[0] == "reset":
            continue  # destructive; covered in test_workspace
        code, out, _ = cli(*arguments)
        assert code == 0, (example, out)
