## Why

In a real search on 2026-11-18, Glassdoor stopped on its first title with
reason `error` ("the page changed") and refused the 15 remaining titles of
the run. The cause was one results page that did not look like the others,
not a block and not a site-wide change. Every built-in reader has the same
rule: any `Stop("error")`, wherever it comes from, ends the provider for the
whole run. `common.finish` records the provider as `failed`, and
`common.context` (or Bumeran's own copy of it) then refuses every later title
with `provider_stopped`. So one odd results page, one posting without its
description, or one search that returns unreadable answers costs every other
title of that site.

A problem tied to one title's search is evidence about that title, not about
the site. A real layout change shows up on every title, so it can be told
apart cheaply: the same problem on two titles in a row.

## What Changes

In the built-in readers for LinkedIn, Indeed, Bumeran, Get on Board, and
Greenhouse:

- A **title problem** (a problem tied to one title's search: a results page
  that no longer has the data the reader expects, postings in a title whose
  description cannot be found, unreadable answers from the site's API) ends
  only that title. The postings already read for it are kept and imported as
  usual; the summary says what happened in a new `title_problem` field;
  `stopped` stays empty; the provider is not recorded as failed; the next
  title is read normally.
- One posting without its description is listed in `unreadable` with the
  reason and the title goes on. Two such postings in a row inside one title
  are a title problem.
- The provider still **stops for the rest of the run** (unchanged meaning of
  `stopped`, recorded as `failed`, later calls refused) on:
  - a hard block: the statuses, block, challenge, and sign-in pages each
    provider file already lists (reason `blocked`, unchanged);
  - a browser or network failure (reason `error`, unchanged);
  - the **same kind** of title problem on **two titles in a row** (reason
    `error`, the detail naming both titles): evidence of a real layout
    change. A title read without a problem resets the count. The count is
    kept in the run's `<provider>-state.json`, so it holds across separate
    reader calls.
- Provider files (`providers/<id>.md`): "Stop conditions" split into what
  ends a title and what stops the provider; the agent's steps say how to read
  `title_problem` (continue with the next title, name it in the report, add
  it to the `--detail` of the final `ok` record).
- `/job-search` step 6: a title that ended with a title problem is not a
  provider failure.

Not changed: what a block is for each provider, pacing, the cap per title,
the window, no-results handling (a results page with no results and no sign
of a problem is still "no postings for this title"), and Indeed's existing
rule that a sign-in or missing card data on a later variant only ends the
title.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `provider-linkedin`: "Pacing and stop conditions" (title problems end the
  title; two in a row stop) and "Posting fields from the posting page"
  (a posting without its description is unreadable, not a stop).
- `provider-indeed`: "Pacing and stop conditions" (missing card data on the
  first variant and missing description panels become title problems).
- `provider-bumeran`: "Pacing and stop conditions" (missing or malformed site
  data for a search, a missing later results page, a result without an id,
  and missing posting data become title or posting problems).
- `provider-getonbrd`: new requirement "Stop conditions per title" (three
  unreadable answers in a row end the title; network failures and the same
  problem on two titles in a row stop).
- `provider-greenhouse`: "Verbatim drafts and pacing" (same per-title rule as
  Get on Board for unreadable API answers).

## Overlaps

- **`fix-provider-glassdoor`** (proposed, not merged): Glassdoor is left out
  of this change on purpose; that change fixes the "limited or no results"
  page that caused the 2026-11-18 stop and adds salary pacing and cool-downs.
  Both touch `readers/common.py` only lightly (this change adds a helper;
  that one does not change `common.Stop` or `common.finish`), so they do not
  conflict. Moving Glassdoor onto the per-title rule afterwards is a
  follow-up for the Glassdoor change or a later one, not this change.
- **`retry-soft-blocks-and-browser-choice`** (proposed, not merged): owns
  throttling, HTTP 429, soft blocks, retries, cool-downs, and the browser
  choice. This change does not touch any of them: what is `blocked` stays
  exactly as it is, and no retry is added. Overlaps in code:
  - That change moves Bumeran off its own copy of `context`/state/lock/`Stop`
    onto `common.py`. This change implements the per-title rule in
    `common.py` and calls it from Bumeran's state; whichever lands second
    rebases (if the retry change lands first, Bumeran simply uses the common
    state; if this one lands first, the retry change carries the
    `title_problems` state key over).
  - Both modify the "Pacing and stop conditions" requirements of
    `provider-linkedin`, `provider-indeed`, and `provider-bumeran`; the
    second to be archived rebases its delta on the first.
  - If the retry change adds in-call retries for 5xx answers, the retried
    answer is what this change classifies; the two rules compose (retry
    first, then title problem).

## Impact

- Code: `src/jobtracker/core/readers/common.py` (a `title_problem` helper
  and state key), `linkedin.py`, `indeed.py`, `bumeran.py`, `getonbrd.py`,
  `greenhouse.py`. No database or CLI change: `jt run provider … --status ok
  --detail` already exists.
- Provider files: `providers/linkedin.md`, `indeed.md`, `bumeran.md`,
  `getonbrd.md`, `greenhouse.md` (agent steps and "Stop conditions").
- Skill: `.claude/skills/job-search/SKILL.md` step 6 (one sentence).
- Tests: the five reader test files gain per-title cases with their existing
  fake fetchers and browsers.
