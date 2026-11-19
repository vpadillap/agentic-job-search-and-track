"""add-changelog: the user-facing changelog, its check, and what `jt update check` reads."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from jobtracker.core import providers, update
from tests.test_self_update import _commit, _git, clones  # noqa: F401  (fixture)

REPO = Path(__file__).resolve().parent.parent

ENTRY = """## 2026-12-01 · add-provider-fictional

Added
- Fictional Jobs is a job site in Peru.

Fixed
- The panel shows dates in your language.

Providers: fictional
Offers: none
Action: turn it on in /setup if you search in Peru
"""


def _script():
    spec = importlib.util.spec_from_file_location("check_changelog",
                                                  REPO / "scripts" / "check_changelog.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_an_entry_is_parsed():
    (entry,) = update.parse_changelog("# Changelog\n\n" + ENTRY)
    assert entry["date"] == "2026-12-01" and entry["change"] == "add-provider-fictional"
    assert entry["added"] == ["Fictional Jobs is a job site in Peru."]
    assert entry["fixed"] == ["The panel shows dates in your language."]
    assert entry["changed"] == [] and entry["offers"] == []
    assert entry["providers"] == ["fictional"]
    assert entry["action"] == "turn it on in /setup if you search in Peru"


def test_the_repositorys_changelog_is_complete_and_names_real_providers():
    entries = update.parse_changelog((REPO / "CHANGELOG.md").read_text(encoding="utf-8"))
    assert entries and [e["date"] for e in entries] == sorted(
        (e["date"] for e in entries), reverse=True)                 # newest first
    known = {p["id"] for p in providers.list_providers(REPO / "providers")}
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    for entry in entries:
        assert entry["added"] or entry["changed"] or entry["fixed"], entry["change"]
        assert set(entry["providers"]) <= known, entry["change"]
    assert text.count("\nProviders:") == text.count("\nOffers:") == text.count(
        "\nAction:") == len(entries)


def test_check_lists_the_entries_the_clone_does_not_have(clones, home):  # noqa: F811
    upstream, clone = clones
    _commit(upstream, "CHANGELOG.md", "# Changelog\n", "Start the changelog")
    _git(clone, "pull", "-q", "--ff-only", "origin", "main")
    _commit(upstream, "CHANGELOG.md", "# Changelog\n\n" + ENTRY, "Add Fictional Jobs")
    report = update.check(home, clone)
    assert [c["change"] for c in report["changes"]] == ["add-provider-fictional"]
    _git(clone, "pull", "-q", "--ff-only", "origin", "main")
    assert update.check(home, clone)["changes"] == []


def test_ci_check_needs_an_entry_only_for_user_facing_files():
    script = _script()
    assert script.needs_entry(["src/jobtracker/core/search.py"])
    assert script.needs_entry(["providers/fictional.md", "README.md"])
    assert not script.needs_entry(["src/jobtracker/core/search.py", "CHANGELOG.md"])
    assert not script.needs_entry(["tests/test_search.py", "openspec/changes/x/proposal.md"])


def test_ci_check_runs_against_a_base(clones):  # noqa: F811
    _, clone = clones
    _git(clone, "checkout", "-q", "-b", "work")
    _commit(clone, "src/app.py", "print(1)\n", "Code without an entry")
    run = lambda: subprocess.run(  # noqa: E731
        [sys.executable, str(REPO / "scripts" / "check_changelog.py"), "main"], cwd=clone,
        capture_output=True, text=True)
    assert run().returncode == 1
    _commit(clone, "CHANGELOG.md", "# Changelog\n\n" + ENTRY, "Its entry")
    assert run().returncode == 0
