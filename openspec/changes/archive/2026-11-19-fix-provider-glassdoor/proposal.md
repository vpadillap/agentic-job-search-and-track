## Why

Glassdoor is a global provider and, for many users, the only salary source
they have turned on. In a real search on 2026-11-18 (Peru, commercial and
marketing titles) it gave nothing: no postings and no salary evidence, so
every top posting ended with "no reliable salary data".

The study (2026-11-19), from that run's captures (kept private; only counts
and markup names here):

| What happened | What the capture shows |
|---|---|
| The first title's search page loaded ("1 brand manager Job in Peru, November 2026 \| Glassdoor") and the reader stopped with `error` ("the page changed") | The markup did not change. The page is Glassdoor's "limited or no results" page: a notice (`lrp-zrp-heading`, "had limited or no results, but similar jobs are listed below"), then only a "Similar jobs" section (`data-test="related-jobs-list"`) with 5 cards (`li[data-test="jobListing"][data-jobid]`). The page's own data (`searchResultsData.jobListings.jobListings`) is an empty list. The title's "1" counts a listing the page does not show. The reader rightly left the similar jobs out, but then read "0 cards, site says 1" as a changed page. |
| Every later title was refused (`provider_stopped`) | The stop ended Glassdoor for the whole run, so 15 titles were never searched. |
| The installed Chrome (`real_chrome=True`) was used because Playwright's Chromium does not start on that machine | The cards, the similar-jobs section, and the page data have the same markup the reader expects. The browser was not the cause. Choosing the browser belongs to `retry-soft-blocks-and-browser-choice`. |
| Salary pages (`/Salaries/peru-<title>-salary-SRCH_IL.0,4_IN189_KO5,<n>.htm`) answered 429 "Security \| Glassdoor" | The salary reader has no pacing between calls (each call is a new browser session, and the agent asks for several titles in a row) and no cool-down: after a 429 the next call goes out at once. Its answer to a 429 is `blocked`, and the agent records it like "no data". |
| Spanish titles | Peru's salary pages are keyed by the title words. A Spanish title ("Jefe de Marca") and its usual English equivalent ("Brand Manager") are different pages; the reader takes one title per call. |

## What Changes

- **Search results from several sources, in order.** The search page's own
  data (`searchResultsData.jobListings.jobListings`, decoded from the page's
  Next.js data), then any JSON-LD `ItemList` of postings, then the cards
  (`li[data-jobid]` with a `/job-listing/` link), then any `/job-listing/…?jl=`
  link. Everything inside "Similar jobs" is never a result. The page data
  also gives each posting's age, so fewer posting pages are opened.
- **No results is not an error.** When the page data's list is empty, or the
  "limited or no results" notice is shown, or the site says 0, the title ends
  with `no_results: true` and Glassdoor goes on with the next title.
- **Every title is tried.** The owner's direction (2026-11-19), shared
  with `end-title-on-page-error`: retry the title, and always work through
  all the titles. No results found by any source, and no sign of "no
  results": the reader loads the search page once more (paced). If it still
  reads nothing, the title ends with `title_problem` (`no_results_read`,
  with the capture's name), Glassdoor is not stopped, and the next title is
  searched. Title problems never stop Glassdoor, however many there are.
- **Postings:** one posting without a readable description is listed in
  `unreadable`; two in a row end that title (`title_problem`
  `no_description`), keeping what was read. Before, three in a row stopped
  Glassdoor for the run.
- **A "Show more jobs" response that does not parse** no longer stops
  Glassdoor: its cards are still on the page; the summary counts it
  (`show_more_unreadable`).
- **A likely site change is reported, not acted on.** When this title and
  every earlier title of the run that read something ended with the same
  kind of problem (two at least), the summary sets `site_may_have_changed`,
  so the agent tells the user and the owner can open a fix. Titles with no
  results do not count either way.
- Glassdoor still **stops for the run** only on a hard block (403, a block
  page, a sign-in wall: `blocked`) or a browser failure (`error`); a 429 or a
  security check is the provider-throttling policy's (waits, then a run
  cool-down).
- **Salary lookups are paced and cool down across calls.** At least 20
  seconds between salary pages, across calls. A throttle is first waited out
  within the call by the shared provider-throttling policy
  (`common.attempt`: `Retry-After`, backoff, at most 3 tries). A refusal
  that remains (or a 403) starts a salary cool-down kept across calls: the
  `Retry-After` the site sends, and at least 15 minutes the first time, 30
  the second, 60 the third and later (reset after a page that loads). Until
  it ends, salary calls answer `throttled` with `resume_after` and open no
  page. Salary calls have no run, so the run cool-downs of provider-throttling
  do not cover them; this is the part this change adds.
- **Title variants for salary pages.** `--title` can be given up to three
  times; the titles are tried in order in one session, paced, until one has
  data. The result lists every page tried (for `jt salary none --checked`).
  The provider file tells the agent to pass, for a Spanish-speaking country,
  the posting's own title and its usual English equivalent. No translation
  table in code: choosing the variants is the agent's judgment.
- **`providers/glassdoor.md`**: the search recipe (`no_results`,
  `title_problem`, `site_may_have_changed`), the salary recipe (variants, `throttled`, what to record),
  stop conditions, pitfalls (the "limited or no results" page), and
  `last_verified`.
- **`docs/workspace-layout.md`**: what `provider-settings/glassdoor.json`
  keeps for salary pacing and cool-down.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `provider-glassdoor`: "Pacing and stop conditions" (a title that cannot be
  read is loaded again, then ends only that title; title problems never stop
  Glassdoor), "Salary reports as evidence" (pacing,
  cool-down, title variants), and a new requirement for where search results
  come from.

## Non-goals

- Retrying a request inside a call, backoff with jitter, run cool-downs for
  searches, and the browser setting: all in
  `retry-soft-blocks-and-browser-choice`.
- Proxies, changed user agents, the user's cookies or account, warming up a
  session, or anything else meant to get past a throttle. Waiting is the
  only answer.
- A translation table of job titles.

## Alignment with `end-title-on-page-error`

That change applies the same owner rules to LinkedIn, Indeed, Bumeran, Get
on Board, and Greenhouse and leaves Glassdoor to this change. This change
uses its names (`title_problem` with a `kind`, `site_may_have_changed`,
`retries`) and its rule for a likely site change. Its shared
`common.TitleProblem` helper does not exist yet, so Glassdoor has a local
`TitleProblem` with the same shape; whichever change lands second moves
Glassdoor onto the shared one.

## Ordering with `retry-soft-blocks-and-browser-choice`

That change landed first (archived as `retry-soft-blocks`). This change is
rebased on it: its delta of "Pacing and stop conditions" is written on the
archived text, Glassdoor's searches and posting pages keep going through
`common.attempt`, and salary pages use `common.attempt`,
`common.parse_retry_after`, `common.Throttle`, and `common.is_challenge`
instead of a copy. Only the salary cool-down across calls is Glassdoor's own.

## Impact

- Code: `src/jobtracker/core/readers/glassdoor.py`,
  `src/jobtracker/core/readers/__init__.py` and `src/jobtracker/cli/main.py`
  (`--title` repeated for salary).
- Tests: `tests/test_glassdoor_reader.py` with fictional saved pages in
  `tests/fixtures/glassdoor/` (a results page, a "limited or no results"
  page, a page known only by its data, a 429 salary answer).
- Docs: `providers/glassdoor.md`, `docs/workspace-layout.md`,
  `.claude/skills/job-search/salary-guide.md` (salary variants and
  `throttled`).
- No database change.
