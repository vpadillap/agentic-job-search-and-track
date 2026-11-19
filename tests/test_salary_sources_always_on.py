"""salary-sources-always-on: salary sources are never switched; the agent is told which
ones serve each posting's country."""
from __future__ import annotations

import json
from pathlib import Path

from jobtracker.core import installer, providers


def _country(cli, workspace, code):
    path = workspace.home / "c.json"
    path.write_text(json.dumps({"country": code}), encoding="utf-8")
    cli("profile", "set", str(path))


def test_sources_serving_a_country():
    peru = {s["id"] for s in providers.salary_sources("PE")}
    assert {"glassdoor", "indeed", "computrabajo", "payscale", "talent"} <= peru
    usa = {s["id"] for s in providers.salary_sources("US")}
    assert "computrabajo" not in usa and {"payscale", "talent", "indeed"} <= usa
    assert all(s["reader"] for s in providers.salary_sources("PE"))


def test_a_salary_only_source_cannot_be_switched(workspace, cli):
    code, out, _ = cli("providers", "disable", "payscale")
    assert code == 1 and out["error"]["code"] == "salary_source"
    assert "always used" in out["error"]["message"]
    code, _, _ = cli("providers", "enable", "computrabajo")      # a job site: its search
    assert code == 0


def test_lookup_lists_the_sources_for_the_posting(searchable, cli, tmp_path, monkeypatch):
    from tests.test_search import captures

    path = tmp_path / "c.json"
    path.write_text(json.dumps(captures()[:1]), encoding="utf-8")
    _, run, _ = cli("run", "start")
    _, imported, _ = cli("postings", "import", str(run["run_id"]), str(path))
    posting = imported["postings"][0]["posting_id"]
    # The real provider files (the fixture searched with fictional ones), none turned on.
    monkeypatch.setattr("jobtracker.core.providers.providers_dir",
                        lambda: Path(__file__).resolve().parent.parent / "providers")
    _, found, _ = cli("salary", "lookup", str(posting))
    ids = {s["id"] for s in found["sources"]}
    assert {"glassdoor", "indeed", "computrabajo", "payscale", "talent"} <= ids  # nothing on
    assert all({"ready", "checked", "reader"} <= set(s) for s in found["sources"])


def test_install_includes_the_salary_sources_of_the_country(workspace, cli):
    _country(cli, workspace, "PE")
    commands = []
    report = installer.install(workspace, enabled=True,
                               runner=lambda c: commands.append(c) or (0, "ok"))
    covered = {item["provider"] for item in report["providers"]}
    assert {"payscale", "talent", "computrabajo"} <= covered      # none of them turned on


def test_doctor_checks_the_salary_sources(workspace, cli, monkeypatch):
    from jobtracker.core import doctor

    _country(cli, workspace, "MX")
    monkeypatch.setattr(doctor, "_tool_available", lambda name: name != "scrapling")
    _, out, _ = cli("doctor")
    ids = {c["id"] for c in out["checks"]}
    assert {"provider:payscale", "provider:talent", "provider:computrabajo"} <= ids
