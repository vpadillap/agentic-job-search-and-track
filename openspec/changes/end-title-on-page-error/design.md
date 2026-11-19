## Context

Every built-in reader raises `common.Stop(reason, detail)` (Bumeran: its own
`_Stop`) for anything unexpected. The reader's `_read` catches it, puts it in
`summary["stopped"]`, and `common.finish` records the provider `failed` for
the run. The next call for another title then fails in `common.context` with
`provider_stopped`. The rule does not distinguish a block (the site refuses
us: stopping is right) from a page that did not look as expected for one
title (stopping costs every other title).

Where each reader raises `Stop("error")` today:

| Reader | Site | Today | This change |
|---|---|---|---|
| LinkedIn | search page has job ids but no cards | stop | title problem `cards_without_data` |
| LinkedIn | posting page without its description | stop | posting unreadable; two in a row in a title → title problem `no_description` |
| LinkedIn | network error | stop | unchanged (stop) |
| LinkedIn | other HTTP status (not 200, 3xx, 429, 999, the unreadable 404/410) | stop | unchanged (see D6) |
| Indeed | first variant has no job-card data | stop | title problem `no_card_data` |
| Indeed | a chosen posting shows no description panel | stop | posting unreadable; two in a row in a title → title problem `no_description` |
| Indeed | browser fails | stop | unchanged (stop) |
| Bumeran | search page sends no readable data in 30 s | stop | title problem `no_search_data` |
| Bumeran | page N is not page N | stop | ends the title after the pages already read: title problem `paging` |
| Bumeran | a result without an id | stop | that result is skipped and counted; a page where no result has an id → title problem `no_search_data` |
| Bumeran | posting page sends no data / no `aviso` | stop | posting unreadable; two in a row in a title → title problem `no_posting_data` |
| Bumeran | browser cannot load a page | stop | unchanged (stop) |
| Get on Board | 3 unreadable API answers in a row | stop | title problem `unreadable_answers`, unless all were network failures (stop) |
| Greenhouse | 3 unreadable API answers in a row | stop | same as Get on Board |

Glassdoor is not in the table: `fix-provider-glassdoor` owns its reader.

## Goals / Non-Goals

**Goals:** one bad title costs one title; a real layout change still stops
the provider quickly (within two titles); the user and agent see what
happened in the summary and the report.

**Non-Goals:** retries, throttling, 429 handling, cool-downs, soft blocks
(all `retry-soft-blocks-and-browser-choice`); Glassdoor
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
   `failed`, later calls refused.

`title_problem` is a new summary key present (as `null`) in every summary so
the agent can always read it. Indeed's existing `ended_early` (a later
variant shows a sign-in page or no card data) is unchanged: it is a normal
end, since the first variant already proved the layout and the access.

### D2. Two titles in a row with the same kind stop the provider

`common.title_problem(ctx, state, summary, kind, detail)`:

- reads `state["title_problems"]` (a list of `{"title", "kind", "detail"}`
  in reading order, stored in `<provider>-state.json` with the rest of the
  run state) and `state["last_title_kind"]`;
- if `last_title_kind == kind`, raises `Stop("error", "<detail>; the same
  problem (<kind>) on '<previous title>' and '<this title>': the site has
  probably changed")`;
- otherwise appends the entry, sets `last_title_kind = kind`, and sets
  `summary["title_problem"]`.

A title that ends normally after reading at least one results page with
results sets `last_title_kind = None` (done in `common.finish` when neither a
title problem nor a stop is set); a title with no results leaves it as it is
(see Risks). So:

- A, B, C where only B has `no_card_data` → only B is lost.
- A and B both `no_card_data` → B's call stops the provider; C onwards are
  refused as today.
- A `no_card_data`, B `no_description` → different kinds: each loses only
  itself. Different symptoms are weak evidence of a single change, and the
  cost of being wrong is one extra title.

Why two and not three: a real layout change then costs at most one extra
title (about 1–3 minutes of paced requests), which is cheaper than one false
stop (every remaining title).

Why "in a row" across calls and not "in a call": every call is one title, so
the evidence lives between calls; the state file already survives between
calls of a run and is the only place that does.

### D3. Postings without a description are a posting problem first

Today one LinkedIn posting page without its description stops LinkedIn for
the run. A single removed or oddly built posting is common; a layout change
affects every posting. So:

- one posting whose description (or Bumeran posting data) is missing → it is
  listed in `unreadable` with the reason, its id is still marked handled (as
  today: it is not opened again in the run), and the title continues;
- two in a row in the same title → title problem `no_description` (Bumeran:
  `no_posting_data`), which then follows D2.

A posting read successfully resets the in-title count.

### D4. API readers: classify the three failures

Get on Board and Greenhouse already tolerate up to two unreadable answers in
a row within a call. Their failure counter stays per call. When it reaches
three:

- if every one of the three had no HTTP status (the request itself failed:
  `OSError`, timeout), it is a network failure → `Stop("error")` as today;
- otherwise → title problem `unreadable_answers` with the last URL and
  status.

For Greenhouse a title's work spans several boards; the title problem ends
the title's remaining boards and postings, and the board memory
(`save_settings`) is saved as today (the `finally` already does it).

### D5. Where the code goes

- `common.py`: `title_problem(...)`, the `title_problems` and
  `last_title_kind` state defaults in `load_state`, and the reset in
  `finish`. `Stop`'s docstring is unchanged; a new `TitleProblem(kind,
  detail)` exception lets a reader leave its loops from deep inside (for
  example from Indeed's `select` callback or the API `fetch` helper); the
  reader's `_read` catches it next to `Stop` and calls `title_problem`, which
  may itself raise `Stop` (caught by the same handler, which then records the
  stop as today).
- Bumeran: until `retry-soft-blocks-and-browser-choice` moves it onto
  `common`, it keeps its own state file shape (`last_page_at`, `ids`, …);
  `title_problem` only reads and writes its two keys, so it works with
  Bumeran's state dict too. Its `_Stop` becomes an alias of `common.Stop`
  so one handler serves both.
- Each reader catches `TitleProblem` in the same `try` as `Stop`; nothing
  else in the flow changes.

### D6. What stays a stop (and why)

- Blocks: unchanged per provider file (`blocked`).
- Browser or network failure: the session or connection is broken; the next
  title would fail the same way and cost pacing time.
- LinkedIn's "other HTTP status" (for example a 5xx or 400 on a search):
  left as a stop here. A 5xx is the territory of the retry change (it may
  retry before deciding); a 4xx for a specific query is possible but was
  never seen. Reopen if it happens.
- Indeed: a block or sign-in page on the first variant of a title stays a
  block (unchanged).

### D7. What the agent and the user see

- Provider files, step "read the summary": `title_problem` is named with
  `stopped`; a new step says: if `title_problem` is set, import what was
  written, go on with the next title, and remember it for the report.
- The final record for a provider with title problems:
  `jt run provider <run_id> <id> --status ok --detail "<n> titles ended
  early: <title> (<kind>), …"`. The detail is stored and shown as today.
- `/job-search` step 6: one sentence that a title problem is not a provider
  failure; the report names the titles that ended early.

## Risks / Trade-offs

- **A real layout change costs one more title.** Accepted (D2); the provider
  still stops on the second.
- **Alternating titles hide a change.** If titles alternate between
  "results with the problem" and "no results at all", a title with no
  results resets the count. A no-results title is not evidence either way,
  so it does **not** reset `last_title_kind`; only a title that read at
  least one results page cleanly does. (Stated in the spec scenarios.)
- **Two readers' state in flight.** The retry change also adds state keys
  (cool-downs). Distinct key names; no conflict.
- **Agents that ignore `title_problem`.** Harmless: the provider is still
  open, the next call works; only the report loses the note. The provider
  files make it explicit.

## Migration Plan

No data migration: state files are per run and `load_state` supplies the
defaults for the new keys. A run started before the change continues with
the old keys and gains the new ones on its next call.

## Open Questions

- None blocking. If the owner prefers three titles in a row, it is one
  constant (`SAME_PROBLEM_TITLES = 2`) in `common.py`.
