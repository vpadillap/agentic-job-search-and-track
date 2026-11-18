# Backlog

Issues found outside the change being applied. Each one needs its own OpenSpec
change (or a decision to drop it). Nothing here is scheduled.

## Try Scrapling on the other providers

- **Found:** 2026-11-18, while studying Glassdoor (`add-provider-glassdoor`).
  Scrapling's headless stealth session passed Cloudflare where Playwright did
  not: several searches in one session, the site's "Show more" button, and
  posting pages, with no visible window.
- **Owner's note:** see whether the other providers improve with it. Indeed
  (visible window, 30 postings per title, posting pages ask to sign in) and
  Bumeran (visible window) are the first candidates; LinkedIn reads over HTTP
  and is not affected.
- **How:** each provider in its own change, with a study comparing results
  and the user's account rule (no logged-in automation where an account could
  be banned).

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
