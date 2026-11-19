## 0. Approval

- [x] 0.1 Owner approves the proposal and design (in particular D3: one retry per title; D4: title problems never stop the provider) before section 1 (2026-11-19)
- [ ] 0.2 Rebase on `main` after `retry-soft-blocks-and-browser-choice` is merged (it lands first and touches the same readers)

## 1. Shared rule

- [ ] 1.1 `readers/common.py`: `TitleProblem(kind, detail)`, `TITLE_RETRIES = 1`, `title_problem(ctx, state, summary, kind, detail)` (records the entry, never stops), `title_problems: []` state default in `load_state`, `site_may_have_changed` from that list (D4: same kind on every title that read anything, two at least; no-results titles left out)
- [ ] 1.2 `title_problem: None`, `site_may_have_changed: False`, `retries: 0` in every reader's summary
- [ ] 1.3 Tests: problem recorded and provider not failed; next call reads normally; three title problems in a row still leave the provider open; `site_may_have_changed` set only for the same kind on every title that read anything; no-results titles do not count; state survives between calls

## 2. Readers (one task each; each keeps its existing tests green)

- [ ] 2.1 LinkedIn: job ids without cards → retry once, then `cards_without_data`; posting without description → unreadable, two in a row → `no_description`; network error and blocks unchanged
- [ ] 2.2 Indeed: first variant without card data → retry once, then `no_card_data`; missing description panel → unreadable, two in a row → `no_description`; browser failure, blocks, and `ended_early` unchanged
- [ ] 2.3 Bumeran (on `common`, after the retry change): no search data → retry once, then `no_search_data`; wrong page number → retry once, then `paging` (pages already read kept); results without an id skipped and counted, a page where none has one → retry once, then `no_search_data`; missing posting data → unreadable, two in a row → `no_posting_data`; browser failure and blocks unchanged
- [ ] 2.4 Get on Board: each unreadable answer retried once; three in a row → `unreadable_answers`, unless all three had no answer (stop); 403/429 unchanged
- [ ] 2.5 Greenhouse: same as 2.4; board memory still saved
- [ ] 2.6 No results (D2): for LinkedIn, Indeed, Bumeran, Get on Board, and Greenhouse, a fictional fixture built from a real no-results capture is read as "no postings", with no retry and no title problem; several such titles in a row leave the provider open
- [ ] 2.7 Tests per reader with the existing fake fetchers/browsers: a bad page that reads on retry (title continues, `retries` = 1); a bad page twice (title problem, provider open, next title read); one posting without description (unreadable, title continues); blocks and network failures still stop at once

## 3. Provider files and skill

- [ ] 3.1 `providers/linkedin.md`, `indeed.md`, `bumeran.md`, `getonbrd.md`, `greenhouse.md`: agent steps read `title_problem` and `site_may_have_changed` (continue with the next title, note them); final `ok` record carries `--detail` with the titles that ended early; "Stop conditions" split into "Ends the title" and "Stops the provider"
- [ ] 3.2 `.claude/skills/job-search/SKILL.md` step 6: a title problem is not a provider failure; the report names the titles that ended early and a probable site change
- [ ] 3.3 `uv run ruff check .` and `uv run pytest`

## 4. Close

- [ ] 4.1 `/opsx:verify`, `/opsx:archive` (deltas rebased on the archived `retry-soft-blocks-and-browser-choice`), commit, merge into `main`
