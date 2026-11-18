"""provider-recipes: validation, listing, per-user state, dependency checks."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from jobtracker.core import db, doctor
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
    assert listed["delta"]["valid"] is True
    assert listed["delta"]["enabled"] is False  # arrives switched off: the user decides


def test_invalid_files_are_listed_but_skipped_by_searches(searchable, cli, providers_dir):
    (providers_dir / "broken.md").write_text("---\nid: broken\n---\n", encoding="utf-8")
    assert cli("providers", "enable", "broken")[0] == 0
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
    cli("providers", "enable", "alpha")
    cli("providers", "enable", "beta")
    _, out, _ = cli("doctor")
    checks = {c["id"]: c for c in out["checks"]}
    alpha, beta = checks["provider:alpha"], checks["provider:beta"]
    assert alpha["status"] == "fail" and "Alpha" in alpha["detail"]
    assert "playwright-surely-missing" in alpha["detail"]
    assert "providers/alpha.md" in alpha["fix"]
    assert 'pip install "scrapling[fetchers]", then: scrapling install' in beta["fix"]


def test_disabled_providers_are_not_checked(workspace, cli, providers_dir, monkeypatch):
    (providers_dir / "alpha.md").write_text(
        provider_text("alpha", dependencies="[surely-missing]"), encoding="utf-8")
    cli("providers", "disable", "alpha")
    _, out, _ = cli("doctor")
    assert "provider:alpha" not in {c["id"] for c in out["checks"]}


def test_providers_never_turned_on_are_not_checked(workspace, cli, providers_dir):
    (providers_dir / "alpha.md").write_text(
        provider_text("alpha", dependencies="[surely-missing]"), encoding="utf-8")
    _, out, _ = cli("doctor")                    # alpha was never chosen: it is off
    assert "provider:alpha" not in {c["id"] for c in out["checks"]}


# ── job sites are off until the user turns them on ────────────────────────

def test_a_fresh_workspace_lists_every_provider_switched_off(workspace, cli, providers_dir):
    _, out, _ = cli("providers", "list")
    assert {p["id"]: p["enabled"] for p in out["providers"]} == {
        "alpha": False, "beta": False, "gamma": False}


def test_providers_never_chosen_are_not_searched_until_enabled(searchable, cli):
    with db.session(searchable) as conn:  # as if the user never chose any site
        conn.execute("DELETE FROM providers_state")
    _, run, _ = cli("run", "start")
    assert run["to_search"] == []
    assert {p["id"]: p["status"] for p in run["providers"]} == {
        "alpha": "disabled", "beta": "disabled", "gamma": "disabled"}
    cli("run", "finish", str(run["run_id"]))
    with db.session(searchable) as conn:  # finishing a run turns nothing on
        assert conn.execute("SELECT COUNT(*) FROM providers_state WHERE enabled = 1"
                            ).fetchone()[0] == 0

    assert cli("providers", "enable", "beta")[0] == 0
    _, run, _ = cli("run", "start")
    assert run["to_search"] == ["beta"]


def test_a_stored_off_stays_off(searchable, cli):
    cli("providers", "disable", "alpha")
    _, run, _ = cli("run", "start")
    cli("run", "provider", str(run["run_id"]), "beta", "--status", "ok")
    cli("run", "finish", str(run["run_id"]))
    _, out, _ = cli("providers", "list")
    assert {p["id"]: p["enabled"] for p in out["providers"]}["alpha"] is False


def test_setup_turns_on_the_chosen_sites():
    setup = (TEMPLATE.parents[1] / ".claude" / "skills" / "setup" / "SKILL.md").read_text(
        encoding="utf-8")
    step = setup[setup.index("## 8. Job sites"):setup.index("## 9.")]
    assert "`jt providers enable <id>` for each one" in step
    assert "starts switched off" in step
    assert "disable <id>` for those not wanted" not in step
    assert "terms-of-use risk" in step


# ── global and local coverage ─────────────────────────────────────────────

COUNTRIES = ("\n## Countries\n\n| Country | Site | Last verified |\n|---|---|---|\n"
             "| PE | https://pe.example.test | 2026-11-01 |\n{extra}")
CL_ROW = "| CL | https://cl.example.test | 2026-11-02 |\n"


def _problems(tmp_path, cli, name, text):
    path = tmp_path / f"{name}.md"
    path.write_text(text, encoding="utf-8")
    _, out, _ = cli("providers", "validate", str(path))
    return out["files"][0]["problems"]


def test_global_and_local_coverage_are_listed(workspace, cli, tmp_path, monkeypatch):
    folder = tmp_path / "sites"
    folder.mkdir()
    (folder / "world.md").write_text(provider_text("world", regions="[global]"), encoding="utf-8")
    (folder / "andes.md").write_text(
        provider_text("andes", regions="[PE, CL]")
        + COUNTRIES.format(extra=CL_ROW),
        encoding="utf-8")
    (folder / "lima.md").write_text(provider_text("lima"), encoding="utf-8")
    monkeypatch.setenv("JOBTRACKER_PROVIDERS_DIR", str(folder))
    _, out, _ = cli("providers", "list")
    listed = {p["id"]: p for p in out["providers"]}
    assert (listed["world"]["coverage"], listed["world"]["countries"]) == ("global", [])
    assert (listed["andes"]["coverage"], listed["andes"]["countries"]) == ("local", ["PE", "CL"])
    assert (listed["lima"]["coverage"], listed["lima"]["countries"]) == ("local", ["PE"])
    assert all(p["valid"] for p in listed.values()), listed


def test_invalid_regions_are_reported(tmp_path, cli):
    for value in ("[global, PE]", "[pe]", "[]", "[Peru]"):
        problems = _problems(tmp_path, cli, "bad", provider_text("bad", regions=value))
        assert any(p.startswith("field 'regions' must be [global]") for p in problems), value


def test_every_country_of_a_multi_country_provider_is_verified(tmp_path, cli):
    text = provider_text("andes", regions="[PE, CL]")
    assert "missing section '## Countries' (one row per country in 'regions')" in _problems(
        tmp_path, cli, "andes", text)
    problems = _problems(tmp_path, cli, "andes", text + COUNTRIES.format(extra=""))
    assert problems == ["country 'CL' has no row in '## Countries'"]
    problems = _problems(tmp_path, cli, "andes", text + COUNTRIES.format(
        extra="| CL | https://cl.example.test | soon |\n"
              "| AR | https://ar.example.test | 2026-11-01 |\n"))
    assert problems == ["country 'CL' needs a 'Last verified' date like 2026-11-15",
                        "country 'AR' is in '## Countries' but not in 'regions'"]
    assert _problems(tmp_path, cli, "andes", text + COUNTRIES.format(extra=CL_ROW)) == []


def test_one_country_provider_needs_no_countries_table(tmp_path, cli):
    assert _problems(tmp_path, cli, "lima", provider_text("lima")) == []


# ── the repository's provider files ───────────────────────────────────────

def test_every_provider_file_in_the_repository_is_valid():
    from jobtracker.core import providers

    result = providers.validate(TEMPLATE.parent)
    assert result["valid"], result
    assert "linkedin.md" in {f["file"] for f in result["files"]}


def test_linkedin_is_read_logged_out_over_http():
    from jobtracker.core import providers

    listed = {p["id"]: p for p in providers.list_providers(TEMPLATE.parent)}
    linkedin = listed["linkedin"]
    assert (linkedin["access"], linkedin["requires_login"], linkedin["live_walk"]) == (
        "http", False, False)
    assert linkedin["dependencies"] == []                  # the reader uses Python only
    text = (TEMPLATE.parent / "linkedin.md").read_text(encoding="utf-8")
    assert "jt providers read linkedin <run_id> --title" in text
    assert "--readings" in text
    for forbidden in ("Playwright", "the browser extension", "jobs/search"):
        assert forbidden in text.split("## Search recipe")[0]  # named as forbidden
    assert "throttles or blocks requests from the user's IP address" in text


def test_bumeran_is_read_in_a_real_browser_without_an_account():
    from jobtracker.core import providers

    listed = {p["id"]: p for p in providers.list_providers(TEMPLATE.parent)}
    bumeran = listed["bumeran"]
    assert bumeran["valid"], bumeran["problems"]
    assert (bumeran["access"], bumeran["requires_login"], bumeran["live_walk"]) == (
        "playwright", False, False)
    assert bumeran["dependencies"] == ["playwright"] and bumeran["regions"] == ["PE"]
    text = (TEMPLATE.parent / "bumeran.md").read_text(encoding="utf-8")
    assert "jt providers read bumeran <run_id> --title" in text
    assert "--readings" in text
    access = text.split("## Search recipe")[0]
    for forbidden in ("calling Bumeran's API directly", "curl_cffi", "stealth plugins",
                      "proxies", "the user's Bumeran account", "postularV2"):
        assert forbidden in access                         # named as forbidden
    assert "A browser window opens" in access
    assert "1.5.1" in text and "blocks the user's IP address" in text


def test_doctor_names_playwright_for_an_enabled_bumeran(workspace, cli, monkeypatch):
    monkeypatch.setenv("JOBTRACKER_PROVIDERS_DIR", str(TEMPLATE.parent))
    cli("providers", "enable", "bumeran")
    monkeypatch.setattr(doctor, "_tool_available", lambda name: name != "playwright")
    monkeypatch.setattr(doctor.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, ".githooks\n", ""))
    _, out, _ = cli("doctor")
    check = {c["id"]: c for c in out["checks"]}["provider:bumeran"]
    assert check["status"] == "fail" and "playwright" in check["detail"]
    assert "python -m playwright install chromium" in check["fix"]


def test_indeed_is_read_logged_out_in_a_visible_browser():
    from jobtracker.core import providers

    listed = {p["id"]: p for p in providers.list_providers(TEMPLATE.parent)}
    item = listed["indeed"]
    assert item["valid"] is True
    assert (item["access"], item["requires_login"], item["dependencies"]) == (
        "playwright", False, ["playwright"])
    text = (TEMPLATE.parent / "indeed.md").read_text(encoding="utf-8")
    assert "jt providers read indeed <run_id> --title" in text and "--readings" in text
    assert "a headless browser" in text.split("## Search recipe")[0]   # named as forbidden
    assert "blocks requests from the user's IP address" in " ".join(text.split())
