## Why

A real search on 2026-11-18 showed that the readers treat every refusal as
final for the run:

- LinkedIn answered HTTP 429 after one search page. The reader recorded
  LinkedIn as `blocked`, and every later call in that run was refused
  (`provider_stopped`). The only way to read the remaining titles was a new
  run, which searches every provider again.
- Glassdoor answered 429 on salary pages, with the same result.

A 429 or a challenge page is usually a temporary throttle of the user's IP,
not a ban. Sites expect a client to slow down and come back later. Stopping
for the whole run throws away the rest of the search, and a new run repeats
requests the site has already answered. The readers should tell a throttle
apart from a hard block, wait as the site asks, and resume the same run later,
without ever trying to get around the limit.

## What Changes

- **Soft blocks and hard blocks.** Each reader's stop signals are split in
  two. *Soft* (a throttle): HTTP 429; LinkedIn's 999; HTTP 503 with a
  `Retry-After` header; a Cloudflare challenge page ("Just a moment…",
  "Un momento…", "Security | Glassdoor", Indeed's "Security Check") that
  Scrapling did not pass. *Hard* (unchanged: the provider stops for the
  run): HTTP 403, a Cloudflare "Attention Required" or "Access denied" page,
  any redirect to a sign-in or sign-up page, a sign-in wall that does not
  close, a layout change, and a network or browser failure.
- **Retry inside a call.** On a soft block the reader waits and repeats the
  same request: the `Retry-After` value when the site sends one (seconds or
  an HTTP date), otherwise exponential backoff with jitter. At most 3
  attempts per request, each wait at most 2 minutes, and at most 6 retries
  per provider per run.
- **Cool-down instead of a stop.** When a request is still throttled after
  its attempts, or the site asks for a wait longer than 2 minutes, or the run
  budget is used up, the reader ends the call with
  `stopped: {"reason": "throttled", "resume_after": <time>}` and records a
  cool-down on the run's provider entry: at least 15 minutes the first time,
  30 the second, or longer when `Retry-After` says so. Calls before that time
  are refused without any request (`provider_cooling`, with the time left).
  The first call after it goes ahead in the same run. A third throttle in the
  same run is a hard stop (`blocked`, "throttled again after two
  cool-downs"). A run started while a provider is still cooling down from an
  earlier run inherits the remaining cool-down.
- **Progress survives a cool-down.** The per-run state file (`<id>-state.json`
  in the capture folder) also keeps, per title, the search pages already read
  and whether the title is complete, plus the retry counters. A call after a
  cool-down skips completed titles and pages already read where the site
  pages by URL (LinkedIn, Bumeran). Postings already opened in the run are
  never opened again. A posting whose request was throttled is not marked as
  read, so it is opened after the cool-down. Today LinkedIn and Glassdoor mark
  it as read before checking the answer, so it would be lost.
- **One policy for every built-in reader.** The classification, waits,
  budget, and cool-down live in `readers/common.py` and are used by LinkedIn,
  Bumeran, Glassdoor (searches and salary pages), Indeed, Greenhouse, and
  Get on Board. Bumeran, which still has its own copy of the run context,
  state, and lock, moves onto `common`. Scrapling's own silent retries
  (3 by default, 1 s apart) are turned off in the Scrapling readers, so
  every repeat goes through this policy.
- **`jt run finish`** records a provider that is still cooling down as
  `failed` with the new reason `throttled` and the time it was waiting for.
  The panel shows that reason in English and Spanish.
- **Provider files.** "Limits and etiquette" and "Stop conditions" in
  `providers/linkedin.md`, `bumeran.md`, `glassdoor.md`, `indeed.md`,
  `greenhouse.md`, and `getonbrd.md` state the soft and hard signals, the
  waits, and the cool-down. They also state the limits that stay in place:
  no proxies, no rotating or changed user agents, no account, no new browser
  identity to get past a block.
- **`/job-search` skill.** When a reader returns `throttled`, the agent
  imports the drafts already written, goes on with the other providers, and
  then tells the user when the throttled provider can resume. The user
  chooses to come back to it in the same run or to finish the run.

## Capabilities

### New Capabilities

- `provider-throttling`: telling a temporary throttle apart from a hard
  block, waiting as the site asks, cool-downs that resume the same run, and
  keeping progress across them.

### Modified Capabilities

- `provider-linkedin`, `provider-bumeran`, `provider-glassdoor`,
  `provider-indeed`: "Pacing and stop conditions" (a throttle leads to a
  cool-down and a later call in the same run; hard blocks unchanged).
- `provider-greenhouse`: "Verbatim drafts and pacing" (429 leads to a
  cool-down; 403 still stops).

## Non-goals

- Proxies, rotating or spoofed user agents, a different IP, the user's
  accounts or cookies, or a fresh browser identity to get past a block.
  Waiting is the only response to a throttle.
- Retrying hard blocks (403, sign-in walls, redirects to login).
- A command to end a cool-down early. The time gate cannot be overridden.
- Sleeping through a long cool-down inside one CLI call. A call waits at most
  2 minutes per retry; longer waits end the call.
- New provider front-matter keys for the retry policy. The values are the
  same for every built-in reader and are documented in each provider file.
- Private providers' readers (`<home>/providers/<id>.py`). They may raise
  the same `common` signals, but nothing is required of them.
- Which browser the Scrapling readers start, and how `jt providers install`
  checks it: that belongs to the change `fix-browser-install-windows`. This
  change only sets Scrapling's `retries` in the readers' existing sessions.

## Impact

- Code: `src/jobtracker/core/readers/common.py` (policy, signals, state),
  the six built-in readers, `src/jobtracker/core/search.py` (cool-down on the
  run's provider entry, `throttled` reason, inheritance in `start_run`,
  `finish_run`, shown by `run show`), the panel's en/es strings.
- No database migration: the cool-down is a field of the run's provider
  entry, which is already stored as JSON.
- Docs: the six provider files, `.claude/skills/job-search/SKILL.md` (and
  its Spanish alias template if it repeats the stop handling),
  `docs/workspace-layout.md` (the state file's fields).
- Tests: unit tests with fake fetchers and browsers that answer 429 with and
  without `Retry-After`, 999, 503, challenge pages, and 403. A fake clock,
  sleep, and random generator make the waits exact. Further tests cover the
  cool-down refusal and resumption, the run's retry budget, and inheritance
  by a new run.
