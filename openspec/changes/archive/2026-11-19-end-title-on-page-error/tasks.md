## 0. Approval

- [x] 0.1 Owner approves the proposal and design (in particular D3: one retry per title; D4: title problems never stop the provider) before section 1 (2026-11-19)
- [x] 0.2 Rebase on `main` after `retry-soft-blocks` is merged (it landed first and touches the same readers); deltas rebuilt on its archived requirement texts

## 1. Shared rule

- [x] 1.1 `readers/common.py`: `TitleProblem(kind, detail)`, `TITLE_RETRIES = 1`, `POSTING_PROBLEMS_IN_A_ROW = 2`, `retry_title(step, summary)`, `title_problem(summary, problem)` (never stops), `title_outcomes: []` state default in `load_state`, `site_may_have_changed` computed in `finish` (D4: same kind on every title that read anything, two at least; no-results titles left out)
- [x] 1.2 `title_problem: None`, `site_may_have_changed: False`, `title_retries: 0` in every reader's summary (set by `finish` and `done_summary` too)
- [x] 1.3 Tests (in the LinkedIn reader tests, which exercise the shared code): problem recorded and provider not failed; next call reads normally; three title problems in a row still leave the provider open; `site_may_have_changed` false on the first, true from the second; no-results titles do not count

## 2. Readers (one task each; each keeps its existing tests green)

- [x] 2.1 LinkedIn: job ids without cards → retry once, then `cards_without_data`; posting without description → unreadable, two in a row → `no_description`; network error and blocks unchanged
- [x] 2.2 Indeed: first variant without card data → retry once, then `no_card_data`; missing description panel → unreadable, two in a row → `no_description`; browser failure, blocks, and `ended_early` unchanged
- [x] 2.3 Bumeran: no search data → retry once, then `no_search_data`; wrong page number → retry once, then `paging` (pages already read kept); results without an id skipped and counted (`without_id`), a page where none has one → retry once, then `no_search_data`; missing posting data → unreadable, two in a row → `no_posting_data`; browser failure and blocks unchanged
- [x] 2.4 Get on Board: each unreadable answer retried once; three in a row → `unreadable_answers`, unless none of the three had an answer (stop); 403 and throttling unchanged
- [x] 2.5 Greenhouse: same as 2.4; board memory still saved
- [x] 2.6 No results (D2): LinkedIn (empty guest page), Bumeran (empty `content`), Get on Board (empty `data`), and Greenhouse (nothing matching) read as "no postings" with no retry and no title problem, in the shapes the real sites answer. Indeed: no real no-results capture exists yet (none in any past run); if Indeed's empty page turns out to lack job-card data, it costs one retry and a title problem per empty title, never the provider. Check it on the next real run that has an empty Indeed title.
- [x] 2.7 Tests per reader with the existing fake fetchers/browsers: a bad page that reads on retry (`title_retries` = 1); a bad page twice (title problem, provider open, next title read); one posting without description (unreadable, title continues); two in a row (title problem); blocks and network failures still stop at once

## 3. Provider files and skill

- [x] 3.1 `providers/linkedin.md`, `indeed.md`, `bumeran.md`, `getonbrd.md`, `greenhouse.md`: agent steps read `title_problem` and `site_may_have_changed` (continue with the next title, note them); final `ok` record carries `--detail` with the titles that ended early; "Stop conditions" gain a "Title problems" part and lose the old "page no longer matches" stop
- [x] 3.2 `.claude/skills/job-search/SKILL.md` step 6: a title problem is not a provider failure; the report names the titles that ended early and a probable site change
- [x] 3.3 `uv run ruff check .` and `uv run pytest`

## 4. Close

- [x] 4.1 `/opsx:verify`, `/opsx:archive`, commit, merge into `main` (archived by hand: the OpenSpec CLI is not installed here)
