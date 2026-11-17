"""The prepare-documents and form-answers skills only use what the CLI really offers."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from jobtracker.cli.main import build_parser
from jobtracker.core import skills
from tests.test_setup import _subcommands

REPO = Path(__file__).resolve().parent.parent
FOLDERS = [REPO / ".claude" / "skills" / name for name in ("prepare-documents", "form-answers")]


def _skill_texts() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8")
            for folder in FOLDERS for path in folder.glob("*.md")}


def test_skill_files_exist():
    for folder in FOLDERS:
        text = (folder / "SKILL.md").read_text(encoding="utf-8")
        assert text.startswith("---\nname: " + folder.name + "\n")


def test_skills_only_use_commands_that_exist():
    found = set()
    for text in _skill_texts().values():
        found |= set(re.findall(
            r"(?:`jt|python scripts/jt\.py|^jt) ([a-z]+(?:[ ][a-z-]+)?(?:[ ][a-z-]+)?)", text,
            flags=re.MULTILINE))
    top_level = _subcommands(build_parser())
    checked = set()
    for command in found:
        choices = top_level
        for word in command.split():
            if choices is None:
                break
            assert word in choices, f"`{command}` is not a jobtracker command"
            checked.add(word)
            choices = _subcommands(choices[word])
    assert {"context", "pending", "applications", "documents", "tailor", "register",
            "cover-letter", "path", "answers", "set", "alternative", "list", "score",
            "rules"} <= checked


def test_referenced_skill_files_exist():
    for text in _skill_texts().values():
        for reference in re.findall(r"`(\.claude/skills/[^`]+\.md)`", text):
            assert (REPO / reference).is_file(), reference
        for reference in re.findall(r"`([a-z-]+-guide\.md)`", text):
            assert any((folder / reference).is_file() for folder in FOLDERS), reference


def test_json_examples_are_valid():
    blocks = 0
    for text in _skill_texts().values():
        for block in re.findall(r"```(?:json)?\n(.*?)```", text, flags=re.DOTALL):
            body = block
            if "<<'JSON'" in block:
                body = block.split("<<'JSON'\n", 1)[1].rsplit("JSON", 1)[0]
            elif not block.lstrip().startswith(("{", "[")):
                continue
            json.loads(body)
            blocks += 1
    assert blocks >= 4


@pytest.mark.parametrize("alias", ["preparar-documentos", "formulario"])
def test_spanish_aliases_install_now_that_the_skills_exist(workspace, cli, skills_target, alias):
    _, out, _ = cli("config", "set", "language", "es")
    assert alias in out["skills"]["installed"]
    assert (skills_target / alias / "SKILL.md").is_file()
    _, listed, _ = cli("skills", "list")
    by_id = {c["id"]: c for c in listed["commands"]}
    command = next(c for c in skills.COMMANDS if c["aliases"].get("es") == alias)
    assert by_id[command["id"]]["available"] is True
    assert by_id[command["id"]]["command"] == f"/{alias}"


def test_alias_argument_names():
    text = (skills.templates_dir("es") / "formulario" / "SKILL.md").read_text(encoding="utf-8")
    assert "`alternativa` means `alternative`" in text
    text = (skills.templates_dir("es") / "preparar-documentos" / "SKILL.md").read_text(
        encoding="utf-8")
    assert "`pendientes` means `pending`" in text and "`todas` means `all`" in text
