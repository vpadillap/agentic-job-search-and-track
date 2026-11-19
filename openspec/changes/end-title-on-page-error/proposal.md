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
the site. Several titles in a row can also naturally have no results, so a
run of empty or odd titles is not proof of a site change either. The owner's
direction (2026-11-19): retry the title, and always work through all the
titles.

## What Changes

In the built-in readers for LinkedIn, Indeed, Bumeran, Get on Board, and
Greenhouse:

- **No results is never a problem.** A results page the site marks as
  empty is "no postings for this title", however many titles in a row have
  none. Each reader is checked against a real no-results capture so an empty
  page is not taken for a changed one (the Glassdoor 2026-11-18 failure).
- **Retry the title once.** When a title's results page (or API answer) does
  not have the data the reader expects, the reader waits the provider's
  pacing and loads that page once more in the same call.
- **Then end only that title.** If the retry fails too, it is a **title
  problem**: the title ends, the postings already read for it are kept and
  imported as usual, the summary says what happened in a new `title_problem`
  field, `stopped` stays empty, the provider is not recorded as failed, and
  the next title is read normally. **Title problems never stop the
  provider**, however many there are: every title of the run is tried.
- **Postings:** one posting without its description is listed in
  `unreadable` with the reason and the title goes on. Two in a row inside one
  title are a title problem (no retry: posting pages are opened once per run),
  so a changed posting page does not cost every posting of every title.
- **A likely site change is reported, not acted on.** When the same kind of
  title problem has happened on every title read so far in the run (two at
  least), the summary sets `site_may_have_changed`, and the agent says so in
  the report, so the owner can open a fix.
- The provider still **stops for the rest of the run** (unchanged meaning of
  `stopped`, recorded as `failed`, later calls refused) only on:
  - a hard block: the statuses, block, challenge, and sign-in pages each
    provider file already lists (reason `blocked`, unchanged);
  - a browser or network failure (reason `error`, unchanged).
- Provider files (`providers/<id>.md`): "Stop conditions" split into what
  ends a title and what stops the provider; the agent's steps say how to read
  `title_problem` and `site_may_have_changed` (continue with the next title,
  name them in the report, add them to the `--detail` of the final `ok`
  record).
- `/job-search` step 6: a title problem is not a provider failure.

Not changed: what a block is for each provider, pacing, the cap per title,
the window, and Indeed's existing rule that a sign-in or missing card data on
a later variant only ends the title.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `provider-linkedin`: "Pacing and stop conditions" (title problems are
  retried once, then end the title; never stop the provider) and "Posting
  fields from the posting page" (a posting without its description is
  unreadable, not a stop).
- `provider-indeed`: "Pacing and stop conditions" (missing card data on the
  first variant and missing description panels).
- `provider-bumeran`: "Pacing and stop conditions" (missing or malformed site
  data for a search, a missing later results page, results without ids, and
  missing posting data).
- `provider-getonbrd`: new requirement "Stop conditions per title"
  (unreadable answers end the title; only blocks and network failures stop).
- `provider-greenhouse`: "Verbatim drafts and pacing" (same rule as Get on
  Board).

## Overlaps

- **`fix-provider-glassdoor`** (proposed, not merged): Glassdoor is left out
  of this change on purpose; that change fixes the "limited or no results"
  page that caused the 2026-11-18 stop and adds salary pacing and cool-downs.
  This change only adds helpers to `readers/common.py` and does not change
  `common.Stop` or `common.finish`'s stop recording, so the two do not
  conflict. Moving Glassdoor onto the per-title rule afterwards is a
  follow-up, not this change.
- **`retry-soft-blocks-and-browser-choice`** (proposed, lands first): owns
  throttling, HTTP 429, soft blocks, their retries and cool-downs, and the
  browser choice. This change does not touch any of them: what is `blocked`
  stays as that change leaves it. The one retry added here is for a page
  whose content is not what the reader expects, not for a refused request.
  When that change has landed, the title retry goes through its
  throttle/retrier instead of a separate wait, so pacing stays in one place.
  Code overlaps:
  - It moves Bumeran off its own copy of `context`/state/lock/`Stop` onto
    `common.py`; this change is rebased on that and uses the common state.
  - Both modify the "Pacing and stop conditions" requirements of
    `provider-linkedin`, `provider-indeed`, and `provider-bumeran`; this
    change rebases its deltas on the archived ones.
  - If it retries 5xx answers, the retried answer is what this change
    classifies; the two compose (its retry first, then the title rule).

## Impact

- Code: `src/jobtracker/core/readers/common.py` (a `TitleProblem` exception,
  `retry_title` and `title_problem` helpers, a `title_outcomes` state key),
  `linkedin.py`,
  `indeed.py`, `bumeran.py`, `getonbrd.py`, `greenhouse.py`. No database or
  CLI change: `jt run provider … --status ok --detail` already exists.
- Provider files: `providers/linkedin.md`, `indeed.md`, `bumeran.md`,
  `getonbrd.md`, `greenhouse.md` (agent steps and "Stop conditions").
- Skill: `.claude/skills/job-search/SKILL.md` step 6 (one sentence).
- Tests: the five reader test files gain per-title, retry, and no-results
  cases with their existing fake fetchers and browsers.
