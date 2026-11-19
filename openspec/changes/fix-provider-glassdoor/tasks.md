## 1. Study

- [x] 1.1 The 2026-11-18 captures read (table in the proposal; captures stay private)
- [x] 1.2 Cause found: Glassdoor's "limited or no results" page, not a markup or browser change

## 2. Search results

- [x] 2.1 Page data decoded from the Next.js chunks; JSON-LD `ItemList`, cards, and links as fallbacks; "Similar jobs" never counted
- [x] 2.2 Ages from the page data used for the window
- [x] 2.3 `no_results` (empty page data, `lrp-zrp` notice, total 0) ends the title without an error
- [x] 2.4 An unreadable search page is loaded once more, then `title_problem` ends only the title; title problems never stop Glassdoor
- [x] 2.5 Two unreadable postings in a row end the title; an unparsable "Show more" response is counted, not a stop
- [x] 2.6 `site_may_have_changed` as in `end-title-on-page-error` (owner's rules, 2026-11-19)

## 3. Salary pages

- [x] 3.1 Pacing of 20 s across calls and the salary cool-down in `provider-settings/glassdoor.json`
- [x] 3.2 `Retry-After` (seconds or HTTP date); 15/30/60 minutes; reset after a page that loads
- [x] 3.3 Up to three titles per call (`--title` repeated), `tried` in the answer

## 4. Tests and docs

- [x] 4.1 Fictional saved pages in `tests/fixtures/glassdoor/` and tests for each source, no results, `title_problem`, the retry, the 429 handling, and variants
- [x] 4.2 `providers/glassdoor.md`, `docs/workspace-layout.md`, `.claude/skills/job-search/salary-guide.md`
- [x] 4.3 `ruff check .`, `pytest`, privacy guard, OpenSpec not installed on this machine: the delta was checked with a structural script
