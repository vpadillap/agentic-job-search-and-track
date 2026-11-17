## Why

The panel does not let the user read the job they are working on. In the
Search tab the description sits in a 250-pixel box with its own scroll bar,
cut off after a few lines while space beside it stays empty; real postings run
4,000–9,000 characters. In the Applications tab the description is not shown
at all, even with the row expanded, and there is no link to the posting, so
the user cannot apply from the tab where they prepare and track the
application (track → prepare documents → apply). Reported by the project
owner as critical (`docs/backlog.md`).

## What Changes

- The description is readable in full in both tabs. The expanded row shows
  its beginning, and "Read the full description" opens the complete text in
  place, without a box with its own scroll bar; "Show less" closes it.
- The Applications tab shows the description in the expanded row, the same
  way as the Search tab.
- The Applications tab links to the original posting in every row (next to
  the job title, with the site's name) and in the expanded row; it opens in a
  new tab.
- The two backlog entries are removed from `docs/backlog.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `search-results-board`: "Expandable detail" requires the complete
  description to be readable without an inner scroll box.
- `applications-board`: "Table of all tracked applications" includes the link
  to the original posting; "Expandable detail" includes the complete
  description.

## Non-goals

- Changing how descriptions are captured or stored.
- Formatting descriptions (headings, bold): they stay verbatim text.
- Any other part of the boards.

## Impact

- Frontend: a shared description component (`components/`), `boards/search.js`,
  `boards/applications.js`, `app.css`, locale strings (en/es).
- No API change: `/api/applications/{job}` already returns the description
  and each row already carries the posting's URL.
- Tests: browser tests for both tabs.
- `docs/backlog.md`.
