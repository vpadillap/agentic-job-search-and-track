## Context

Readers (`src/jobtracker/core/readers/`) raise `common.Stop(reason, detail)`
on any refusal; `common.finish` then records the provider as `failed` on the
run, and `common.context` refuses every later call (`provider_stopped`).
Bumeran keeps its own copy of the context, state, lock, and `_Stop`. The
per-run state file `<id>-state.json` holds `last_request_at`, `requests`,
`job_ids` (postings handled in the run), and `drafts`.

LinkedIn and Glassdoor call `keep(job_id)` before checking a posting page's
answer, so a posting whose page was throttled counts as handled and would
never be opened again in the run.

Scrapling (0.5.1) `StealthySession` takes `retries` (default 3) and
`retry_delay` (default 1 s). The defaults mean Scrapling already retries
failed page loads on its own, once a second, without the reader knowing.

## Goals / Non-Goals

**Goals:** recover from a temporary throttle in the same run, honouring what
the site asks; never resend a request already answered; one policy for all
built-in readers.

**Non-Goals:** see the proposal. In short, nothing that changes who the
requests appear to come from, and no retry of hard blocks.

## Decisions

### D1. Two exceptions: `Stop` (hard) and `Throttle` (soft)

`common.Throttle(detail, retry_after: float | None)` is raised by a reader's
check when an answer is a soft block; `common.Stop` stays for hard blocks and
errors. Each reader keeps its own classification (its markers differ), using
shared helpers: `common.SOFT_STATUSES = (429, 999)`; 503 is soft only with a
`Retry-After` header (without one it is a server error: `Stop("error")`);
`common.CHALLENGE_TITLES` for challenge pages; 403 and "Attention
Required"/"Access denied" titles are hard.

*Alternatives:* (a) one `Stop` with a `soft` flag: every `except` site would
need to look at it, which is easy to miss. (b) Classifying in `common` from
the raw answer: the readers' signals are too different (HTTP status, page
title, captured API responses, a dialog that will not close).

### D2. Retry inside the call, around one request

`common.Retrier(ctx, state, clock, sleep, rand)` wraps a single request:

```
for attempt in 1..ATTEMPTS (3):
    try: return request()
    except Throttle as t:
        record signal in state
        if attempt == ATTEMPTS or run budget (6 retries) used: cool down (D3)
        wait = t.retry_after if given else backoff(attempt)
        if wait > MAX_WAIT (120 s): cool down (D3)
        sleep(max(wait, ctx.min_seconds)); state.retries += 1
```

`backoff(n) = b/2 + rand() * b/2` with `b = min(120, 20 * 2**(n-1))`
("equal jitter"): 10–20 s, then 20–40 s. `Retry-After` is parsed as
delta-seconds or an HTTP date (`email.utils.parsedate_to_datetime`); an
unparsable value counts as absent. The pacing clock (`last_request_at`) is
updated after each attempt, so the normal minimum gap still holds. Clock,
sleep, and random are injected; tests make every wait exact.

*Alternatives:* (a) full jitter (`rand() * b`): it can retry almost at once,
which is rude after a 429. (b) A retry library (tenacity, backoff): `core`
must stay standard-library only. (c) No in-call retry, cool-down only: a
short 429 burst would cost a 15-minute pause.

### D3. Cool-down on the run's provider entry, gated by time only

On cool-down the reader writes what it has (drafts, state) and records
`search.record_cooldown(conn, run_id, provider, until, detail)`. That sets
`cooldown_until` (ISO time) and `cooldown_detail` on the provider's item in
`search_runs.providers` (JSON) and increments `cooldowns`. The status stays
`pending` or `ok`. Duration: `max(retry_after or 0, 15 min * 2**(k-1))` for the
k-th cool-down. The third throttle in the run that would need a cool-down is
recorded as `failed`, reason `blocked`.

`common.context` refuses a call while `now < cooldown_until`
(`provider_cooling`, with `resume_after` and the minutes left) and lets the
first call after it through. `search.start_run` copies a still-running
cool-down from the latest earlier run's entry for the same provider.
`search.finish_run` records a provider that is still cooling as `failed`
with the new reason `throttled` (added to `SKIP_REASONS`). Its detail gives
the time it was waiting for.

The reader's summary carries `stopped: {"reason": "throttled", "detail",
"resume_after"}` so the agent can tell the user.

*Alternatives:* (a) `jt run resume-provider <run> <id>`: an explicit command
lets the agent resume before the site's time, and the time gate already does
the job. `jt run show` already lists each provider's entry, so the
cool-down is visible without a new command. (b) A new status `cooling`: every
consumer of the status (panel, summaries, `finish_run`, stats) would need to
learn it; a field on the entry changes nothing for them. (c) Storing the
cool-down in `providers_state`: needs a migration and mixes per-user settings
with run state; inheritance in `start_run` covers the cross-run case.

### D4. Progress in the state file

`common.load_state` gains `titles: {<title>: {"pages": n, "done": bool}}`,
`retries` (count in the run), and `throttles` (a short list of `{at,
signal, url}` for the audit). A reader:

- returns at once (`already_done: true`, no request) for a title marked
  `done` in this run;
- for page-addressed searches (LinkedIn `start`, Bumeran `page`), starts at
  the first page not yet read;
- marks a posting as handled (`job_ids`) only after its answer passed the
  checks, so a throttled posting is opened after the cool-down (the order
  in LinkedIn and Glassdoor is fixed);
- marks the title `done` when it ends without a stop.

Glassdoor and Indeed search one page that grows with clicks. After a
cool-down they load it again, which is one request, and skip every
posting already handled.

*Alternatives:* storing progress in the database: it is capture-folder
bookkeeping for one run, like the existing state, and the database has no
place for it without a migration.

### D5. Bumeran moves onto `common`

`readers/bumeran.py` drops `_Context`, `_context`, `_load_state`,
`_save_state`, `_lock`, `_Stop`, and its seen-records copy, and uses
`common`'s. Its state key `last_page_at`/`pages`/`ids` becomes
`last_request_at`/`requests`/`job_ids`. `load_state` reads the old keys
when present, so a run that is open during the upgrade keeps its progress.

*Alternative:* adding the policy to Bumeran's copy: two copies of the policy
would drift.

### D6. Scrapling's own retries off

The three Scrapling readers (Bumeran, Glassdoor, Indeed) pass `retries=1`
(one attempt; Scrapling accepts 1 to 10) to the `StealthySession` they
already open, so every repeat goes through D2 and is counted and paced.
Which browser they start, and how `jt providers install` checks it, stays
with the change `fix-browser-install-windows`.

*Alternative:* leaving Scrapling's default: up to three hidden loads a
second apart, outside the pacing and the run budget.

## Risks / Trade-offs

- [A site reads repeated retries as abuse] → at most 2 retries per request
  and 6 per run, never sooner than the site asks or than `min_seconds`, two
  cool-downs then a hard stop.
- [A cool-down blocks an interactive session for 15+ minutes] → the agent
  goes on with the other providers and asks the user. The run stays open,
  and a new run inherits the cool-down instead of hammering.
- [Challenge pages after a Scrapling solve are not always throttles] →
  they become a cool-down, then a hard stop at the third. That is the same
  bound as a 429.

## Migration Plan

No database migration. Old state files are read with their old keys (D5).
This change lands after `fix-browser-install-windows` and is rebased onto it;
the two touch different files except `.claude/skills/job-search/SKILL.md`.
