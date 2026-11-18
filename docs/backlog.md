# Backlog

Issues found outside the change being applied. Each one needs its own OpenSpec
change (or a decision to drop it). Nothing here is scheduled.

## Browser tests are skipped silently on local machines without Chromium

- **Found:** 2026-11-17. A local `uv run pytest` reported 46 skipped tests:
  every test in `tests/test_browser.py` skips when Playwright's Chromium is
  not installed, and nothing in the summary says the panel went untested. CI
  installs Chromium, so they do run there.
- **Workaround:** `uv run playwright install chromium`, then run the tests.
- **Possible direction:** mention the Chromium step in the contributor setup
  (`AGENTS.md`, README), or print a clear warning when the browser tests skip.

## A registered document version cannot be withdrawn

- **Found:** 2026-11-17, same run. A tailored resume registered by mistake
  (here, with corrupted accents from a stdin encoding bug, since fixed) stays
  in the application's history; only a newer version can replace it.
- **Spec:** `document-preparation` forbids modifying earlier versions; a
  "withdraw" (hide, keep the file) would need its own change.
