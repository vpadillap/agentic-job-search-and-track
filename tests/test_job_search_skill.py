"""The /job-search skill: its commands exist, and its Spanish alias installs."""
from __future__ import annotations

import re
from pathlib import Path

from jobtracker.cli.main import build_parser
from jobtracker.core import skills
from tests.test_setup import _subcommands

SKILL = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "job-search"


def test_skill_files_exist():
    assert {p.name for p in SKILL.glob("*.md")} == {
        "SKILL.md", "scoring-guide.md", "salary-guide.md"}


def test_skill_only_uses_commands_that_exist():
    found = set()
    for path in SKILL.glob("*.md"):
        found |= set(re.findall(r"`jt ([a-z]+(?: [a-z-]+)?(?: [a-z-]+)?)",
                                path.read_text(encoding="utf-8")))
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
    assert {"context", "run", "start", "provider", "finish", "postings", "import", "list",
            "filter", "flag", "score", "set", "salary", "lookup", "evidence", "add",
            "none"} <= checked


def test_skill_states_the_read_only_rule():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "Never apply" in text and "providers/<id>.md" in text


def test_spanish_alias_installs_now_that_the_skill_exists(workspace, cli, skills_target):
    _, out, _ = cli("config", "set", "language", "es")
    assert "buscar-empleos" in out["skills"]["installed"]
    assert (skills_target / "buscar-empleos" / "SKILL.md").is_file()
    listed = {c["id"]: c for c in skills.command_list("es")}
    assert listed["job-search"]["available"] is True
    assert listed["job-search"]["example"] == "/buscar-empleos dias=7"
