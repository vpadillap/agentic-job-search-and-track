## Why

Searching is only useful if the user can follow each opportunity to its
outcome. The tracked-applications board is where the user records what really
happened, and those records are the raw material of the learning loop.

## What Changes

- Add the Applications board (board 2 of the design): funnel by stage,
  "needs something" summary, table of all tracked postings across searches,
  type-ahead search, filters, sorting, and expandable rows.
- Add statuses that behave like tags: built-in statuses plus user-created ones
  added inline, each mapped to a stage; plus free-form tags.
- Add the user's application record: applied date, monthly salary asked,
  channel, contact, notes, next step, and upload/replacement of the resume
  actually sent.
- Add the timeline of events per application and the application snapshot
  taken at the moment of applying.
- Hide negative closed applications by default, with a toggle to show them.

## Non-goals

- Generating resumes, cover letters, or form answers (see
  `add-document-preparation`); this change shows document slots and accepts
  the user's upload.
- Calendar or email integration; reminders are shown in the panel only.

## Capabilities

### New Capabilities

- `application-tracking`: tracked postings, their statuses, tags, user-entered
  details, uploaded resume, and history.
- `applications-board`: viewing, searching, filtering, and editing tracked
  applications in the panel.

### Modified Capabilities

None.

## Impact

- New: applications tables (migration extending the minimal record from
  `add-panel-search-tab`), API routes, upload handling (`python-multipart`),
  `jobtracker applications …`, Applications board frontend.
- Depends on `add-panel-search-tab`.
