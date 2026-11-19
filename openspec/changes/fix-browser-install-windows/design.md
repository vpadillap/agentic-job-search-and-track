## Context

Scrapling 0.5 starts Patchright's Chromium with `channel="chromium"` and a
persistent context; Patchright and Playwright read the browser folder from
`PLAYWRIGHT_BROWSERS_PATH` (default on Windows: `%LOCALAPPDATA%\ms-playwright`).
Inside an MSIX-packaged host (the Claude desktop app), writes to
`%LOCALAPPDATA%` are redirected to the package's private copy, and the
side-by-side manifest that `chrome.exe` needs is not found there. Copies of
the same folder start under `%USERPROFILE%` and `%TEMP%`, and fail anywhere
under `%LOCALAPPDATA%`.

## Goals / Non-Goals

**Goals:** Scrapling's browser starts on any Windows machine, inside or
outside a packaged host, with no manual step; a broken browser is repaired
by `jt providers install`.

**Non-Goals:** changing how any site is read; managing browsers left in the
old folder.

## Decisions

### D1. A fixed browser folder on Windows, set by `jobtracker` itself

`core/browsers.py` exposes `configure()`, called first thing by the CLI's
`main()`. On Windows, when `PLAYWRIGHT_BROWSERS_PATH` is not set, it sets it
to `%USERPROFILE%\.cache\ms-playwright` in the process environment. Every
reader runs inside that process and every install step is a child process
that inherits the variable, so installs and reads always agree on the
folder. A value the user set (including `0`) is kept.

Alternatives considered:
- *Detect MSIX redirection and move only then*: detection is unreliable
  (the shell started by the host reports no package identity yet is
  redirected), and behavior would differ between a terminal and the app.
  Rejected.
- *Ask the user to set the variable (setx)*: a manual step, against the
  "the user never installs by hand" rule, and invisible to new clones.
  Rejected.
- *`real_chrome=True` (use an installed Google Chrome)*: works only where
  Chrome is installed, changes the browser's fingerprint per machine, and
  depends on the user's Chrome version. Rejected.
- *A folder inside the clone (`.venv`)*: clones often live in synced folders
  (OneDrive), which slows and sometimes locks large binaries. Rejected.
- *`%TEMP%`*: not redirected, but cleaned by the system. Rejected.

### D2. A browser tool is installed only when it starts

For tools with a check (Scrapling, Playwright), `install()` runs the check
even when the package imports. If it passes, the tool is "already"
installed (one browser start, a few seconds). If it fails, only the browser
steps run (the package is not reinstalled), then the check again; the tool
is then reported as installed and listed under `repaired`. Tools without a
recipe keep the import test.

Alternatives considered:
- *Check at read time only*: the reader can only say "run install", which
  is what failed before. Rejected.
- *Always reinstall*: pip and the browser download on every search. Rejected.

### D3. Recipes split into package, browser, and check

Each recipe lists `package` steps (pip), `browser` steps (the browser
download), and `check`. A missing package runs all three; a broken browser
runs `browser` and `check`.

Alternatives considered:
- *One flat list of steps*: cannot skip pip when only the browser is
  broken. Rejected.

## Risks / Trade-offs

- Windows machines that already had working browsers in the old folder
  download them once more (about 150 MB per tool). Accepted for one shared
  rule.
- The check adds a browser start (a few seconds) to each
  `jt providers install` call before a search. Accepted.
- Running Playwright directly (`python -m playwright install chromium`, as
  the panel tests' setup does) still uses Playwright's default folder. Not
  affected: the panel tests start the headless shell, which has no
  side-by-side manifest.
