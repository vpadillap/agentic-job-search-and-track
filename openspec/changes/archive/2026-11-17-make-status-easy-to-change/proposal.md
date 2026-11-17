## Why

The learning loop lives on the outcomes the user records, and the main way to
record one is changing an application's status. Today that is hard to find:
the only entry point is a small "+" after the status chip, which reads as "add
a tag"; clicking the status itself does nothing. The project owner could not
find it ("the user cannot edit the status of tracked items"; see
`docs/backlog.md`).

## What Changes

- The status chip in each Applications row becomes the control that opens the
  status picker: built-in and custom statuses grouped by stage, and creating a
  new status inline, as today.
- The "+" button is for tags only.
- The chip looks clickable (hover and focus state, a small chevron) and has an
  accessible name that says what it does ("Status: Applied. Change status").
- The backlog entry is removed.

## Non-goals

- Changing statuses, stages, tags, or how changes are saved.
- Bulk status changes beyond the existing ghost action.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `applications-board`: "Inline editing" says the status is changed from the
  status itself, and tags from their own control.

## Impact

- `src/jobtracker/web/static/boards/applications.js` (status chip as picker
  button, tag menu separate), locale strings (en/es), CSS.
- `tests/test_browser.py` (existing status tests use the new entry point).
- `docs/backlog.md`.
