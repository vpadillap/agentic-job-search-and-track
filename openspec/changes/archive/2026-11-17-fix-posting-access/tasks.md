## 1. Description component

- [x] 1.1 `components/posting-description.js` as in design P1 (clamp, overflow measurement with `ResizeObserver`, "Read the full description"/"Show less" with `aria-expanded`, link footer through `safeHref`), CSS without an inner scroll bar, locale strings en/es (verified by the browser tests in 2.x)

## 2. Boards

- [x] 2.1 Search: `RowDetail` uses the component; the other cards keep their height (verified by a browser test: a long description shows the button, expanding shows the last line of the text, the description element has no inner scroll)
- [x] 2.2 Applications: full-width description panel above the cards in the expanded row (verified by a browser test: expanding an application shows its description and the full text after "Read the full description")
- [x] 2.3 Applications: "Open posting · <site>" link in each row and in the description footer, new tab, `noopener` (verified by a browser test checking `href`, `target`, and `rel`)

## 3. Wrap-up

- [x] 3.1 Remove the two fixed entries from `docs/backlog.md` (verified by reading the diff)
- [x] 3.2 `ruff check .` and the full `pytest` suite with browser tests (verified by both passing, no browser test skipped)
