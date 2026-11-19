"""Plain requests reach the user skills: descriptions, the plain-request section, eval sets."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from jobtracker.core import skills

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "tests" / "skill-evals"
USER_SKILLS = [command["id"] for command in skills.COMMANDS]
SECTION = "## When the request is in plain words"


def _front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    block = text.split("---\n")[1]
    fields = {}
    for line in block.splitlines():
        key, _, value = line.partition(": ")
        fields[key] = json.loads(value) if value.startswith('"') else value
    return fields


def test_eval_sets_cover_exactly_the_user_skills():
    assert sorted(path.stem for path in EVALS.glob("*.json")) == sorted(USER_SKILLS)


@pytest.mark.parametrize("skill", USER_SKILLS)
def test_skill_has_the_plain_request_section(skill):
    text = (REPO / ".claude" / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    assert SECTION in text


@pytest.mark.parametrize("skill", USER_SKILLS)
def test_description_says_when_to_use_it_in_both_languages(skill):
    description = _front_matter(REPO / ".claude" / "skills" / skill / "SKILL.md")["description"]
    assert "Use when the user " in description
    assert "also in Spanish:" in description
    assert len(description) <= 1024


@pytest.mark.parametrize("skill", USER_SKILLS)
def test_eval_set_has_positives_and_near_misses_in_both_languages(skill):
    items = json.loads((EVALS / f"{skill}.json").read_text(encoding="utf-8"))
    for item in items:
        assert set(item) == {"query", "should_trigger", "language"}
        assert item["query"].strip()
    for should_trigger in (True, False):
        for language in ("en", "es"):
            assert any(item["should_trigger"] is should_trigger and item["language"] == language
                       for item in items), (should_trigger, language)


def test_eval_requests_are_fictional():
    # Application ids are the fixture style (J0007), never real contact data.
    for path in EVALS.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[\w.]+@[\w.]+|https?://|\+?\d[\d ()-]{7,}", text), path.name


def test_alias_descriptions_say_when_to_use_them():
    for command in skills.COMMANDS:
        alias = command["aliases"].get("es")
        if not alias:
            continue
        description = _front_matter(skills.templates_dir("es") / alias / "SKILL.md")["description"]
        assert "Úsalo cuando" in description
        assert f"(Alias en español de /{command['id']}.)" in description


def test_agents_md_routes_every_user_skill():
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    table = text.split("## User mode: plain requests", 1)[1].split("\n## ", 1)[0]
    for skill in USER_SKILLS:
        assert f"`/{skill}`" in table
