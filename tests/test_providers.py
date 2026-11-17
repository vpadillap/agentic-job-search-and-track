"""provider-recipes: validation, listing, per-user state, dependency checks."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from jobtracker.core import doctor
from tests.helpers import provider_text

TEMPLATE = Path(__file__).resolve().parents[1] / "providers" / "_template.md"


def test_the_template_is_a_valid_provider_file(tmp_path, cli):
    copy = tmp_path / "example.md"
    shutil.copyfile(TEMPLATE, copy)
    code, out, _ = cli("providers", "validate", str(copy))
    assert code == 0
    assert out["valid"] is True, out


def test_missing_field_and_section_are_reported(tmp_path, cli):
    text = provider_text("delta").replace("live_walk: false\n", "").replace(
        "## Known pitfalls", "## Something else")
    path = tmp_path / "delta.md"
    path.write_text(text, encoding="utf-8")
    _, out, _ = cli("providers", "validate", str(path))
    problems = out["files"][0]["problems"]
    assert out["valid"] is False
    assert "missing field 'live_walk'" in problems
    assert "missing section '## Known pitfalls'" in problems


def test_salary_providers_need_the_salary_section(tmp_path, cli):
    text = provider_text("pay", kind="salary").replace("## Salary data", "## Notes")
    path = tmp_path / "pay.md"
    path.write_text(text, encoding="utf-8")
    _, out, _ = cli("providers", "validate", str(path))
    assert "missing section '## Salary data'" in out["files"][0]["problems"]


def test_id_must_match_the_file_name(tmp_path, cli):
    path = tmp_path / "other.md"
    path.write_text(provider_text("delta"), encoding="utf-8")
    _, out, _ = cli("providers", "validate", str(path))
    assert any("match the file name" in p for p in out["files"][0]["problems"])


def test_a_new_valid_file_appears_in_the_list(workspace, cli, providers_dir):
    (providers_dir / "delta.md").write_text(provider_text("delta"), encoding="utf-8")
    _, out, _ = cli("providers", "list")
    listed = {p["id"]: p for p in out["providers"]}
    assert listed["delta"]["valid"] is True and listed["delta"]["enabled"] is True


def test_invalid_files_are_listed_but_skipped_by_searches(searchable, cli, providers_dir):
    (providers_dir / "broken.md").write_text("---\nid: broken\n---\n", encoding="utf-8")
    _, out, _ = cli("run", "start")
    broken = next(p for p in out["providers"] if p["id"] == "broken")
    assert broken["status"] == "skipped" and broken["reason"] == "invalid_file"
    assert "broken" not in out["to_search"]


def test_disabling_a_provider_means_the_next_search_skips_it(searchable, cli):
    code, _, _ = cli("providers", "disable", "alpha")
    assert code == 0
    _, run, _ = cli("run", "start")
    assert "alpha" not in run["to_search"]


def test_missing_tool_names_provider_tool_and_install(workspace, cli, providers_dir,
                                                       monkeypatch):
    (providers_dir / "alpha.md").write_text(
        provider_text("alpha", dependencies="[playwright-surely-missing]"), encoding="utf-8")
    (providers_dir / "beta.md").write_text(
        provider_text("beta", dependencies="[scrapling]"), encoding="utf-8")
    monkeypatch.setattr(doctor, "_tool_available", lambda name: False)
    monkeypatch.setattr(doctor.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, ".githooks\n", ""))
    _, out, _ = cli("doctor")
    checks = {c["id"]: c for c in out["checks"]}
    alpha, beta = checks["provider:alpha"], checks["provider:beta"]
    assert alpha["status"] == "fail" and "Alpha" in alpha["detail"]
    assert "playwright-surely-missing" in alpha["detail"]
    assert "providers/alpha.md" in alpha["fix"]
    assert "pip install scrapling" in beta["fix"]


def test_disabled_providers_are_not_checked(workspace, cli, providers_dir, monkeypatch):
    (providers_dir / "alpha.md").write_text(
        provider_text("alpha", dependencies="[surely-missing]"), encoding="utf-8")
    cli("providers", "disable", "alpha")
    _, out, _ = cli("doctor")
    assert "provider:alpha" not in {c["id"] for c in out["checks"]}
