## 1. Finish the study (logged out, visible browser, scratch scripts only)

- [x] 1.1 Read every posting of one results page in a row with Escape for the modal; record how often it appears and whether a hard wall appears
- [x] 1.2 Pagination: how page 2 is reached and whether it stays open logged out
- [x] 1.3 `locId` for a country other than Peru through the site's own search box (no internal endpoints) — not reliable; owner chose the table plus a pasted URL
- [x] 1.4 Description completeness and the posting link to store
- [x] 1.5 Salary pages logged out (owner's addition)
- [x] 1.7 Scrapling (owner's addition), in a throwaway environment outside the project: headless search, second search in one session, "Show more jobs" beyond 30, posting page opened directly; results table next to Playwright's
- [ ] 1.6 Owner approves the study results and the revised design before section 2

## 2. Glassdoor reader

- [ ] 2.1 `core/readers/glassdoor.py`: search URL and country id (table, `--search-url`), flight-data and JSON-LD parsing, fields and drafts, 30 cap and cut-off note (D3, D4)
- [ ] 2.2 Playwright adapter: visible Chromium, new context per search, click card, wait for the description, close the modal (D1, D2); skipped postings; stop rules (D6)
- [ ] 2.3 Registry entry `glassdoor`; CLI `--search-url`
- [ ] 2.4 Tests with a fake browser and fictional pages: drafts, window, seen, duplicate, 30 cap, modal closed, modal that stays, description that never loads, blocked, changed page, no results, country from table and from a pasted URL, bad URL refused

## 3. Salary reader

- [ ] 3.1 `jt providers salary glassdoor`: salary URL, JSON-LD distribution, sample size, newest report date, evidence draft (D5)
- [ ] 3.2 Tests with fictional salary pages: draft fields, monthly and yearly periods, no data, blocked
- [ ] 3.3 `job-search` skill: how to use a provider's salary reader as one evidence source

## 4. Provider file

- [ ] 4.1 `providers/glassdoor.md`: `kind: both`, `regions: [global]`, access `playwright`, `dependencies: [playwright]`, `max_results_per_query: 30`, country id table (PE 189), job and salary recipes, fields, terms risk, stop conditions, pitfalls

## 5. Real check and wrap-up

- [ ] 5.1 Real check: two titles and one salary page, logged out, through the commands; import with readings and store the evidence in a temporary home
- [ ] 5.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-glassdoor --strict`
