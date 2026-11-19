## 1. Shared retry policy

- [x] 1.1 `readers/common.py`: `Throttle(detail, retry_after)`, `parse_retry_after` (seconds or HTTP date), `backoff(attempt, rand)` with equal jitter, the constants (3 attempts, 120 s max wait, 6 retries per run, 15/30 min cool-downs, 2 cool-downs before a hard stop)
- [x] 1.2 `common.attempt` around one request: waits never below `min_seconds`, pacing clock updated per attempt, counters and an audit list of throttles in the state file
- [x] 1.3 State file: `titles` (pages read, done), `retries`, `throttles`; old Bumeran keys read on load
- [x] 1.4 `common.finish` records a cool-down (`throttled`) or a hard stop; the summary's `stopped` carries `resume_after`
- [x] 1.5 Tests: Retry-After as seconds and as a date, an unparsable value, backoff bounds with a fixed random, the per-request and per-run caps, a wait over 120 s leading straight to a cool-down

## 2. Cool-down on the run

- [x] 2.1 `search.record_cooldown`; `cooldown_until`, `cooldown_detail`, `cooldowns` on the run's provider entry; the third one becomes `failed`/`blocked`
- [x] 2.2 `common.context` refuses calls during a cool-down (`provider_cooling`, `resume_after`, minutes left) and lets the first call after it through
- [x] 2.3 `search.start_run` inherits a running cool-down from the latest earlier run; `search.finish_run` records a cooling provider as `failed`/`throttled`; `throttled` added to `SKIP_REASONS`
- [x] 2.4 Panel: `skip.throttled` (and any reason label) in en and es
- [x] 2.5 Tests: refusal during a cool-down without any request, resumption after it, inheritance by a new run, finish during a cool-down, third throttle as a hard stop

## 3. Readers

- [x] 3.1 LinkedIn: 429/999 as `Throttle` with `Retry-After` from the answer; redirect and sign-in stay `Stop`; resume at the first unread page; a completed title sends nothing; a posting is kept only after its answer passed
- [x] 3.2 Bumeran onto `common` (context, state, lock, stop, seen records); 429 and challenge titles as `Throttle`, 403 and block titles as `Stop`; resume at the first unread page
- [x] 3.3 Glassdoor: 429 and security-check titles as `Throttle`, 403/"Attention Required"/sign-in wall as `Stop`; a posting kept only after its answer passed; the salary reader answers `throttled` with `resume_after`
- [x] 3.4 Indeed: security-check titles and 429 as `Throttle`, "Blocked"/403/sign-in as `Stop`
- [x] 3.5 Greenhouse and Get on Board: 429 as `Throttle` with `Retry-After`, 403 as `Stop`
- [x] 3.6 Scrapling's own retries off (`retries=1`) in Bumeran, Glassdoor, and Indeed
- [x] 3.7 Tests per reader with fake fetchers/browsers: a 429 that clears after one retry, a 429 with `Retry-After` past 120 s, a challenge page through to a cool-down, a 403 stop, resumption after the cool-down without reopening postings, the throttled posting opened after the cool-down

## 4. Provider files, skill, docs

- [x] 4.1 `providers/linkedin.md`, `bumeran.md`, `glassdoor.md`, `indeed.md`, `greenhouse.md`, `getonbrd.md`: "Limits and etiquette" (waits, caps, cool-downs, what is never done) and "Stop conditions" (soft vs hard); `last_verified` unchanged unless re-verified; `jt providers validate` passes
- [x] 4.2 `.claude/skills/job-search/SKILL.md` (and the Spanish alias template if it repeats it): handling `throttled` and `provider_cooling`
- [x] 4.3 `docs/workspace-layout.md`: the state file's new fields and where the cool-down is kept
- [x] 4.4 Tests: provider files validate; skill evals unchanged

## 5. Verification

- [x] 5.1 `ruff check .`, `pytest`, privacy guard
- [x] 5.2 `openspec validate retry-soft-blocks --strict`: OpenSpec not installed on this machine; deltas checked by a structural script (SHALL + scenario per requirement, MODIFIED headings match)
