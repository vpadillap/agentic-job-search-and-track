## 1. Scoring progress in the run summary

- [x] 1.1 Add `counts.scored` (new postings of the run with a current score) to `summary()` in `src/jobtracker/core/search.py` and sum it in `group_summary()`; verify with `uv run pytest tests/test_search.py tests/test_search_groups.py`
- [x] 1.2 Add tests: a running run with 3 new postings, 1 scored, reports `scored: 1`; a group of two runs adds them up; verify the new tests pass

## 2. Search board while a search runs

- [x] 2.1 In `src/jobtracker/web/static/boards/search.js`, show "Scoring…" in the score column for an unscored new posting when the displayed run or group is `running`, and a dash otherwise; verify in the browser test of 2.4
- [x] 2.2 Let the minimum-score filter keep unscored rows while the run is running, and count them as not hidden; verify in the browser test of 2.4
- [x] 2.3 Add the progress line to the run summary (sites done of searched, scored of new, each cooling site with its resume time) and the strings to `locales/en.json` and `locales/es.json`; verify `uv run pytest tests/test_api.py` and the locale key tests pass
- [x] 2.4 Add browser tests: running run with an unscored posting shows "Scoring…" and stays visible under a minimum score; after the posting is scored the next refresh shows its score; a finished run shows a dash; the progress line shows the counts and the resume time; verify `uv run pytest tests/test_browser.py`

## 3. Job-search skill as a pipeline

- [x] 3.1 Write `.claude/skills/job-search/batch-worker.md`: what a scoring helper reads, how it filters and scores its posting ids, what it reports back (scored ids, `no_resume_for_language` postings), and the salary helper's section; verify it names only existing `jt` commands (`uv run pytest tests/test_job_search_skill.py`)
- [x] 3.2 Rework `.claude/skills/job-search/SKILL.md`: learning refresh right after `run start`; a queue of imported batches; background helpers capped at 3 at once (at most 1 for salary), each taking every waiting batch up to 25 postings; cool-downs handled by going on with other sites and returning after `resume_after`; the fallback without background helpers; the run finished only when the queue, helpers, and salary are done, with a final check that queues unscored new postings once more; verify with the skill tests of 3.3
- [x] 3.3 Extend `tests/test_job_search_skill.py` to check the skill states the cap of 3, the 25-posting batch size, the refresh at the start, the fallback, and that `batch-worker.md` is referenced; verify the tests pass

## 4. Documentation and release

- [x] 4.1 Update the README (en/es) where the search is described: results appear in the panel while the search runs; verify `uv run pytest tests/test_docs.py`
- [x] 4.2 Add the `CHANGELOG.md` entry at the top with the `Providers`, `Offers`, `Action` lines; verify `uv run pytest tests/test_changelog.py`
- [x] 4.3 Run `uv run ruff check .`, `uv run pytest`, and `openspec validate job-search-live-results --strict`; all pass
