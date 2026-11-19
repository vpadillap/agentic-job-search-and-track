## 1. Study (short)

- [x] 1.1 Captures of the Search and Applications tabs with demo data at 1,920, 1,440, 1,366, 1,280, 1,024, 768, and phone widths: sideways scroll, cut columns, row height, reaching the actions
- [x] 1.2 Results and captures in the proposal; D2–D4 confirmed or revised; the owner asked to implement every change directly (2026-11-19); the results are reported with the merge

## 2. Layout

- [x] 2.1 `app.css`: no table minimum width; flexible column widths with minimums; two-line wrap and ellipsis with the full text on hover (D2)
- [x] 2.2 Compact actions: icon buttons with labels and tooltips plus a "more" menu (D3); en/es
- [x] 2.3 `data-table.js`: column priorities, secondary columns in the detail below about 1,024 pixels, cards at phone width (D4)
- [x] 2.4 Search board: source in the job cell, short dates, two-line salary cell (coordinated with `rework-salary-research`)
- [x] 2.5 Applications board: the same treatment

## 3. Tests and wrap-up

- [x] 3.1 Browser tests at 1,366 and 1,280 (no sideways scroll, actions visible), 1,024 (columns in the detail), phone (cards); keyboard reaches every action
- [x] 3.2 Captures after the change in the proposal
- [x] 3.3 `ruff check .`, full `pytest`, privacy guard, `openspec validate improve-table-layout --strict`
