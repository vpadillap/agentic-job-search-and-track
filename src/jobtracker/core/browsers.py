"""Where the browsers that providers need are kept (Playwright, Patchright/Scrapling).

On Windows, Playwright's default folder is `%LOCALAPPDATA%\\ms-playwright`. When the
agent runs inside a packaged desktop app (MSIX), Windows redirects what it writes there
into the app's private copy, and the full Chromium (`chrome.exe`, which Scrapling
starts) then cannot load its side-by-side manifest: it fails with `spawn UNKNOWN`.
A folder under the user's profile is never redirected, so on Windows every command
uses `%USERPROFILE%\\.cache\\ms-playwright` unless the user chose a folder.
Standard library only.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ENV = "PLAYWRIGHT_BROWSERS_PATH"


def default_location(platform: str | None = None, home: Path | None = None) -> Path | None:
    """The folder this project uses on `platform`, or None for the tools' default."""
    if (platform or sys.platform) != "win32":
        return None
    try:
        return (home or Path.home()) / ".cache" / "ms-playwright"
    except RuntimeError:  # no profile folder known (a bare environment): tools' default
        return None


def configure(environ: dict | None = None, platform: str | None = None,
              home: Path | None = None) -> str | None:
    """Set the browser folder for this process and the commands it starts.

    A folder the user already set (including Playwright's `0`) is kept. Returns the
    folder in use, or None when the tools' default applies."""
    env = os.environ if environ is None else environ
    if env.get(ENV):
        return env[ENV]
    location = default_location(platform, home)
    if location is None:
        return None
    env[ENV] = str(location)
    return env[ENV]


def location(environ: dict | None = None) -> str:
    """The folder in use, for reports."""
    env = os.environ if environ is None else environ
    return env.get(ENV) or "the tools' default folder"
