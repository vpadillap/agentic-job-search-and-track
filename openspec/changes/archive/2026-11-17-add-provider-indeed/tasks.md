## 1. Shared reader parts

- [x] 1.1 `core/readers/common.py`: run context checks, per-provider state, pacing, lock, seen records, drafts file, stop recording (D2)
- [x] 1.2 `core/readers/linkedin.py` uses it; its tests pass unchanged

## 2. Indeed reader

- [x] 2.1 `core/readers/indeed.py`: job-card JSON parsing, search URL (site, `fromage`, location, paging), fields and drafts (D3, D4)
- [x] 2.2 Playwright adapter: visible Chromium, fresh context, click card, read the panel; stop rules (D1, D5)
- [x] 2.3 Registry entry `indeed`
- [x] 2.4 Tests with a fake browser and fictional pages: drafts, window, seen, duplicate, paging, blocked, sign-in page, changed page, no results

## 3. Provider file and doctor

- [x] 3.1 `providers/indeed.md`: access `playwright`, `dependencies: [playwright]`, recipe, fields, terms risk, stop conditions, pitfalls
- [x] 3.2 `core/doctor.py` checks only providers the user turned on; tests

## 4. Real check and wrap-up

- [x] 4.1 Real check: one title, logged out, through the command; import with readings in a temporary home
- [x] 4.2 README/AGENTS status, `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-indeed --strict`
