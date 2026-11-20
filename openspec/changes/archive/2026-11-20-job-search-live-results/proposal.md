## Why

A search over many titles and job sites can take hours, mostly because sites
ask the agent to slow down. Today the agent searches every site first and
only then filters, scores, and prices what it found, so the panel stays
without usable results for the whole search and the user cannot start
reviewing postings in parallel.

## What Changes

- `/job-search` becomes a pipeline: the main agent keeps searching and
  importing, and each imported batch (one title on one site) is filtered and
  scored right away by background helper agents, so results reach the panel
  while the search goes on.
- The number of helper agents running at the same time is capped (3), and
  batches are sized so a search with many titles and sites cannot spawn
  more helpers than the cap. This keeps a large search from using up the
  user's usage limit before any helper finishes.
- Salary research runs in its own helper, one at a time, on postings already
  scored, so the same market or company is never researched twice in a run.
- A site cooling down after a throttle no longer holds anything up: the
  agent goes on with the other sites and titles while helpers keep scoring,
  and returns to that site when its cool-down ends, in the same run.
- Learning is refreshed once at the start of the run, so every helper uses
  the same rules and lessons.
- When background helpers are not available, the agent does the same work
  itself in the same order: each batch is filtered and scored right after
  its import, before the next one.
- The run stays open until every batch is filtered and scored and the salary
  queue is done; only then the agent finishes it and reports.
- Search board: while a search is running, new postings appear as soon as
  they are imported, marked "Scoring…", and a minimum-score filter does not
  hide them. The run summary shows the progress: sites done, postings scored
  out of new ones, and each site's cool-down with the time it resumes.
- The run summary given to the agent and the panel adds the count of new
  postings already scored.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `job-search`: results are filtered and scored per batch during the search,
  with a cap on concurrent helper agents; a cool-down does not block the
  other sites; the run is finished only when all batches are done.
- `search-results-board`: unscored postings of a running search are shown
  as "Scoring…" and are not hidden by the minimum-score filter; the run
  summary shows search and scoring progress.

## Non-goals

- Changing how any job site is accessed, its pacing, or its throttle rules
  (`provider-throttling` stays as it is).
- Changing the scoring rubric, the first-pass filter's rules, or salary
  evidence rules. The location filter is a separate, later change.
- Letting the panel start, pause, or control the agent.
- Making the cap a user setting.

## Impact

- `.claude/skills/job-search/SKILL.md` (pipeline, helper agents, cap,
  fallback); a new `.claude/skills/job-search/batch-worker.md` with the
  helper's instructions.
- `src/jobtracker/core/search.py`: `counts.scored` in the run and group
  summaries.
- `src/jobtracker/web/static/boards/search.js` and `locales/en.json`,
  `locales/es.json`: "Scoring…" rows and the progress line.
- Tests: `tests/test_search.py`, `tests/test_search_groups.py`,
  `tests/test_job_search_skill.py`, browser tests for the board.
- `CHANGELOG.md`, README (en/es) where the search is described.
