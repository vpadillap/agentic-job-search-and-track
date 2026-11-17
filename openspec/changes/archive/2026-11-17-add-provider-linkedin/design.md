## Context

The provider mechanism exists (`provider-recipes`, `job-search`): the agent
reads `providers/<id>.md` and follows it literally, imports posting records
with `jt postings import`, and records each provider's outcome with
`jt run provider`. Today a provider with no stored choice counts as enabled
(`providers.with_state`); `/setup` lists providers with their access method,
asks which to use, and disables the others. The LinkedIn file itself is
instructions only.

This change depends on `add-work-mode-detail`, which adds a free-text
work-mode detail to postings (shown in the panel and editable by the user).
It is applied and merged first.

### Study (2026-11-17, logged out, no cookies, generic query "data analyst / United States", 6 s apart, 27 requests, no block)

| Request | Result |
|---|---|
| `jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=…&location=…&f_TPR=…&start=…` | 200, ~29 KB, 10 cards: job id, title, company, location, `/jobs/view/` link, `datetime=YYYY-MM-DD` |
| `jobs-guest/jobs/api/jobPosting/{id}` | 200, ~42–75 KB: description, criteria; seniority showed "Not Applicable" for a posting whose public page says "Mid-Senior level" |
| `jobs/view/{id}/` | 200, ~350 KB, no redirect: full description, criteria (Seniority level, Employment type, Industries); no work-mode field and no JSON-LD; the sign-in pop-up's markup is present but not a redirect |
| `jobs/search?…` (once, to read its form) | 200; visitor filters are only `keywords`, `location`/`geoId`, `f_TPR` (r86400, r604800, r2592000), `f_C` (company), and the `f_AL`/`f_EA` toggles |

Filters tested on the guest search: `f_TPR` works (r86400 returned only the
last day; r604800 only the last week); `start=10/20` returns new cards;
`location` works as free text and resolves to the same results as `geoId`;
`f_WT` (1, 2, 3), `f_JT` (F, P, C), and `sortBy=DD` are ignored (identical
cards, identical order), with free text or `geoId`. Over about 160 cards none
had a salary field.

Rules found: LinkedIn's User Agreement (effective 2025-11-03) §8.2 forbids
scraping with scripts, crawlers, or browser plug-ins, and §1.2 applies it to
Visitors; robots.txt disallows `/jobs-guest/` and states that automated access
without permission is prohibited; LinkedIn's help page says prohibited tools
lead to account restriction. Since April 2026 LinkedIn's pages probe visitors'
browsers for thousands of Chrome extensions to detect scraping tools.

## Goals / Non-Goals

**Goals:** a recipe that never involves the user's account, reads everything
the posting record needs, lets the agent judge work mode from the text, and
fails fast and visibly.

**Non-Goals:** see proposal.md. In addition: no attempt to read more than
about 30 cards per title.

## Decisions

### L1. Guest search for the list, public posting page for each posting
The guest search returns the same cards as the public page without the
sign-in pop-up and takes every visitor filter as a URL parameter, so no click
can push to a login screen. Each posting is then read from its public page
`jobs/view/<id>/`, which gives the complete description and the correct
seniority (the guest detail endpoint did not). Neither needs a browser.
`access: http`, `requires_login: false`, `live_walk: false`.

Alternatives: the guest detail endpoint for each posting (8× smaller, but
wrong seniority in the study); the logged-in session through the extension
(rejected by the owner: account risk, and LinkedIn fingerprints extensions); a
logged-out live walkthrough of `jobs/search` with Playwright or the extension
(rejected by the owner in favour of plain HTTP); web search for
`linkedin.com/jobs/view` links (no reliable dates). No fallback: if these
pages change, the provider fails and a new change revisits the recipe.

### L2. `curl` as the HTTP tool
The agent runs `curl` through its shell: it returns the raw HTML verbatim (a
summarizing fetch tool cannot be trusted with verbatim descriptions), reports
the status code and redirect target (`-w '%{http_code} %{redirect_url}'`),
does not follow redirects by default, and sends no cookies unless asked. It
ships with Windows 10+, macOS, and most Linux systems, and `jt doctor` already
checks `dependencies` with `which`. The request sends a common desktop browser
`User-Agent` and `Accept-Language`, fixed in the file; no rotation.

Alternatives: a new `jt fetch` command or a Python parser for LinkedIn (new
application code for one site); the agent's web fetch tool (summarizes, hides
status codes and redirects).

### L3. Search parameters
Only what LinkedIn offers visitors (see the study):
- `keywords=<title>`, `location=<free text from the profile>`.
- `f_TPR`: `r86400` for a 1-day window, `r604800` for 2–7 days, `r2592000`
  for 8–30 days; the import drops postings older than the run's window.
- `start=0,10,20` for paging.

Not sent, because LinkedIn ignores them for visitors: `f_WT`, `f_JT`,
`sortBy`. Results come in relevance order.

### L4. Pacing, caps, and stop conditions
`min_seconds_between_requests: 5`, `max_results_per_query: 30` (3 pages).
Stop paging early when a page returns fewer than 10 cards. A posting page is
opened once per job id per run, only for cards inside the window.

Stop all LinkedIn requests for the run on: HTTP 429 or 999, any 3xx (curl does
not follow it; a `Location` to `authwall`, `login`, `signup`, or `checkpoint`
is named in the reason), or a 200 without cards on `start=0` whose body
contains a sign-in form. The provider is recorded `failed --reason blocked`
with the status and URL; postings imported so far stay.

Cost: a run with 4 titles is at most 12 search pages plus up to 120 posting
pages (~350 KB each), about 11 minutes at 5 s per request. Repeated runs
re-open pages of postings already stored (the CLI has no lookup by external
id; see risks).

### L5. Field mapping
| Field | Source |
|---|---|
| `external_id` | card `data-entity-urn="urn:li:jobPosting:<id>"` |
| `url` | `https://www.linkedin.com/jobs/view/<id>/` (canonical, no slug or tracking) |
| `title`, `company`, `location` | card `base-search-card__title`, `base-search-card__subtitle`, `job-search-card__location` |
| `posted_at` | card `<time datetime="YYYY-MM-DD">` |
| `description` | posting page `show-more-less-html__markup`, as plain text with paragraph and list breaks kept, otherwise verbatim |
| `seniority`, `contract_type` | posting page criteria "Seniority level", "Employment type" (Full-time, Part-time, Contract; "Not Applicable" is left empty) |
| `work_mode`, work-mode detail | read by the agent from the title and description (L6) |
| `published_salary` | only when the card or description states a pay figure |
| `language` | language of the description |
| `form_questions` | not visible without applying; never recorded |

### L6. Work mode is the agent's reading, not a pattern
LinkedIn shows visitors no work-mode field, so the agent reads the title and
the complete description and decides onsite, remote, or hybrid, with judgment
rather than keyword matching (a "Remote" in a benefits list or a similar-jobs
title is not the posting's mode). When the posting says more, the agent
writes the work-mode detail in the posting's language and close to its words
("Híbrido: 2 días presencial por semana", "Summer hours: Fridays until noon").
When nothing is stated, both stay empty and the posting gets the flag "work
mode not stated"; the first-pass filter of `/job-search` does not exclude it
for work mode. The user can fill it in from the panel after opening the
posting.

### L7. Job sites are off until the user turns them on
`providers.with_state` treats a provider with no row in `providers_state` as
disabled. Nothing else changes in the mechanism: `jt run start` already lists
disabled providers with reason `disabled` and never queries them, `jt doctor`
already checks dependencies only for enabled providers, and the panel toggle
and `jt providers enable|disable` already write the row.

Skills follow: `/setup` step "Job sites" shows the available providers (with
access, login, live walk, and the file's terms note when it has one), and runs
`jt providers enable <id>` for each one the user picks, instead of disabling
the rest. `/job-search`, when no provider is enabled, names the providers that
exist and says they are turned on in `/setup` or the Search tab's job-site
toggles; it never turns one on itself.

No migration: no user has a provider row yet (no provider files existed), and
a stored choice, on or off, is kept as it is.

Alternatives: an `enabled_by_default` field in each provider file (lets a
contributor ship a site turned on, which is exactly what must not happen);
keep the default on and rely on `/setup` (an update would still start new
searches the user never chose).

### L8. Captures
Each search page and posting page is saved to the run's capture folder as
`linkedin-<n>.txt` (raw HTML), as the job-search skill requires, for audit.

## Risks / Trade-offs

- [LinkedIn throttles or blocks the user's IP] → small caps, 5 s pacing, stop
  on the first sign; the run continues with other providers; the user can
  switch LinkedIn off in the panel.
- [Terms of use forbid this access, including for logged-out visitors] →
  stated in the provider file so the user decides; no evasion techniques; the
  user's account is never involved.
- [Without work-mode or contract filters, more off-target postings are read]
  → bounded by the caps; the first-pass filter excludes them with a reason.
- [The HTML classes change] → the recipe names what to look for; a mismatch
  is recorded as `failed --reason error` and `last_verified` shows how old the
  recipe is.
- [Posting pages re-opened on every run] → bounded by the caps; a lookup of
  known postings by external id would remove it but needs CLI code, so it is
  left for a later change if the cost proves real.
- [Relevance order] → the age filter keeps results inside the window; the
  newest postings beyond 3 pages are missed.

## Migration Plan

Adding the file makes LinkedIn appear in `jt providers list`, `/setup`, and
the panel, switched off. Nothing runs until the user turns it on. Rollback:
delete the file; restoring the old default is a one-line revert.
