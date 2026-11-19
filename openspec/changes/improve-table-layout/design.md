## Context

`components/data-table.js` renders both boards' tables from column
definitions (`key`, `label`, `width`, `render`); `.results { overflow-x:
auto }` and `.table { min-width: 1300px }` make the table scroll sideways
below 1,300 pixels. Search columns: score, job, conditions, salary, published,
source (120 px), actions (250 px). Applications: score, job, status and tags,
documents (190 px), applied, asked/suggested (160 px), next step.

## Goals / Non-Goals

**Goals:** every column readable without sideways scroll from 1,280 pixels;
actions one click away; usable on a narrow window and a phone.

**Non-Goals:** changing what each column means; new data; a redesign of the
other tabs.

## Decisions

### D1. Study first

Captures at the widths in the proposal decide the column order, the
breakpoints, and which columns move into the detail. D2–D4 are the expected
shape.

### D2. Column widths (expected)

No table minimum width. Each column gets a minimum and a share of the free
space (job and conditions grow; score, date, and actions stay narrow). Text
that does not fit wraps to at most two lines; longer text is cut with an
ellipsis and shown whole on hover and in the detail.

### D3. Actions (expected)

Icon buttons (track, dismiss, open the original posting) with
`aria-label` and tooltip, plus a "more" menu for the rest; the column is about
120 pixels. Keyboard order and focus are kept.

### D4. Narrow widths (expected)

`data-table.js` takes a priority per column. Below about 1,024 pixels, columns
with low priority are hidden from the row and shown in the row's detail; at
phone width the row renders as a card (title, company, score, salary,
actions). The same component serves both boards.

## Risks / Trade-offs

- [Hidden columns are missed] → They are in the detail, which every row
  already has; the column chooser is not needed.
