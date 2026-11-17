## Why

Every application status is grouped into a "stage" (to apply, applied,
interview, offer, closed positive, closed negative) that the project owner
never asked for. The panel counts and filters by those stages, custom
statuses must be assigned to one, and the agent sees a stage next to each
status. The agent analyzes the results, so it needs each application's status
by its full descriptive name and the path of statuses it went through; broad
stages hide exactly that.

## What Changes

- **BREAKING** Statuses are a flat list. The stage of each status is removed
  (database, CLI, API, panel, agent output). Each status says instead whether
  an application **ended** with it. Built-in statuses know theirs (Accepted,
  Rejected, Ghosted, Offer declined, No economic alignment, and Withdrawn end
  an application; New, Applied, Interview, and Offer do not). Creating a
  custom status asks only for its name and "did the application end with
  this status?". Existing custom statuses keep working: those in a closed
  stage become ending statuses.
- Built-in statuses keep their fixed meaning through their stable key, used
  only where the system must act on a status: filling in the applied date,
  the next step for an interview or offer, and the learning outcome flags.
  Custom statuses carry only their name and whether they end an application.
- **Applied** means the application has an applied date. The date is still
  filled in automatically the first time a built-in status that implies
  having applied is set (Applied, Interview, Offer, Accepted, Rejected,
  Ghosted, Offer declined, No economic alignment) and is still editable and
  clearable in the table. New, Withdrawn, and custom statuses never fill it
  in.
- Everything that read stages reads the new rules: follow-up and no-response
  reminders apply to applications with an applied date that have not ended;
  documents are pending for applications without an applied date that have
  not ended; the open-applications counter counts applications that have not
  ended; the snapshot of the facts at application time is taken when the
  application first gets an applied date.
- **BREAKING** Applications board: the stage cards become one count card per
  status in use, with its full name, each filtering by that status.
  Applications whose status ended are hidden by default (the board says how
  many and with which statuses), and shown on request. Sorting by status
  follows the order of the status list. Status chips lose their stage colors;
  ended statuses look muted.
- **BREAKING** CLI and API: `--stage` is replaced by `--status` on
  `applications list`, by `--ends yes|no` on `statuses create` and on
  `applications status` when it creates a status, and `--hide-closed` by
  `--hide-ended`. The API's `stage` field is replaced by `ends`.
- The agent receives, for every application, the full status name (in the
  panel language, with both names and the stable key for built-ins), whether
  it ended, and the history of status changes with each status's full name
  and date. No stage appears anywhere.
- Learning keeps working without stages: its interpretation of statuses
  (`insights._progress`) and the "apply next" list read the built-in keys,
  the "ends" flag, and the applied date. Giving the learning history the
  statuses by name, the offered salary, and the future of the application
  snapshot are left to a later change, at the owner's request.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `application-tracking`: "One status with a stage" becomes flat statuses
  that say whether they end an application; custom statuses are created with
  a name and that answer; applied is defined by the applied date and its
  automatic filling; the snapshot is taken when the applied date is first
  set; reminders apply to applications that have not ended; the agent gets
  full status names and their history.
- `applications-board`: stage cards become one card per status; ended
  applications are hidden by default instead of the closed negative stage;
  filtering by stage is removed.

## Impact

- Database: migration `0012_status_ends.sql` adds `statuses.ends`, fills it
  (built-ins by key, custom statuses from their old stage), and removes
  `statuses.stage`.
- Code: `core/applications.py` (statuses, `set_status`, next step,
  attention, funnel, list, history), `core/tracking.py`, `core/board.py`,
  `core/recommend.py`, `core/insights.py` (`_progress` only and the outcome
  record's stage field), `core/demo.py`, `cli/main.py`, `web/app.py`,
  `web/static/boards/applications.js`, `boards/search.js` (the "tracked,
  applied" label), `api.js`, `app.css`, locales (en/es).
- Skills and docs: `.claude/skills/prepare-documents/SKILL.md`
  (`--stage to_apply`), README, `docs/backlog.md` (entry removed).
- Tests: tracking, board, API, CLI, browser, learning tests that set or read
  stages.
- Not touched here (later change, by the owner's decision): the learning
  history's status names, an offered-salary field, and whether the
  application snapshot is kept.
