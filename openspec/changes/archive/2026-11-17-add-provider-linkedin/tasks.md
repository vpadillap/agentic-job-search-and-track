## 1. Verify the recipe against the live site

- [x] 1.1 Logged out, no cookies, at least 5 s apart, generic queries only: test `f_TPR`, `f_WT` (1, 2, 3), `f_JT` (F, P, C), `sortBy=DD`, `start=10/20`, free-text `location` vs `geoId`, and read the visitor filters from the `jobs/search` form; record per parameter whether it works (verified by the study table and L3 in design.md)
- [x] 1.2 Confirm the card selectors and the posting-page fields of design.md L5 on at least three postings, compare the guest detail endpoint with the public posting page, and check the canonical `/jobs/view/<id>/` link opens logged out (verified by the study in design.md)
- [x] 1.3 Record what a block looks like if observed; do not provoke one (verified: none in 27 requests; the stop conditions of L4 stay as written)

## 2. Job sites off by default

- [x] 2.1 In `providers.with_state`, a provider without a stored choice is disabled; update tests and fixtures that relied on the old default to enable providers explicitly (verified by new tests: a fresh workspace lists every provider disabled; `jt run start` marks them `disabled` and queries none; after `jt providers enable <id>` the run includes it; a stored "off" stays off)
- [x] 2.2 `/setup` step "Job sites": show each provider with access, login, live walk, and its terms note when present, and run `jt providers enable <id>` for each one picked instead of disabling the rest (verified by a new test in `tests/test_providers.py` asserting the setup skill says `jt providers enable` and no longer says `jt providers disable` for unwanted sites)
- [x] 2.3 `/job-search` step 2: when no provider is enabled, name the ones that exist and say they are turned on in `/setup` or the Search tab's job-site toggles, without turning any on (verified by the job-search skill test asserting this text)

## 3. Provider file

- [x] 3.1 Write `providers/linkedin.md` from `_template.md`: front matter (`access: http`, `requires_login: false`, `live_walk: false`, `dependencies: [curl]`, `max_results_per_query: 30`, `min_seconds_between_requests: 5`, `regions: [global]`, `last_verified: 2026-11-17`), and every section: access method and what is forbidden, search recipe with exact `curl` commands for the guest search and the posting page, the visitor filters only (L3), paging and stop rules, field mapping (L5), how the agent reads work mode and its detail from title and description (L6), form questions not visible, limits and terms-of-use risk, known pitfalls (sign-in pop-up markup, relevance order, ignored filters, guest detail's wrong seniority, 429/999, login redirects); verified by `python scripts/jt.py providers validate providers/linkedin.md` returning valid
- [x] 3.2 Check the file contains no personal data and no cookies or credentials (verified by `python scripts/check_private.py` passing with the file staged)
- [x] 3.3 Add a test that every provider file in the repository's `providers/` folder validates, and that `linkedin` lists `access: http` with no login and no live walk (verified by `pytest tests/test_providers.py`)

## 4. Dry run and docs

- [x] 4.1 With a temporary `JOBTRACKER_HOME` holding the fictional persona, run `jt providers enable linkedin`, then `/job-search days=7` for one title following only `providers/linkedin.md`; confirm postings import with id, canonical link, date, description, seniority, contract type, and work mode with its detail when stated (flag when not), captures are saved, and pacing is respected (verified by the run summary and `jt postings list`); then delete that temporary home
- [x] 4.2 Update README (status table, commands table, and Spanish section) and the AGENTS status: LinkedIn is the first available job site, read logged out (verified by reading the diffs)
- [x] 4.3 Run `ruff check .` and the full `pytest` suite, adjusting only tests that assumed the repository has no provider files or that providers start enabled (verified by both passing)
