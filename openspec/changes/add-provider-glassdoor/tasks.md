## 1. Finish the study (logged out, scratch scripts only)

- [x] 1.1 Read every posting of one results page in a row with Escape for the modal; record how often it appears and whether a hard wall appears
- [x] 1.2 Pagination: how page 2 is reached and whether it stays open logged out
- [x] 1.3 `locId` for a country other than Peru through the site's own search box (no internal endpoints) — not reliable; owner chose the table plus a pasted URL
- [x] 1.4 Description completeness and the posting link to store
- [x] 1.5 Salary pages logged out (owner's addition)
- [x] 1.7 Scrapling (owner's addition), in a throwaway environment outside the project: headless search, second search in one session, "Show more jobs" beyond 30, posting page opened directly; results table next to Playwright's
- [x] 1.6 Owner chooses the route: Scrapling (2026-11-18); design revised (D1–D7)

## 2. Glassdoor reader

- [ ] 2.1 `core/readers/glassdoor.py`: search URL, country id (table, saved setting, `--search-url` saved once), card and show-more parsing, JSON-LD `JobPosting` to draft, plain text from HTML, window and seen handling (D3, D4, D5)
- [ ] 2.2 Scrapling adapter: `StealthySession` per call, "Show more" page action with Escape for the modal, posting pages, stop rules (D1, D2, D7)
- [ ] 2.3 Registry entry `glassdoor`; CLI `jt providers read … --search-url`; `INSTALL_HINTS["scrapling"]`; `docs/workspace-layout.md` (`provider-settings/`)
- [ ] 2.4 Tests with a fake fetcher and fictional pages: drafts, window, seen, duplicate, cap, site total, modal closed, modal that stays, unreadable posting skipped, three in a row stop, blocked, changed page, no results, country from table / saved setting / pasted URL (saved), bad URL refused, missing country

## 3. Salary reader

- [ ] 3.1 `jt providers salary glassdoor`: salary URL, JSON-LD distribution, sample size, newest report date, evidence draft (D6)
- [ ] 3.2 Tests with fictional salary pages: draft fields, monthly and yearly periods, no data, blocked
- [ ] 3.3 `job-search` skill: a provider's salary reader as one evidence source

## 4. Provider file

- [ ] 4.1 `providers/glassdoor.md`: `kind: both`, `regions: [global]`, `access: scrapling`, `dependencies: [scrapling]`, `max_results_per_query: 150`, `## Countries` id table (PE 189 peru), job and salary recipes, fields, terms risk, stop conditions, pitfalls, time per title

## 5. Real check and wrap-up

- [ ] 5.1 Real check: two titles and one salary page through the commands, headless; import with readings and store the evidence in a temporary home
- [ ] 5.2 `docs/backlog.md`: try Scrapling on the other providers (owner's note)
- [ ] 5.3 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-glassdoor --strict`
