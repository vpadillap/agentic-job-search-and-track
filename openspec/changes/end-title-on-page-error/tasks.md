## 0. Approval

- [ ] 0.1 Owner approves the proposal and design (in particular D2: two titles in a row, same kind) before section 1

## 1. Shared rule

- [ ] 1.1 `readers/common.py`: `TitleProblem(kind, detail)`, `SAME_PROBLEM_TITLES = 2`, `title_problem(ctx, state, summary, kind, detail)` (records the entry or raises `Stop("error")` naming both titles), state defaults `title_problems: []` and `last_title_kind: None` in `load_state`, reset of `last_title_kind` in `finish` only when the title read at least one results page cleanly (D2, Risks)
- [ ] 1.2 `title_problem: None` in every reader's summary
- [ ] 1.3 Tests in a shared helper test: first problem recorded; same kind on the next title stops with both titles in the detail; a different kind does not stop; a clean title resets; a no-results title does not reset; state survives between calls

## 2. Readers (one task each; each keeps its existing tests green)

- [ ] 2.1 LinkedIn: job ids without cards → `cards_without_data`; posting without description → unreadable, two in a row → `no_description`; network error and blocks unchanged
- [ ] 2.2 Indeed: first variant without card data → `no_card_data`; missing description panel → unreadable, two in a row → `no_description`; browser failure, blocks, and `ended_early` unchanged
- [ ] 2.3 Bumeran: `_Stop` aliased to `common.Stop`; no search data → `no_search_data`; wrong page number → `paging` (pages already read kept); results without an id skipped and counted, a page where none has one → `no_search_data`; missing posting data → unreadable, two in a row → `no_posting_data`; browser failure and blocks unchanged (coordinate with `retry-soft-blocks-and-browser-choice` if it has landed)
- [ ] 2.4 Get on Board: three unreadable answers in a row → `unreadable_answers`, unless all three had no status (stop); 403/429 unchanged
- [ ] 2.5 Greenhouse: same as 2.4; board memory still saved
- [ ] 2.6 Tests per reader with the existing fake fetchers/browsers: one bad title then a good one (both read, provider not failed, `title_problem` set on the first); two bad titles in a row (second stops, third refused with `provider_stopped`); one posting without description (unreadable, title continues); blocks and network failures still stop at once

## 3. Provider files and skill

- [ ] 3.1 `providers/linkedin.md`, `indeed.md`, `bumeran.md`, `getonbrd.md`, `greenhouse.md`: agent steps read `title_problem` (continue with the next title, note it); final `ok` record carries `--detail` with the titles that ended early; "Stop conditions" split into "Ends the title" and "Stops the provider"
- [ ] 3.2 `.claude/skills/job-search/SKILL.md` step 6: a title problem is not a provider failure; the report names the titles that ended early
- [ ] 3.3 `uv run ruff check .` and `uv run pytest`

## 4. Close

- [ ] 4.1 `/opsx:verify`, `/opsx:archive` (rebase the spec deltas on `retry-soft-blocks-and-browser-choice` if it was archived first), commit, merge into `main`
