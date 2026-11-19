"""Self-update (`add-self-update`): `jt update check|finish` on throwaway git repositories,
and one-time offers with a fictional offer."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from jobtracker.core import db, offers, update
from jobtracker.core.errors import JobTrackerError

REPO = Path(__file__).resolve().parent.parent


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout


def _commit(cwd: Path, name: str, content: str, message: str) -> None:
    path = cwd / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(cwd, "add", name)
    _git(cwd, "-c", "user.email=t@example.test", "-c", "user.name=Test", "commit", "-q",
         "-m", message)


@pytest.fixture
def clones(tmp_path):
    """An upstream repository and a user's clone of it, both on main."""
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _git(upstream, "init", "-q", "-b", "main")
    _commit(upstream, "README.md", "hello\n", "Start")
    _commit(upstream, "providers/alpha.md", "alpha\n", "Alpha site")
    _commit(upstream, "src/jobtracker/core/migrations/0001_start.sql", "--\n", "Schema 1")
    _commit(upstream, ".gitignore", "user-data/\n", "Ignore user data")
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", str(upstream), str(clone))
    return upstream, clone


def test_up_to_date(clones, home):
    _, clone = clones
    report = update.check(home, clone)
    assert report["up_to_date"] and report["behind"] == 0 and report["fast_forward"]
    assert report["tracked_changes"] == [] and report["new_providers"] == []


def test_behind_lists_the_news_and_changes_nothing(clones, home):
    upstream, clone = clones
    _commit(upstream, "providers/beta.md", "beta\n", "Add the Beta site")
    _commit(upstream, "src/jobtracker/core/migrations/0002_more.sql", "--\n", "Schema 2")
    head = _git(clone, "rev-parse", "HEAD").strip()
    report = update.check(home, clone)
    assert report["behind"] == 2 and report["fast_forward"] and not report["up_to_date"]
    assert [line.split(" ", 1)[1] for line in report["new_commits"]] == [
        "Schema 2", "Add the Beta site"]
    assert report["new_providers"] == ["beta"]
    assert report["schema_to"] == 2
    assert report["restore"] == f"git reset --hard {head}"
    assert _git(clone, "rev-parse", "HEAD").strip() == head            # nothing pulled
    assert not (clone / "providers" / "beta.md").exists()


def test_ahead_or_diverged_is_not_a_fast_forward(clones, home):
    upstream, clone = clones
    _commit(clone, "notes.md", "mine\n", "A local commit")
    report = update.check(home, clone)
    assert report["ahead"] == 1 and not report["fast_forward"]
    _commit(upstream, "README.md", "changed\n", "Upstream change")
    report = update.check(home, clone)
    assert report["ahead"] == 1 and report["behind"] == 1 and not report["fast_forward"]


def test_a_changed_tracked_file_is_reported_and_user_data_is_not(clones, home):
    _, clone = clones
    (clone / "README.md").write_text("edited by hand\n", encoding="utf-8")
    (clone / "user-data").mkdir()
    (clone / "user-data" / "jobtracker.db").write_text("private", encoding="utf-8")
    (clone / "scratch.txt").write_text("untracked", encoding="utf-8")
    report = update.check(home, clone)
    assert report["tracked_changes"] == ["README.md"]


def test_another_branch_is_not_a_fast_forward(clones, home):
    _, clone = clones
    _git(clone, "checkout", "-q", "-b", "experiment")
    report = update.check(home, clone)
    assert report["branch"] == "experiment" and not report["on_main"]
    assert not report["fast_forward"]


def test_not_a_clone(tmp_path, home):
    with pytest.raises(JobTrackerError) as error:
        update.check(home, tmp_path)
    assert error.value.code == "not_a_clone"


def test_the_pull_keeps_user_data(clones, home):
    upstream, clone = clones
    (clone / "user-data").mkdir()
    private = clone / "user-data" / "profile.json"
    private.write_text('{"name": "fictional"}', encoding="utf-8")
    _commit(upstream, "README.md", "new\n", "News")
    _git(clone, "pull", "-q", "--ff-only", "origin", "main")
    assert private.read_text(encoding="utf-8") == '{"name": "fictional"}'
    assert update.check(home, clone)["up_to_date"]


# ── finish ────────────────────────────────────────────────────────────────

def _venv_root(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / ".venv").mkdir(parents=True)
    (root / "uv.lock").write_text("", encoding="utf-8")
    return root


def test_finish_twice_leaves_everything_working(workspace, tmp_path, monkeypatch):
    root = _venv_root(tmp_path)
    monkeypatch.setattr(update.shutil, "which", lambda name: "/bin/uv" if name == "uv" else None)
    commands = []
    no_tools = lambda paths: {"providers": [], "ok": True}  # noqa: E731
    monkeypatch.setattr(update.doctor, "run", lambda paths: {"checks": [{"status": "pass"}]})
    for _ in range(2):
        report = update.finish(workspace, root, runner=lambda c: commands.append(c) or (0, ""),
                               install_tools=no_tools)
        assert report["ok_all"], report
        assert [s["step"] for s in report["steps"]] == [
            "packages", "database", "command_names", "provider_tools", "diagnostics"]
    assert commands == [["uv", "sync", "--inexact"]] * 2      # keeps tools providers added
    assert db.stored_schema_version(workspace.database) == db.current_schema_version()


def test_finish_stops_at_a_failed_install_and_names_the_backup(workspace, tmp_path,
                                                               monkeypatch):
    root = _venv_root(tmp_path)
    monkeypatch.setattr(update.shutil, "which", lambda name: "/bin/uv")
    report = update.finish(workspace, root, runner=lambda c: (1, "resolution failed"))
    assert not report["ok_all"] and report["failed_step"] == "packages"
    assert "resolution failed" in report["steps"][0]["detail"]
    assert [s["step"] for s in report["steps"]] == ["packages"]


def test_finish_reports_failed_provider_tools(workspace, tmp_path, monkeypatch):
    root = _venv_root(tmp_path)
    monkeypatch.setattr(update.shutil, "which", lambda name: "/bin/uv")
    failing = lambda paths: {"providers": [{"provider": "demo", "ok": False}], "ok": False}  # noqa: E731
    report = update.finish(workspace, root, runner=lambda c: (0, ""), install_tools=failing)
    assert report["failed_step"] == "provider_tools"


def test_finish_before_setup(home, tmp_path, monkeypatch):
    root = _venv_root(tmp_path)
    monkeypatch.setattr(update.shutil, "which", lambda name: "/bin/uv")
    report = update.finish(home, root, runner=lambda c: (0, ""))
    assert report["ok_all"] and report["steps"][-1]["step"] == "database"


# ── one-time offers ───────────────────────────────────────────────────────

@pytest.fixture
def fictional_offer(monkeypatch):
    calls = []
    state = {"applies": True}
    offer = offers.Offer(
        id="regroup-demo",
        text={"en": "Group your earlier searches by day?",
              "es": "¿Agrupar tus búsquedas anteriores por día?"},
        applies=lambda conn, paths: state["applies"],
        apply=lambda conn, paths: calls.append(1) or {"grouped": 3},
    )
    monkeypatch.setattr(offers, "REGISTRY", [offer])
    return calls, state


def test_offer_listed_only_when_it_applies(workspace, cli, fictional_offer):
    _, state = fictional_offer
    _, out, _ = cli("offers", "list")
    assert out["offers"] == [{"id": "regroup-demo", "text": "Group your earlier searches by day?"}]
    state["applies"] = False
    _, out, _ = cli("offers", "list")
    assert out["offers"] == []


def test_offer_accepted_once(workspace, cli, fictional_offer):
    calls, _ = fictional_offer
    code, out, _ = cli("offers", "accept", "regroup-demo")
    assert code == 0 and out["result"] == {"grouped": 3} and calls == [1]
    _, out, _ = cli("offers", "list")
    assert out["offers"] == []                                     # never presented again
    code, out, _ = cli("offers", "accept", "regroup-demo")
    assert code == 1 and out["error"]["code"] == "already_answered" and calls == [1]


def test_offer_declined_is_not_applied_nor_presented_again(workspace, cli, fictional_offer):
    calls, _ = fictional_offer
    _, out, _ = cli("offers", "decline", "regroup-demo")
    assert out["answer"] == "declined" and calls == []
    _, out, _ = cli("offers", "list")
    assert out["offers"] == []


def test_finish_presents_pending_offers(workspace, tmp_path, monkeypatch, fictional_offer):
    root = _venv_root(tmp_path)
    monkeypatch.setattr(update.shutil, "which", lambda name: "/bin/uv")
    monkeypatch.setattr(update.doctor, "run", lambda paths: {"checks": []})
    report = update.finish(workspace, root, runner=lambda c: (0, ""),
                           install_tools=lambda p: {"providers": [], "ok": True})
    assert [o["id"] for o in report["offers"]] == ["regroup-demo"]


def test_unknown_offer(workspace, cli):
    code, out, _ = cli("offers", "accept", "no-such-offer")
    assert code == 1 and out["error"]["code"] == "not_found"
