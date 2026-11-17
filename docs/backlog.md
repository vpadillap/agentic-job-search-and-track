# Backlog

Issues found outside the change being applied. Each one needs its own OpenSpec
change (or a decision to drop it). Nothing here is scheduled.

## Applications board: changing a status is hard to find

- **Found:** 2026-11-17, by the project owner ("the user cannot edit the status
  of tracked items").
- **Current behavior:** status editing works (covered by
  `test_inline_status_change_persists` and
  `test_inline_status_creation_and_tags`), but the only entry point is a small
  "+" button after the status chip. Its accessible name is "Change status or
  add a tag", but visually it reads as "add". Clicking the status chip itself
  does nothing.
- **Spec:** `openspec/specs/applications-board/spec.md`, requirement "Inline
  editing" ("the user picks a new status in a row").
- **Possible direction (to decide in its change):** make the status chip the
  control that opens the status picker, and keep "+" for tags only.

## Browser tests are skipped silently on local machines without Chromium

- **Found:** 2026-11-17. A local `uv run pytest` reported 46 skipped tests:
  every test in `tests/test_browser.py` skips when Playwright's Chromium is
  not installed, and nothing in the summary says the panel went untested. CI
  installs Chromium, so they do run there.
- **Workaround:** `uv run playwright install chromium`, then run the tests.
- **Possible direction:** mention the Chromium step in the contributor setup
  (`AGENTS.md`, README), or print a clear warning when the browser tests skip.

## Demo seed: a score note lists dbt as both matched and missing

- **Found:** 2026-11-17, during the end-to-end run of `/prepare-documents`.
  Quipu Analytics' demo score note says "Matches … dbt … Missing: dbt".
- **Where:** `src/jobtracker/core/demo.py` (from `add-panel-search-tab`).

## A registered document version cannot be withdrawn

- **Found:** 2026-11-17, same run. A tailored resume registered by mistake
  (here, with corrupted accents from a stdin encoding bug, since fixed) stays
  in the application's history; only a newer version can replace it.
- **Spec:** `document-preparation` forbids modifying earlier versions; a
  "withdraw" (hide, keep the file) would need its own change.

## Job-search scoring guide: resume reference format

- **Found:** 2026-11-17, same run. `.claude/skills/job-search/scoring-guide.md`
  shows `"ref": "<file name>"`, while `jobtracker pending` gives refs like
  `resume-proposed-v2.docx#v2`. The prepare-documents skill now says to send
  the pending item's `resume` object as is; the job-search guide still shows
  the older form.
