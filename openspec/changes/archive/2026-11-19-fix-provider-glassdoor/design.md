## Context

`readers/glassdoor.py` takes cards only from `<li data-jobid>` before the
"Similar jobs" section, and raises `common.Stop("error")` when it finds none
while the page's title count is not 0. `common.finish` then records
Glassdoor as failed for the run. The salary reader opens one page per call
with a new session, with no pacing and no memory between calls.

## Decisions

### D1. Results: page data first, then JSON-LD, cards, links

The search page is a Next.js page; its data comes as `self.__next_f.push([1,
"<chunk>"])` script strings. The reader decodes each chunk as a JSON string,
joins them, finds `"searchResultsData"`, then the first `"jobListings":[`
after it, and reads that array with `json.JSONDecoder.raw_decode`. Each item
gives `jobview.job.listingId`, `jobview.header.ageInDays`, and, when present,
a link (`jobview.header.seoJobLink`, or `jobview.job.jobLink`).

Order of sources, the first that answers wins for *which* postings are
results; links are filled from any source by listing id:

1. the page data (`found`, possibly empty: an empty list is an answer);
2. JSON-LD `ItemList` items whose `url` has `/job-listing/` and `jl=`;
3. cards `li[data-jobid]` with a `/job-listing/` link;
4. any `/job-listing/…?jl=<id>` link.

Sources 2–4 read only the HTML before `data-test="related-jobs-list"`. A
result with no link anywhere is skipped and counted in `unlinked`.

*Alternatives:* cards first (today): breaks on any markup rename, and cannot
tell "no results" from "page changed". A full RSC parser: too much for what
is needed; the chunk join plus `raw_decode` is enough and standard-library.

### D2. Ending a title vs stopping Glassdoor

The owner's rules (2026-11-19, shared with `end-title-on-page-error`): no
results is never a problem; retry the title; always work through all the
titles.

- No results (`no_results: true`): the page data's list is empty, the
  `lrp-zrp` notice is in the page, or the site total is 0. Never a problem,
  however many titles in a row have none.
- Unreadable search page: none of the sources answers and there is no sign
  of "no results". It raises `common.TitleProblem("no_results_read", …)`,
  and `common.retry_title` loads the same URL once more, paced
  (`title_retries: 1`). If it reads, the title goes on. If not, the title
  ends: `title_problem: {kind, detail}` in the summary, `stopped` stays
  empty, and the provider is not recorded as failed.
- Postings: one without a readable description goes to `unreadable`; two
  in a row end the title (`no_description`), keeping the drafts already
  made. No retry: a posting page is opened once per run.
- A "Show more jobs" response that does not parse is counted
  (`show_more_unreadable`) and its cards are still read from the page.
- `site_may_have_changed`: `state["title_outcomes"]` keeps, per title that
  read something, its problem kind or none. It is true when this title and
  every earlier one ended with the same kind (two at least). Titles with no
  results are left out. Information only, never a stop.
- Blocks and browser failures keep stopping Glassdoor as today.

The cost of a real layout change is bounded: two search pages per
remaining title at Glassdoor's pace, instead of losing every title to one
odd page.

### D3. Salary pacing and cool-down outside a run

Salary calls have no run, so their memory is the user's
`provider-settings/glassdoor.json`, key `salary`:
`{"last_request_at": <epoch>, "cooldown_until": <epoch|null>,
"throttles": <int>, "last_detail": <str>}`.

- Pacing: `SALARY_MIN_SECONDS = 20` between salary page loads, also across
  calls (the reader sleeps the rest of the gap). Twenty seconds is chosen to
  be well above the search pacing, not measured: each salary call is a new
  session that passes Cloudflare again.
- Each salary page goes through `common.attempt` (provider-throttling): a
  429 or a security title is a `common.Throttle` carrying the
  `Retry-After` the site sent (`common.parse_retry_after`), waited out
  within the call. When `common.attempt` gives up (`Stop("throttled")`), or
  the page answers 403 or a block page (`Stop("blocked")`):
  `throttles += 1`; wait = `max(Retry-After, 15 min × 2^(throttles-1))`,
  at most 60 minutes unless `Retry-After` asks for longer; no further title
  is tried.
- A page that loads (with or without data) sets `throttles = 0`.
- While `now < cooldown_until` the reader opens no page and answers
  `{"data": false, "throttled": true, "resume_after": <ISO time>,
  "minutes_left": n}`.

The fetcher reports response headers through `last_headers` (Scrapling's
`Response.headers`); fakes in tests set it.

### D4. Title variants

`salary(paths, titles: str | list[str])`: up to 3 distinct titles, one
session, paced (D3), in the given order. It stops at the first with data,
or at a throttle (later titles are not tried). The answer is the first
result with data (or the last one) plus `tried: [{"title", "url", "data",
"reason"}]`. The CLI's `--title` becomes `action="append"`; one `--title`
keeps today's answer shape (plus `tried`).

## Risks

- Glassdoor renames `searchResultsData`: sources 2–4 still work; the
  per-title end keeps the run going.
- The 20-second gap makes a salary call with three variants about a minute.
  That is acceptable for the few titles the agent researches per run.
