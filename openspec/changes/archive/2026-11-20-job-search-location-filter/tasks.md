## 1. Restore in core, CLI, and API

- [x] 1.1 In `src/jobtracker/core/search.py`, add `restore_filtered(conn, posting_ids)`: the row goes back to `new` with reason and detail cleared, a posting event `filter_restored` keeps the run, reason, and detail; refuse a posting that is not filtered out; verify with the tests of 1.5
- [x] 1.2 Make `filter_postings` refuse a restored posting (`restored_by_user`), and add `restored: true|false` to `jt postings list` items; verify with the tests of 1.5
- [x] 1.3 Add `jt postings restore <posting_id>…` in `src/jobtracker/cli/main.py` and `POST /api/actions/restore-filtered` in `src/jobtracker/web/app.py` with `api.restoreFiltered` in `static/api.js`; verify with the tests of 1.5
- [x] 1.4 In `core/board.py`, derive a pending `score` item for restored, unscored, new postings of the latest page whose run is finished; in `core/insights.py`, list restores as filter corrections (reason, detail, site, date) in the history; verify with the tests of 1.5
- [x] 1.5 Tests (`tests/test_restore_filtered.py`): restore moves the posting back and records the event; filtering it again is refused; `postings list` marks it; a pending `score` item appears after the run is finished and not while it runs, and disappears once scored; the history lists the correction; verify `uv run pytest` on those files

## 2. Site chips with the latest result

- [x] 2.1 In `group_summary()` (`core/search.py`), merge each provider by run order (latest attempt wins; `disabled` and `skipped`/`not_searched` do not replace), keep `found` summed, and add `last_searched_at`; verify with the tests of 2.3
- [x] 2.2 In `boards/search.js`, show the time of `last_searched_at` on each searched site's chip (with en/es strings); verify with the browser test of 2.3
- [x] 2.3 Tests: failure then success on one page shows success with the later time; success then failure shows the failure and the earlier success time; a later search that did not try the site keeps its earlier result (`tests/test_search_groups.py`), and a browser test for the chip; verify they pass

## 3. Restore in the panel

- [x] 3.1 In `boards/search.js`, add a "Restore" button to each filtered-out posting that calls the endpoint and shows a message saying it will be scored with the pending work (or, during a running search, by the search); add `pending.kind.score` and the new strings to `locales/en.json` and `locales/es.json`; verify with the browser test of 3.2
- [x] 3.2 Browser tests: restoring from the filtered-out list moves the posting to the results without a score and shows the message; during a running search it shows "Scoring…"; the pending counter includes the score item after a finished search; verify `uv run pytest tests/test_browser.py`

## 4. Skills

- [x] 4.1 In `.claude/skills/job-search/batch-worker.md`, rewrite the `work_mode` and `location` rows and add the place rules (not stated = some presence unless concluded fully remote; remote only → `work_mode` with a detail; district → city, region ≠ city, workplace named in the description; doubts kept with a flag; remote never filtered for location), and say that a posting with `restored: true` is never filtered, only scored; verify with the tests of 4.4
- [x] 4.2 In `.claude/skills/job-search/scoring-guide.md`, say that `conditions` reflects a kept posting's place doubt; verify with the tests of 4.4
- [x] 4.3 In `.claude/skills/prepare-documents/SKILL.md`, handle pending `score` items: follow `batch-worker.md` job `score` for the posting, without filtering it; list them in the arguments table and the report; verify with the tests of 4.4
- [x] 4.4 Update `tests/test_job_search_skill.py` (the "never excluded" assertion replaced by the new rule; district, region, doubt, remote, and restored cases stated) and the prepare-documents skill test for the `score` item; verify `uv run pytest tests/test_job_search_skill.py tests/test_document_skills.py`

## 5. Documentation and release

- [x] 5.1 Update the README (en/es) where filtering is described to mention restoring; add the `CHANGELOG.md` entry at the top with the `Providers`, `Offers`, `Action` lines; verify `uv run pytest tests/test_docs.py tests/test_changelog.py`
- [x] 5.2 Run `uv run ruff check .`, `uv run pytest`, and `openspec validate job-search-location-filter --strict`; all pass
