## Why

The Search and Applications tables are wider than the screen: the stylesheet
gives the table a minimum width of 1,300 pixels (`.table { min-width:
1300px }`) and the actions column alone takes 250, so on a 1,366-pixel laptop
screen, or any window that is not maximized, the user has to scroll sideways
to see the salary, the date, or the actions. The salary rework will add more
to the salary cell. The owner wants the tables' layout and usability improved.

## Study (short; first section)

With the demo's fictional data (`jt demo seed` in a temporary home), the
Search and Applications tabs are captured at 1,920, 1,440, 1,366, 1,280,
1,024, and 768 pixels wide (and a phone width), recording for each: whether
the page scrolls sideways, which columns are cut, row height, and what the
user has to do to reach the actions. The captures and a short table go into
this proposal; the layout below is confirmed or revised with them, and the
owner approves before implementing.

## What Changes (expected; revised after the study)

- **No sideways scroll from 1,280 pixels up**: the fixed minimum width goes;
  columns get flexible widths with sensible minimums, long text wraps or is
  shortened with the full text on hover and in the detail.
- **Compact actions**: the row's actions (track, dismiss, open, …) become
  icon buttons with labels for screen readers and tooltips, plus a "more"
  menu, instead of a 250-pixel column of buttons.
- **Fewer, denser columns**: the source link moves into the job cell (under
  the title and company), the publication date becomes a short relative date
  with the full date on hover; the salary cell keeps the offered and
  suggested ranges on two short lines (coordinated with
  `rework-salary-research`).
- **Narrow screens**: below about 1,024 pixels, secondary columns move into
  the row's expandable detail; at phone width, each row becomes a card with
  the title, company, score, salary, and actions.
- The Applications table gets the same treatment.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `search-results-board`: the table fits the screen.
- `applications-board`: the table fits the screen.

## Impact

- `src/jobtracker/web/static/app.css`, `components/data-table.js`,
  `boards/search.js`, `boards/applications.js`, locales (en/es) for new
  labels; browser tests at several widths (no horizontal scroll from 1,280;
  actions reachable; cards at phone width).
- Coordinated with `rework-salary-research` for the salary cell; whichever is
  implemented second adapts to the first.
