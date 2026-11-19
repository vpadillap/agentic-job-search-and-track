"""Where provider browsers are kept: a fixed folder outside %LOCALAPPDATA% on Windows."""
from __future__ import annotations

import os
from pathlib import Path

from jobtracker.core import browsers


def test_windows_uses_a_folder_under_the_profile():
    env: dict = {}
    home = Path("C:/Users/someone")
    chosen = browsers.configure(env, platform="win32", home=home)
    assert chosen == str(home / ".cache" / "ms-playwright")
    assert env[browsers.ENV] == chosen
    assert "AppData" not in chosen


def test_a_folder_the_user_chose_is_kept():
    env = {browsers.ENV: "D:/browsers"}
    assert browsers.configure(env, platform="win32") == "D:/browsers"
    assert env[browsers.ENV] == "D:/browsers"
    env = {browsers.ENV: "0"}                       # Playwright's "inside the package"
    assert browsers.configure(env, platform="win32") == "0"


def test_other_systems_keep_the_default():
    for platform in ("linux", "darwin"):
        env: dict = {}
        assert browsers.configure(env, platform=platform) is None
        assert env == {}
    assert browsers.location({}) == "the tools' default folder"


def test_no_profile_folder_keeps_the_default(monkeypatch):
    def no_home():
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.setattr(Path, "home", staticmethod(no_home))
    env: dict = {}
    assert browsers.configure(env, platform="win32") is None and env == {}


def test_the_cli_sets_the_folder_for_every_command(cli, home, monkeypatch):
    monkeypatch.delenv(browsers.ENV, raising=False)  # restored by conftest's fixture
    monkeypatch.setattr(browsers, "default_location",
                        lambda platform=None, home=None: Path("/fixed/ms-playwright"))
    cli("context")
    assert os.environ[browsers.ENV] == str(Path("/fixed/ms-playwright"))
