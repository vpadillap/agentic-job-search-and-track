## Context

The first-pass filter lives in `.claude/skills/job-search/batch-worker.md`
(since `job-search-live-results`): background helpers, or the main agent
without helpers, read it for every batch. Its table today says a posting
whose work mode is not stated is never excluded for work mode, and that
`location` applies to "onsite or hybrid outside the accepted locations".
The profile stores `work_modes` and `locations` (setup asks A4, the places
the user can commute to, only when hybrid or onsite is accepted). The CLI
validates only the reason code of a filter (`jt postings filter`); it does
not judge places. Captures already keep `location` as the site shows it
("Lima, Lima", "San Isidro, Lima, Perú").

## Goals / Non-Goals

**Goals:**
- The filter catches postings in other cities, including those that do not
  state the work mode.
- Districts count as part of their city; region names do not.
- No posting is lost to a doubt: unclear places are kept with a flag.

**Non-Goals:**
- Code that parses or geocodes places.
- Undoing a restore (the user can dismiss the posting instead).

## Decisions

### 1. The agent compares places; no code or stored gazetteer

The rule and its examples go in `batch-worker.md`; the agent resolves
"San Isidro" → Lima, "Huaral, Lima" → not Lima. The judgement is the same
kind it already makes for titles and seniority, and works for every
country the project covers.

- Alternative: a district → city table in the repository. Rejected: one
  table per country to keep up to date, and still blind to spelling
  variants and to workplaces named only in the description.
- Alternative: a check in `jt postings filter`. Rejected: the CLI would need
  the same gazetteer; it stays the validator of reasons.

### 2. "Not stated" means some presence for filtering only

The capture rules stay as they are (`work_mode: null` plus the "work mode
not stated" flag; never invented). Only the filter treats such a posting as
onsite/hybrid. So the panel still shows "Work mode not stated", and a user
correction (`jt postings work-mode`) keeps working.

- Alternative: write `onsite` into `work_mode`. Rejected: it would invent a
  fact the posting does not state.

### 3. Remote only → filter out (user decision)

The user chose to filter such postings out with reason `work_mode` and a
detail ("does not state that it is remote"), rather than keep them with a
flag. The detail makes the reason visible in the filtered-out list.

- Alternative: keep with a flag. Rejected by the user.

### 4. Doubts keep the posting

Only the country, no place, or another district inside a saved city → kept
with a flag (in the panel language), and the `conditions` score reflects the
doubt. A district list means "places I can reach", so a different district
of the same city is a doubt, not a clear violation.

- Alternative: exclude other districts. Rejected: a district list is often
  an example of where the user lives, and the filter only removes clear
  violations.

### 5. Where the workplace is read

The posting's `location` first; the description when it names the
workplace ("sede en Arequipa", "oficina en Miraflores"). When the two
disagree, the description wins and a flag says so, as for work-mode hints.

### 6. Restore turns the filtered result back into a new one

Restoring sets the posting's `run_results` row back to `outcome = 'new'`
(reason and detail cleared) and writes a posting event `filter_restored`
with the run, reason, and detail it had. No new table: the event marks the
posting as restored for good, and the board, the pending list, and the
history all read it. `jt postings filter` refuses a posting with that event
(`restored_by_user`), so neither a helper nor a later search can filter it
again, and `jt postings list` shows `restored: true` so the helper skips its
filter step. Core function, CLI command (`jt postings restore
<posting_id>…`, every filtered row of the posting), and panel endpoint (`POST /api/actions/restore-filtered`)
share one implementation, as dismiss/undismiss do.

- Alternative: a `restored` column on `run_results`. Rejected: a later
  search finds the posting again as `seen`, so the mark must belong to the
  posting, not to one run's row.
- Alternative: re-run the filter with the user's decision as a rule.
  Rejected: one restore is a correction, not a rule; lessons come from the
  learning loop.

### 7. Who scores a restored posting

While its run is `running`, nothing new is needed: the search's final check
(`job-search` step 5) queues every new posting without a score. Once the run
is finished, `jt pending` derives a `score` item (latest page, new outcome,
restored, no current score), and `/prepare-documents pending` handles it:
follow `batch-worker.md` job `score` for that posting (no filter step). The
pending chip in the panel already offers that one command.

- Alternative: score restored postings in the next `/job-search`. Rejected:
  the user would wait for a whole new search.
- Alternative: score immediately from the panel. Rejected: the panel never
  runs the agent.

### 8. Site chips: latest attempt wins, success time kept

`group_summary()` merges providers by run order instead of worst status: a
run's entry replaces the held one unless it is `disabled` or `skipped` with
reason `not_searched` (the site was not tried). `found` is still summed, and
each entry carries `last_searched_at`: the start of the latest run on the
page where the site's status was `ok`. A running run's `pending` entry
counts as an attempt, so the progress line of a running search stays right.
The chip shows the time next to the count, and a failure chip shows only
when the latest attempt failed.

- Alternative: keep worst-first and add a "fixed later" mark. Rejected: it
  tells the user about a problem that no longer exists.

## Risks / Trade-offs

- [A restored posting stays unscored if the user never runs the pending
  command] → the panel shows it as "–" and the pending counter shows it.
- [The agent misplaces a district] → the rule gives the examples and asks to
  keep the posting with a flag when unsure; the detail of each exclusion
  names the place, so the user can spot a wrong one in the filtered list and
  restore it.
- [Remote-only users lose postings that are remote but do not say so] →
  accepted by the user; the exclusion detail says why, they appear in the
  filtered-out list, and one click restores each.

## Migration Plan

Skill text only; no data migration. Earlier runs keep their results.
