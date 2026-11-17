# Backlog

Issues found outside the change being applied. Each one needs its own OpenSpec
change (or a decision to drop it). Nothing here is scheduled.

## Learning: offered salary, statuses by name, no application snapshot

- **Decided:** 2026-11-17, by the project owner, after
  `remove-status-stages`. It is the next change for the learning loop and
  does not depend on any provider work.
- **Offered salary.** Add the salary the company offered to the application
  (amount, currency, gross or net, monthly, like the asked salary), editable
  by the user in the Applications board, recorded in the history, and given
  to the agent. Learning considers it next to the asked and suggested salary.
- **Statuses by name in learning.** Learning works from results: how far each
  application got and what was offered. The learning history
  (`learning/history.jsonl`, built from `insights.outcomes`) must give each
  application's status and its whole status path by full name, custom
  statuses included, with dates. Today `status` is the English name and
  `status_path` holds built-in keys or stored names.
- **No application snapshot.** The history plus the current data are enough;
  drop `application_snapshots`. What each snapshot field becomes:
  - applied date, asked salary, channel, work mode (as corrected), sent
    resume, and cover letter: the current data. The sent resume is often
    uploaded after marking Applied, so the snapshot recorded it wrongly.
  - title, site, contract type, and posting age: the posting plus the
    applied date.
  - score and salary suggestion at application time: the version that was
    current when the application first got its applied date (`scores` and
    `salary_suggestions` keep every version with its date).
  - Readers to change: `core/insights.py` (`outcomes` joins the snapshot),
    `core/predict.py`, `core/refresh.py`, `core/scoring.py`
    (`at_application`, shown by `jt score show`), `core/applications.py`
    (`_snapshot`, `_update_snapshot`, `snapshot`), `core/tracking.py`
    (`untrack`), `core/demo.py`, `core/demo_learning.py`, and
    `boards/applications.js` (`AskedSuggested` reads the snapshot's
    suggested salary).
- **Context:** since `remove-status-stages`, built-in statuses keep their
  meaning by key (they define "reached interview" and "reached offer" in
  `insights._progress`), and a custom status is only its name and whether it
  ends an application. An application counts as applied when it has an
  applied date.

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
