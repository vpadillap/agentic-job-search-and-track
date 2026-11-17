## Context

Search: `RowDetail` in `boards/search.js` renders the description in
`.description` (`max-height: 250px; overflow-y: auto`) inside a three-column
grid. Applications: `ApplicationDetail` in `boards/applications.js` fetches
`/api/applications/{job}` (which includes `description`) but renders only the
documents, form, and "your application" cards; rows carry `posting.url` and
`posting.provider` but show no link. See proposal.md for the problem.

## Decisions

### P1. One description component for both tabs
`components/posting-description.js` exports `PostingDescription({ text, url,
provider, capturedAt })`: a panel with the heading, the verbatim text
(`white-space: pre-wrap`), and the link to the original posting. The text is
clamped to about 14 lines (`max-height` in `em`, `overflow: hidden`, a fade at
the bottom). After layout the component measures `scrollHeight >
clientHeight`; only then it shows a button "Read the full description",
which removes the clamp (`aria-expanded`); "Show less" restores it and keeps
the panel in view. No inner scroll bar in either state.

Alternatives: drop the clamp entirely (every expanded row becomes several
screens long and pushes the score and salary out of sight); a modal (hides
the rest of the row the user is comparing with); keep the scroll box but
taller (still a scroll inside a scroll, the reported problem).

### P2. Layout
Search: the description panel keeps its place as the first column; when
expanded it grows downward and the grid row grows with it (`align-items:
start` so the other cards keep their height).

Applications: the description panel spans the full width above the three
existing cards (a new grid row), so the documents, form, and details keep
their columns.

### P3. Link to the posting in Applications
In the job cell, under the company line: "Open posting · <site>" with the
external-link icon, `target="_blank" rel="noopener noreferrer"`, through the
existing `safeHref` check (a non-http URL renders no link). The description
panel's footer repeats it, as in the Search tab.

## Risks / Trade-offs

- [Measuring overflow before fonts load] → re-measure on `ResizeObserver` of
  the text element, so the button appears when the text actually overflows.
- [Very long descriptions when expanded] → the user chose to expand; the
  single toggle sits right below the text ("Show less" when open) and keeps
  focus and the panel in view when the text is collapsed again.
