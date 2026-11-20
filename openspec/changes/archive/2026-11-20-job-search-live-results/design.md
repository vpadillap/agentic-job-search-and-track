## Context

`/job-search` (`.claude/skills/job-search/SKILL.md`) runs its steps in strict
order: search every provider (step 3), then filter (4), refresh learning and
score (5), research salary (6), finish and report. Postings are written to the
database as each provider is imported, and the panel polls for changes every
3 seconds, but scoring only starts after the last provider. A throttled
provider can keep the run open for 15–30 minutes per cool-down
(`provider-throttling`). The board's minimum-score filter hides rows without a
score (`boards/search.js`), so an active default minimum hides everything
until scoring starts.

The database is SQLite in WAL mode with a busy timeout (`core/db.py`), so
several CLI processes may write at the same time; every write already goes
through `jt` (`postings filter`, `score set`, `salary …`), which are per
posting and independent of each other.

## Goals / Non-Goals

**Goals:**
- Results usable in the panel minutes after the search starts.
- A bounded cost: the number of helper agents in flight is capped, and a run
  with many titles and sites does not create one helper per batch.
- The same behavior, slower, for agents without background helpers.

**Non-Goals:**
- New CLI commands for queuing or locking; the queue lives in the main
  agent's working memory for the run.
- Any change to provider readers, pacing, or cool-down rules.

## Decisions

### 1. Batch = one title on one provider; helpers drain the queue

The main agent imports per provider and title (it already does), and appends
each import's new posting ids to a queue. A helper, when started, takes
**every batch waiting in the queue, up to 25 postings**, not just one batch.
So the number of helpers started in a run grows with the postings found, not
with titles × sites.

- Alternative: one helper per batch. Rejected: 10 titles × 6 sites = 60
  helpers, each re-reading the resume, profile, history, and scoring guide;
  that is the usage blow-up the user warned about.
- Alternative: one helper per provider. Rejected: a provider with many
  titles would finish its batch only at its end, which is what we are fixing.

### 2. A hard cap of 3 concurrent helpers, salary in at most one of them

At most 3 background helpers run at once in a run: up to 3 scoring helpers,
or 2 scoring + 1 salary helper. The salary helper takes scored postings at or
above the minimum, best first, within the existing 15-per-run limit, and runs
alone so each market key and company is researched once (the de-duplication
`salary-guide.md` asks for stays in one place). When the cap is reached, new
batches wait; a helper's completion notification frees a slot and the main
agent starts the next helper if the queue is not empty.

- Alternative: a cap based on the number of titles/providers. Rejected: the
  cost problem grows with that number, so the cap must not.
- Alternative: user-configurable cap. Rejected for now (Non-goal); 3 is a
  constant named in the skill and easy to revisit.
- Alternative: salary research inside each scoring helper. Rejected: two
  helpers would research the same market key in parallel.

### 3. Helper instructions in their own file

A new `.claude/skills/job-search/batch-worker.md` holds what a helper does:
read the active rules, profile, resume, the history file from the run's
start-of-run refresh, and `scoring-guide.md`; filter its postings
(`jt postings filter`, flags); score the rest (`jt score set … --run`);
report the ids it scored and any `no_resume_for_language` postings back to
the main agent. A salary section covers the salary helper. The main agent
passes the run id, the posting ids, and the refreshed learning summary in the
helper's prompt. `SKILL.md` keeps the orchestration and the fallback.

- Alternative: helpers load the whole `SKILL.md`. Rejected: they would also
  read the search steps, costing tokens and risking a helper that searches.

### 4. Learning refreshed once, at the start

`jt learning refresh` moves from step 5 to the start of the run (after
`run start`). `rules-and-lessons` only requires it before the first score,
which still holds. Helpers read the history file it wrote and may call
`jt learning refresh --posting <id>` (read-only ordering) as today.

- Alternative: refresh per batch. Rejected: a refit in the middle of a run
  could score batches with different estimates.

### 5. Cool-downs: keep working, come back

When a reader answers `throttled`, the main agent marks that provider as
"come back after `resume_after`" and goes on with the remaining providers and
the queue. When nothing else is left, it asks the user (as today) whether to
wait; if yes, it waits for the earliest `resume_after` and resumes there in
the same run; if no, it finishes the run once the queue and helpers are done.

### 6. Fallback without helpers

If the agent has no background-agent tool, it processes the queue itself
after every import, in the same order (filter, score), and runs salary
research between providers or during a cool-down wait. Same results, no
parallelism.

### 7. Panel: "Scoring…" and progress from the existing summary

`summary()` adds `counts.scored` (new postings of the run with a current
score); `group_summary()` sums it like the other counts. The board already
polls and already shows running runs and provider cool-downs
(`cooldown_until`). It adds:
- in the score column, "Scoring…" for an unscored new posting when the run
  (or its group) is `running`, a dash otherwise;
- the minimum-score test lets those rows through while running;
- the summary's progress line: providers done (status not `pending`) out of
  providers searched, `scored` of `new`, and each cooling provider with
  its resume time.

- Alternative: a new "scoring" state stored per posting. Rejected: "has no
  score and the run is running" already says it, with no new data to keep in
  sync.

## Risks / Trade-offs

- [Helpers writing at the same time] → WAL plus the busy timeout already
  serialize writes; each helper owns distinct posting ids, so no two helpers
  write the same row.
- [A helper fails or stops mid-batch] → the main agent lists the run's new
  postings without a score (`jt postings list --run … --outcome new` plus
  score) before finishing and queues them again, once.
- [Postings reordered on the board while the user reads it] → rows only
  gain a score; sorting by score moves them, which is the expected effect of
  scoring. The detail panel of an open row stays open.
- [Cost still high on very large searches] → bounded by the cap and the
  25-posting batches; the number of helpers is about new postings ÷ 25.

## Migration Plan

No data migration: `counts.scored` is computed. Rollback is reverting the
skill and panel files.
