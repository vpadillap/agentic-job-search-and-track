"""project-documentation: the README stays in step with the skills and the job sites."""
from __future__ import annotations

import re
from pathlib import Path

from jobtracker.core import providers, skills

REPO = Path(__file__).resolve().parents[1]
README = (REPO / "README.md").read_text(encoding="utf-8")


def _command_cells() -> set[str]:
    """Every `/command` written in the first cells of the README's command tables."""
    found = set()
    for line in README.splitlines():
        if line.startswith("| `/"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            for cell in cells[:2]:
                found |= set(re.findall(r"`/([a-z-]+)", cell))
    return found


def test_every_command_in_the_readme_exists():
    known = {c["id"] for c in skills.COMMANDS}
    known |= {alias for c in skills.COMMANDS for alias in c["aliases"].values()}
    named = _command_cells()
    assert named, "the README has no command table"
    missing = sorted(named - known)
    assert not missing, f"the README names commands that do not exist: {missing}"
    for command in skills.COMMANDS:                     # and every command is documented
        assert f"`/{command['id']}" in README, command["id"]
        for alias in command["aliases"].values():
            assert f"`/{alias}" in README, alias


def test_every_command_has_a_skill():
    for command in skills.COMMANDS:
        assert (skills.canonical_dir() / command["id"] / "SKILL.md").is_file(), command["id"]


def test_every_job_site_is_in_the_readme():
    listed = providers.list_providers(REPO / "providers")
    assert listed
    for provider in listed:
        name = str(provider["name"])
        short = name.split(" (")[0]
        assert f"| {short} |" in README or f"| {name} |" in README, (
            f"providers/{provider['file']} ({name}) is not in the README's job-site table")


def test_contributing_guides_exist_and_are_linked():
    assert (REPO / "CONTRIBUTING.md").is_file()
    assert (REPO / "providers" / "CONTRIBUTING.md").is_file()
    assert "CONTRIBUTING.md" in README
    assert "providers/CONTRIBUTING.md" in README
