# Backlog

Issues found outside the change being applied. Each one needs its own OpenSpec
change (or a decision to drop it). Nothing here is scheduled.

## CRITICAL: the user cannot read the job description (Search and Applications tabs)

- **Found:** 2026-11-17, by the project owner ("the user can't read the actual
  job description in the Búsqueda tab or in the Postulaciones tab").
- **Current behavior:**
  - Search tab: the description exists only inside a row's expanded detail,
    in a box capped at 250 px with its own scroll (`.description` in
    `src/jobtracker/web/static/app.css`, `RowDetail` in
    `boards/search.js`). The owner reports it cannot be read there; the
    cause is not yet diagnosed (reproduce with the owner first).
  - Applications tab: confirmed by the owner in the demo: no description even
    with the row expanded. `GET /api/applications/{job}` returns
    `description` (`core/applications.py`, `detail()`), but
    `boards/applications.js` never renders it.
- **Spec:** `search-results-board` (row detail shows the description) and
  `applications-board` (detail of an application).
- **Why it matters:** the description is what the user judges a job by, and
  what they check before applying.

## CRITICAL: the Applications tab has no link to the job posting

- **Found:** 2026-11-17, by the project owner.
- **Current behavior:** `boards/applications.js` links only to stored
  documents; the posting's `url` is shown nowhere in the Applications tab.
  The Search tab has it (a link in the row detail), which forces the user to
  go back to the Search tab and find the row.
- **Why it matters:** the flow is track → prepare documents → apply, and
  applying happens on the posting's page. Without the link the user cannot
  apply from the Applications tab.
- **Spec:** `applications-board`.

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
