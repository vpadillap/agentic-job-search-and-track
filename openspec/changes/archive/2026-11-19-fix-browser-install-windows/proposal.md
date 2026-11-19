## Why

On Windows, the job-site readers that run on Scrapling (Bumeran, Indeed,
Glassdoor) can fail to start their browser with
`BrowserType.launch_persistent_context: spawn UNKNOWN`, even right after
`jt providers install` reported success. Found on a Windows 11 machine where
the agent runs inside the Claude desktop app:

- The desktop app is an MSIX package. Windows redirects what a packaged app
  (and the processes it starts) writes under `%LOCALAPPDATA%` (except
  `Temp`) into `%LOCALAPPDATA%\Packages\<app>\LocalCache\Local\...`.
  Playwright and Patchright install their browsers in
  `%LOCALAPPDATA%\ms-playwright` by default, so they land in that redirected
  copy.
- The full Chromium `chrome.exe` loads `chrome_elf.dll` through a
  side-by-side manifest (`<version>.manifest`). Windows resolves that
  manifest outside the redirection, does not find it, and refuses to start
  the program ("the side-by-side configuration is incorrect"; the
  Application log shows a *SideBySide* error). Playwright reports only
  `spawn UNKNOWN`.
- Scrapling's stealth session asks for `channel="chromium"`, which starts
  that full `chrome.exe`. Plain Playwright starts `chrome-headless-shell.exe`
  by default, which has no such manifest, so the panel tests and the
  installer's Playwright check still pass.
- `jt providers install` counts a tool as present when its Python package
  imports, so it never ran its own check and never repaired the browser;
  the readers' message ("run jt providers install") led nowhere.

The same copy of the browser starts normally from any folder outside
`%LOCALAPPDATA%`.

## What Changes

- On Windows, `jobtracker` uses a fixed browser folder outside
  `%LOCALAPPDATA%` (`%USERPROFILE%\.cache\ms-playwright`) by setting
  `PLAYWRIGHT_BROWSERS_PATH` for itself and every command it starts, unless
  the user already set that variable. Other systems keep Playwright's
  default.
- `jt providers install` counts a browser tool (Scrapling, Playwright) as
  present only when its check really starts the browser; when the package
  is there but the browser does not start, it installs the browser again.
  The report names the browser folder.
- The Bumeran and Glassdoor readers keep using Scrapling's own Chromium (no
  dependency on an installed Google Chrome).

## Non-goals

- No change to how any job site is read, paced, or parsed.
- No change to the panel tests' browser setup (they use the headless shell,
  which is not affected).
- No detection of MSIX packaging: the fixed folder is used on every Windows
  machine, packaged or not, so the behavior is the same everywhere.
- No clean-up of browsers left in the old folder; the user may delete them.

## Capabilities

### New Capabilities

- `provider-tools`: where the tools that providers need are installed and
  when they count as installed.

## Impact

- `src/jobtracker/core/browsers.py` (new, standard library only),
  `src/jobtracker/core/installer.py`, `src/jobtracker/cli/main.py`.
- `tests/test_installer.py`, `tests/test_browsers.py` (new).
- `CONTRIBUTING.md`: where the browsers go on Windows.
- One-time cost on Windows machines that already had browsers in the old
  folder: the next `jt providers install` downloads them again (about
  150 MB).
