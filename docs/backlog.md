# Backlog

Issues found outside the change being applied. Each one needs its own OpenSpec
change (or a decision to drop it). Nothing here is scheduled.

## Statuses: remove the stage layer; the agent needs the full status

- **Found:** 2026-11-17, by the project owner: statuses now come with a
  second layer of "super-statuses" (stages: to apply, applied, interview,
  offer, closed positive, closed negative) that nobody asked for.
- **Owner's requirement:** the agent analyzes everything, so it must receive
  each application's status by its full descriptive name, to know in its
  learning loop exactly what works or fails, at which step, and why. Grouping
  statuses into broad stages loses that.
- **Where it comes from:** `openspec/specs/application-tracking/spec.md`
  ("One status with a stage", custom statuses assigned to a stage) and
  `applications-board` (stage cards, closed-negative hidden by default,
  filter by stage), implemented in `core/applications.py`
  (`STAGES`, `APPLIED_STAGES`, `OPEN_STAGES`), migration
  `0006_applications.sql` (`statuses.stage`), and `boards/applications.js`.
  Other logic keys off stages too (applied date and snapshot on entering an
  applied stage, follow-up and ghost timing, the open-applications counter,
  the funnel); its change has to say what replaces each one.
- **Check also:** `add-learning-loop` (not built yet) before it is applied, so
  it reads statuses, not stages.

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
