"""The agent installs what enabled providers need (`jt providers install`). A fake runner
records the commands; nothing is installed."""
from __future__ import annotations

from pathlib import Path

import pytest

from jobtracker.core import doctor, installer
from jobtracker.core.errors import JobTrackerError
from tests.helpers import provider_text

REPO = Path(__file__).resolve().parents[1]


class FakeRunner:
    def __init__(self, fail_on: str | None = None) -> None:
        self.commands: list[list[str]] = []
        self.fail_on = fail_on

    def __call__(self, command: list[str]) -> tuple[int, str]:
        self.commands.append(command)
        if self.fail_on and self.fail_on in " ".join(command):
            return 1, "network unreachable"
        return 0, "ok"


@pytest.fixture
def sites(workspace, cli, providers_dir, monkeypatch):
    (providers_dir / "stealthy.md").write_text(
        provider_text("stealthy", dependencies="[scrapling]"), encoding="utf-8")
    (providers_dir / "odd.md").write_text(
        provider_text("odd", dependencies="[some-tool]"), encoding="utf-8")
    installed: set[str] = set()
    monkeypatch.setattr(doctor, "_tool_available", lambda name: name in installed)
    return installed


def test_installs_a_missing_tool_and_checks_it(sites, workspace, cli):
    runner = FakeRunner()
    report = installer.install(workspace, "stealthy", runner=runner)
    assert report["ok"] is True and report["installed"] == ["scrapling"]
    assert "150 MB" in report["sizes"]["scrapling"]
    joined = [" ".join(c[1:]) for c in runner.commands]
    assert joined[0] == "-m pip install scrapling[fetchers]"
    assert joined[1] == "-m patchright install chromium"
    assert "StealthySession" in joined[2]                       # the check that it works


def test_enabled_installs_each_tool_once(sites, workspace, cli, providers_dir):
    (providers_dir / "stealthy2.md").write_text(
        provider_text("stealthy2", dependencies="[scrapling]"), encoding="utf-8")
    cli("providers", "enable", "stealthy")
    cli("providers", "enable", "stealthy2")
    runner = FakeRunner()
    report = installer.install(workspace, enabled=True, runner=runner)
    assert [p["provider"] for p in report["providers"]] == ["stealthy", "stealthy2"]
    assert len(runner.commands) == 3 and report["ok"] is True


def test_an_installed_tool_is_left_alone(sites, workspace):
    sites.add("scrapling")
    runner = FakeRunner()
    report = installer.install(workspace, "stealthy", runner=runner)
    assert runner.commands == [] and report["providers"][0]["already"] == ["scrapling"]


def test_a_failed_install_is_reported(sites, workspace):
    report = installer.install(workspace, "stealthy", runner=FakeRunner(fail_on="patchright"))
    assert report["ok"] is False and report["installed"] == []
    failure = report["providers"][0]["failed"][0]
    assert failure["tool"] == "scrapling" and "network unreachable" in failure["detail"]


def test_an_unknown_tool_is_not_installed(sites, workspace):
    runner = FakeRunner()
    report = installer.install(workspace, "odd", runner=runner)
    assert runner.commands == [] and report["ok"] is False
    assert report["providers"][0]["unknown"][0]["tool"] == "some-tool"


def test_usage_errors(sites, workspace):
    with pytest.raises(JobTrackerError) as error:
        installer.install(workspace, "nope")
    assert error.value.code == "not_found"
    with pytest.raises(JobTrackerError) as error:
        installer.install(workspace)
    assert error.value.code == "usage"


def test_skills_install_instead_of_skipping():
    search = (REPO / ".claude" / "skills" / "job-search" / "SKILL.md").read_text(
        encoding="utf-8")
    assert "jt providers install --enabled" in search
    assert "The user never installs anything by hand" in search
    setup = (REPO / ".claude" / "skills" / "setup" / "SKILL.md").read_text(encoding="utf-8")
    assert "jt providers install <id>" in setup
