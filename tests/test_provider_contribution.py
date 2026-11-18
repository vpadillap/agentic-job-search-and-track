"""provider-contribution: private providers (files and readers), the rules and templates
for contributing one, and the /add-provider skill. Fictional sites only."""
from __future__ import annotations

import re
from pathlib import Path

from jobtracker.cli.main import build_parser
from tests.helpers import provider_text
from tests.test_setup import _subcommands

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / ".claude" / "skills" / "add-provider" / "SKILL.md"

PRIVATE_READER = '''
def read(paths, run_id, title, location=None):
    return {"provider": "acme-jobs", "run_id": run_id, "title": title, "private": True}
'''


def private_folder(workspace) -> Path:
    folder = workspace.home / "providers"
    folder.mkdir(exist_ok=True)
    return folder


# ── private providers ─────────────────────────────────────────────────────

def test_a_private_provider_is_listed_enabled_and_searched(searchable, cli):
    folder = private_folder(searchable)
    (folder / "acme-jobs.md").write_text(provider_text("acme-jobs"), encoding="utf-8")
    (folder / "acme-jobs.study.md").write_text("# study\n", encoding="utf-8")   # not a provider
    _, out, _ = cli("providers", "list")
    listed = {p["id"]: p for p in out["providers"]}
    acme = listed["acme-jobs"]
    assert (acme["origin"], acme["valid"], acme["enabled"]) == ("private", True, False)
    assert acme["path"] == str(folder / "acme-jobs.md")
    assert listed["alpha"]["origin"] == "repo"
    assert "acme-jobs.study" not in listed
    assert cli("providers", "enable", "acme-jobs")[0] == 0
    _, run, _ = cli("run", "start")
    assert "acme-jobs" in run["to_search"]


def test_a_private_id_already_used_is_invalid(searchable, cli):
    (private_folder(searchable) / "alpha.md").write_text(provider_text("alpha"),
                                                         encoding="utf-8")
    _, out, _ = cli("providers", "list")
    private = next(p for p in out["providers"] if p["id"] == "alpha" and p["origin"] == "private")
    assert private["valid"] is False
    assert any("id already used by providers/alpha.md" in p for p in private["problems"])
    repo = next(p for p in out["providers"] if p["id"] == "alpha" and p["origin"] == "repo")
    assert repo["valid"] is True


def test_a_private_reader_runs_like_a_built_in_one(searchable, cli):
    folder = private_folder(searchable)
    (folder / "acme-jobs.md").write_text(provider_text("acme-jobs"), encoding="utf-8")
    (folder / "acme-jobs.py").write_text(PRIVATE_READER, encoding="utf-8")
    cli("providers", "enable", "acme-jobs")
    _, run, _ = cli("run", "start")
    code, out, _ = cli("providers", "read", "acme-jobs", str(run["run_id"]), "--title",
                       "Senior Data Engineer")
    assert code == 0, out
    assert out["read"] == {"provider": "acme-jobs", "run_id": run["run_id"],
                           "title": "Senior Data Engineer", "private": True}
    code, out, _ = cli("providers", "read", "acme-jobs", str(run["run_id"]), "--title", "x",
                       "--found", "links.json")
    assert code == 1 and out["error"]["code"] == "invalid_option"


def test_a_reader_file_without_a_private_provider_is_not_run(searchable, cli):
    (private_folder(searchable) / "alpha.py").write_text(PRIVATE_READER, encoding="utf-8")
    _, run, _ = cli("run", "start")
    code, out, _ = cli("providers", "read", "alpha", str(run["run_id"]), "--title", "x")
    assert code == 1 and out["error"]["code"] == "no_reader"     # alpha is a repo provider


def test_doctor_names_the_private_file_of_an_invalid_provider(searchable, cli, monkeypatch):
    from jobtracker.core import doctor

    folder = private_folder(searchable)
    (folder / "acme-jobs.md").write_text(provider_text("acme-jobs", dependencies="[scrapling]"),
                                         encoding="utf-8")
    cli("providers", "enable", "acme-jobs")
    monkeypatch.setattr(doctor, "_tool_available", lambda name: False)
    _, out, _ = cli("doctor")
    check = next(c for c in out["checks"] if c["id"] == "provider:acme-jobs")
    assert check["status"] == "fail" and "scrapling" in check["detail"]


def test_paths_name_the_private_folders(workspace, cli):
    _, out, _ = cli("paths")
    assert out["paths"]["private_providers"] == str(workspace.home / "providers")
    assert out["paths"]["provider_settings"] == str(workspace.home / "provider-settings")


# ── rules, templates, skill ───────────────────────────────────────────────

def test_rules_and_templates_exist():
    rules = (REPO / "providers" / "CONTRIBUTING.md").read_text(encoding="utf-8")
    for required in ("user-data/providers/<id>.md", "Study before", "Proved means",
                     "rewritten without personal data", "/add-provider",
                     "Never type or pass credentials"):
        assert required in rules, required
    for name in ("proposal.md", "spec.md", "tasks.md"):
        assert (REPO / "providers" / "change-template" / name).is_file()
    pr = (REPO / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    assert "New job site" in pr and "privacy guard" in pr
    assert "CONTRIBUTING.md" in (REPO / "providers" / "README.md").read_text(encoding="utf-8")


def test_the_skill_names_its_steps_and_limits():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\nname: add-provider\n")
    for required in ("providers/CONTRIBUTING.md", "private_providers", "jt providers validate",
                     "jt providers enable", "Prove it", "Offer a pull request",
                     "Without a clear yes, stop", "gh auth status", "gh pr create",
                     "python scripts/check_private.py", "providers/change-template/",
                     "Never type, ask for, or pass the user's credentials"):
        assert required in text, required


def test_the_skill_only_uses_commands_that_exist():
    text = SKILL.read_text(encoding="utf-8")
    found = set(re.findall(r"`jt ([a-z]+(?: [a-z-]+)?)", text))
    top = _subcommands(build_parser())
    for command in found:
        words = command.split()
        assert words[0] in top, command
        sub = _subcommands(top[words[0]])
        if sub is not None and len(words) > 1 and not words[1].startswith("<"):
            assert words[1] in sub, command
