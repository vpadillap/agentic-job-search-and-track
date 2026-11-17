## Context

`providers/linkedin.md` (from `add-provider-linkedin`) tells the agent to run
`curl` for LinkedIn's guest search and each public posting page, read the
HTML, and build import records. The dry run worked only because the agent
wrote a throwaway script. Measured 2026-11-17: a guest search page is about
31 KB, a posting page about 250 KB, and the description markup in it about
5 KB. A study with Python's `urllib` (2 real requests, logged out, 5 s apart,
same User-Agent and Accept-Language) got the same answers as `curl`: 200 with
10 cards, and 200 with the description and the criteria "Seniority level",
"Employment type", "Industries".

## Goals / Non-Goals

**Goals:**

- The fixed work (requests, pacing, stop conditions, extraction) is code,
  tested, and the same every run.
- The agent reads only what needs judgment, and never retypes a description.
- Fewer requests to LinkedIn on repeated searches.

**Non-Goals:**

- Any other LinkedIn access, filter, or field (unchanged from
  `add-provider-linkedin`).
- Readers for other sites, or making readers mandatory: a provider can still
  be added with its file alone.
- Deciding the work mode, language, or flags in code.

## Decisions

### D1. One command per title: `providers read linkedin <run_id> --title T`

`jobtracker providers read <provider> <run_id> --title "<title>" [--location
"<country in English>"]`. A small registry maps provider ids to readers; only
`linkedin` has one, and other ids answer `no_reader`. One title per call keeps
a call at most 3 search pages plus 30 posting pages (about 3 minutes with the
pacing), within one tool call, and lets the agent import after each title, so
a later block keeps what was read.

### D2. Inputs come from the system

The run gives the window (`published_since`, `posting_age_days`, mapped to
`f_TPR` with the table already in the provider file) and the capture folder;
the provider file's front matter gives `min_seconds_between_requests` and
`max_results_per_query` (pages = max / 10); the profile's ISO `country` fills
each record's `country`. LinkedIn's `location` needs the country's English
name, which the standard library cannot produce from an ISO code, so the agent
passes it with `--location` (the provider file says so); without it the
parameter is left out. The run must be running and list LinkedIn as a pending
provider.

### D3. HTTP with the standard library

`urllib.request` with an opener that never follows redirects and has no cookie
handler; the fixed User-Agent and `Accept-Language: en-US,en;q=0.9` of the
provider file; a 30 s timeout. A network error stops LinkedIn with reason
`error`. The fetch function, the clock, and the sleep are injected so tests
never touch the network or wait. `curl` stops being a LinkedIn dependency
(`dependencies: []`).

### D4. Run state in the capture folder

`linkedin-state.json` in the run's capture folder keeps the time of the last
request, the request counter (raw pages are saved as `linkedin-<n>.html`, for
audit), the job ids opened in this run, and the drafts files written. Each
request waits until `min_seconds_between_requests` after the last one, also
across calls. It is per-run working data next to the captures, so no schema
change. Whether LinkedIn is stopped is read from the run itself (provider
status `failed`), not from the file.

Calls in parallel would all read the same "last request" time and request
LinkedIn together (and could open one posting twice), so a call takes
`linkedin.lock` in the capture folder, created exclusively, and removes it
when it ends; a second call while it exists is refused with `reader_busy`
before any request. A lock older than 30 minutes (longer than any call: 33
requests with pacing and timeouts) is treated as left by a crashed call and
taken over. The provider file also says to read titles one at a time.

### D5. What happens to each card

In order: a date before `published_since` is counted as outside the window; a
job id already opened in this run (another title) is counted as a duplicate;
a job id LinkedIn already stored in an earlier run is imported right away as
seen, built from the stored posting with the card's date (no request); anything
else gets its posting page opened and becomes a draft. A posting page that
answers 404 or 410 is listed as unreadable with its link and reason.

### D6. Extraction with `html.parser`

A small `HTMLParser` collects text by class name: cards (`base-search-card`
with `data-entity-urn`, `base-search-card__title`,
`base-search-card__subtitle`, `job-search-card__location`, `time[datetime]`,
`job-search-card__salary-info`) and posting pages
(`show-more-less-html__markup`, `description__job-criteria-subheader` /
`description__job-criteria-text`). The description becomes plain text: block
ends and `<br>` are line breaks, list items start with "• ", entities are
unescaped, spaces are collapsed within a line, and runs of blank lines become
one. Stop rules are those of the provider file: 429 or 999, any 3xx (with
where it points), or a first page with a sign-in form and no cards →
`blocked`; a posting page without the description markup, or a non-empty
search page without cards or sign-in form that is not "no results" →
`error`. A first page without cards and without a sign-in form means no
results for that title.

### D7. Fields the reader decides, and fields it leaves

Contract type: Full-time → `full-time`, Part-time → `part-time`, Contract →
`contractor`; anything else leaves it empty and keeps the raw
`employment_type` in the draft so the agent can flag it. Seniority "Not
Applicable" is left empty. A card salary text is kept as `salary_shown`.
`work_mode`, `work_mode_detail`, `language`, `published_salary` are null and
`flags` is empty: the agent's reading. The import ignores the informational
fields.

### D8. Readings merged at import

`postings import <run_id> <drafts> --readings <file>`. A reading is
`{external_id, work_mode, work_mode_detail, language, flags,
published_salary}`; only those keys are accepted, every draft needs exactly
one, and a reading for an unknown id is refused. The merge happens before the
normal validation, so values are checked as usual and nothing is stored when
anything is wrong. The agent writes only a few hundred bytes per posting
instead of each description.

### D9. Summary

`{provider, title, requests, pages, cards, outside_window, duplicate_in_run,
already_seen, new, unreadable: [{external_id, url, reason}], drafts_path,
stopped: null | {reason, detail}}`. On a stop the reader records
`run provider … failed --reason blocked|error --detail` itself and says so.

## Risks / Trade-offs

- [LinkedIn changes its HTML] → The reader stops with reason `error` naming
  what is missing; fixing it is a provider change, as before.
- [Python's client is treated differently from curl in the future] → Same
  stop rules apply; the provider change would revisit the client.
- [A call takes minutes] → One title per call keeps it to about 3 minutes.
- [Seen postings get no fresh description] → They were stored verbatim when
  first read; a repost with changes is a new job id on LinkedIn.

## Migration Plan

None: no schema change. The provider file and the skill change together with
the command.

## Open Questions

None.
