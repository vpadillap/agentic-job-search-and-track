## Context

Every built-in reader raises `common.Stop(reason, detail)` (Bumeran: its own
`_Stop`) for anything unexpected. The reader's `_read` catches it, puts it in
`summary["stopped"]`, and `common.finish` records the provider `failed` for
the run. The next call for another title then fails in `common.context` with
`provider_stopped`. The rule does not distinguish a block (the site refuses
us: stopping is right) from a page that did not look as expected for one
title (stopping costs every other title).

The owner's direction (2026-11-19): retry the title, and always work through
all the titles, since two or three titles in a row can naturally have no
results.

Where each reader raises `Stop("error")` today:

| Reader | Site | Today | This change |
|---|---|---|---|
| LinkedIn | search page has job ids but no cards | stop | retry once, then title problem `cards_without_data` |
| LinkedIn | posting page without its description | stop | posting unreadable; two in a row in a title → title problem `no_description` |
| LinkedIn | network error | stop | unchanged (stop) |
| LinkedIn | other HTTP status (not 200, 3xx, 429, 999, the unreadable 404/410) | stop | unchanged (see D6) |
| Indeed | first variant has no job-card data | stop | retry once, then title problem `no_card_data` |
| Indeed | a chosen posting shows no description panel | stop | posting unreadable; two in a row in a title → title problem `no_description` |
| Indeed | browser fails | stop | unchanged (stop) |
| Bumeran | search page sends no readable data in 30 s | stop | retry once, then title problem `no_search_data` |
| Bumeran | page N is not page N | stop | retry once, then end the title after the pages already read: title problem `paging` |
| Bumeran | a result without an id | stop | that result is skipped and counted; a page where no result has an id → retry once, then `no_search_data` |
| Bumeran | posting page sends no data / no `aviso` | stop | posting unreadable; two in a row in a title → title problem `no_posting_data` |
| Bumeran | browser cannot load a page | stop | unchanged (stop) |
| Get on Board | 3 unreadable API answers in a row | stop | each unreadable search answer retried once; 3 in a row → title problem `unreadable_answers`, unless all were network failures (stop) |
| Greenhouse | 3 unreadable API answers in a row | stop | same as Get on Board |

Glassdoor is not in the table: `fix-provider-glassdoor` owns its reader.

## Goals / Non-Goals

**Goals:** one bad title costs at most that title; every title of the run is
tried; a probable site change is visible in the report; empty titles are
never mistaken for a problem.

**Non-Goals:** retries for throttling, 429, soft blocks, cool-downs (all
`retry-soft-blocks-and-browser-choice`); Glassdoor
(`fix-provider-glassdoor`); changing what counts as a block; private readers
(they keep their own rules; `common` helpers are available to them).

## Decisions

### D1. Three outcomes, not two

A reader call ends in one of:

1. **normal end** (results exhausted, cap, window, no results);
2. **title problem**: `summary["title_problem"] = {"kind", "detail"}`,
   `summary["stopped"] = None`, the provider stays `pending`/`ok`, the drafts
   and seen postings gathered before the problem are written and imported as
   usual;
3. **stop**: `summary["stopped"] = {"reason", "detail"}` as today, recorded
   `failed`, later calls refused. Only for blocks and browser or network
   failures.

`title_problem` and `site_may_have_changed` are new summary keys present
(`null` / `false`) in every summary so the agent can always read them.
Indeed's existing `ended_early` (a later variant shows a sign-in page or no
card data) is unchanged: it is a normal end, since the first variant already
proved the layout and the access.

### D2. No results is not a problem

Every reader already treats a results page with no results as "no postings
for this title". This change makes it a stated requirement and a test per
reader with a real no-results capture (anonymized into the fictional
fixtures), because the 2026-11-18 Glassdoor stop was exactly an empty page
taken for a changed one. Where a reader cannot tell "empty" from "changed"
with certainty, it treats the page as empty when the site's own no-results
marker is present, and as a title problem only when neither results nor that
marker are there.

### D3. Retry the title's page once, then end the title

When a results page (or API search answer) lacks the data the reader
expects, the reader waits the provider's pacing (`min_seconds`, or the
retry change's throttle once it exists) and loads the same page once more in
the same call. If the retry reads cleanly the title continues as if nothing
happened (the summary counts `retries`). If not, it raises
`common.TitleProblem(kind, detail)`, which `_read` catches next to `Stop`.

One retry, not more: a page that is wrong twice in a row, 5+ seconds apart,
is unlikely to fix itself in the same call, and each retry costs a paced
request on a site that may be watching volume.

### D4. Title problems never stop the provider

`common.title_problem(ctx, state, summary, kind, detail)` records
`{"title", "kind", "detail"}` in `state["title_problems"]` (the run's
`<provider>-state.json`) and sets `summary["title_problem"]`. It never
raises `Stop`. The next call reads the next title normally, whatever came
before: three titles in a row with nothing are three titles with nothing.

`site_may_have_changed` is set when this title and every earlier title of
the run that read anything ended with the same `kind` (two titles at least).
Titles with no results are left out of that test (they are neither evidence
for nor against). It is information for the agent and the user (the report
names it, so the owner can open a fix), not a stop.

The cost of a real layout change is bounded: one search page plus one retry
per remaining title, at the provider's pace (for 15 titles at 5 s, under
three minutes of requests), instead of losing every title to one odd page.

### D5. Postings without a description are a posting problem first

Today one LinkedIn posting page without its description stops LinkedIn for
the run. A single removed or oddly built posting is common; a layout change
affects every posting. So:

- one posting whose description (or Bumeran posting data) is missing → it is
  listed in `unreadable` with the reason, its id is still marked handled (as
  today: it is not opened again in the run), and the title continues;
- two in a row in the same title → title problem `no_description` (Bumeran:
  `no_posting_data`), which follows D4. No retry: posting pages are opened
  once per posting per run.

A posting read successfully resets the in-title count.

### D6. API readers

Get on Board and Greenhouse already tolerate up to two unreadable answers in
a row within a call. Each unreadable answer is now retried once (D3) before
it counts. When the count reaches three:

- if every one of them had no HTTP status (the request itself failed:
  `OSError`, timeout), it is a network failure → `Stop("error")` as today;
- otherwise → title problem `unreadable_answers` with the last URL and
  status.

For Greenhouse a title's work spans several boards; the title problem ends
the title's remaining boards and postings, and the board memory
(`save_settings`) is saved as today (the `finally` already does it).

### D7. What stays a stop (and why)

- Blocks: unchanged per provider file (`blocked`), and as the retry change
  leaves them.
- Browser or network failure: the session or connection is broken; the next
  title would fail the same way.
- LinkedIn's "other HTTP status" (for example a 5xx or 400 on a search):
  left as a stop here. A 5xx is the territory of the retry change (it may
  retry before deciding); a 4xx for a specific query was never seen. Reopen
  if it happens.
- Indeed: a block or sign-in page on the first variant of a title stays a
  block (unchanged).

### D8. Where the code goes

- `common.py`: `TitleProblem(kind, detail)`, `title_problem(...)`, the
  `title_problems` state default in `load_state`, and
  `site_may_have_changed` computed from that list. `Stop` and the stop
  recording in `finish` are unchanged.
- Bumeran: rebased on the retry change, which moves it onto `common`; it
  then uses the common state and `Stop`.
- Each reader wraps its search-page load in a small "load, check, retry
  once" step and catches `TitleProblem` in the same `try` as `Stop`.

### D9. What the agent and the user see

- Provider files, step "read the summary": `title_problem` and
  `site_may_have_changed` are named with `stopped`; a new step says: if
  `title_problem` is set, import what was written, go on with the next title,
  and remember it for the report.
- The final record for a provider with title problems:
  `jt run provider <run_id> <id> --status ok --detail "<n> titles ended
  early: <title> (<kind>), …"`, plus "the site may have changed" when the
  last summary said so.
- `/job-search` step 6: one sentence that a title problem is not a provider
  failure; the report names the titles that ended early.

## Risks / Trade-offs

- **A real layout change costs every remaining title's two requests.**
  Accepted (D4): bounded, paced, and reported; the owner preferred trying
  every title.
- **An empty page mistaken for a changed one** would now cost a retry per
  title instead of the provider. D2's per-reader no-results test guards it.
- **Two changes' state in flight.** The retry change also adds state keys
  (cool-downs). Distinct key names; no conflict.
- **Agents that ignore `title_problem`.** Harmless: the provider is still
  open, the next call works; only the report loses the note. The provider
  files make it explicit.

## Migration Plan

No data migration: state files are per run and `load_state` supplies the
default for the new key. A run started before the change continues and gains
it on its next call.

## Open Questions

- None blocking. The retry count (1) is one constant
  (`TITLE_RETRIES = 1`) in `common.py`.
