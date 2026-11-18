## 1. Finish the study (logged out, visible browser, scratch scripts only)

- [ ] 1.1 Read every posting of one results page in a row with Escape for the modal; record how often it appears and whether a hard wall appears
- [ ] 1.2 Pagination: how page 2 is reached and whether it stays open logged out
- [ ] 1.3 `locId` for a country other than Peru through the site's own search box (no internal endpoints)
- [ ] 1.4 Description completeness and the posting link to store
- [ ] 1.5 Write the results into the proposal and design; owner approves before section 2

## 2. Glassdoor reader

- [ ] 2.1 `core/readers/glassdoor.py`: flight-data parsing, search URL (country id, title, `fromAge`, paging), fields and drafts (D1, D3)
- [ ] 2.2 Playwright adapter: visible Chromium, fresh context, click card, wait for the description, close the modal (D1, D2); stop rules (D4)
- [ ] 2.3 Registry entry `glassdoor`
- [ ] 2.4 Tests with a fake browser and fictional pages: drafts, window, seen, duplicate, paging, modal closed, modal that stays, blocked, changed page, no results

## 3. Provider file

- [ ] 3.1 `providers/glassdoor.md`: `regions: [global]`, access `playwright`, `dependencies: [playwright]`, recipe, fields, terms risk, stop conditions, pitfalls

## 4. Real check and wrap-up

- [ ] 4.1 Real check: one title, logged out, through the command; import with readings in a temporary home
- [ ] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-glassdoor --strict`
