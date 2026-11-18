## Context

`access: web-search` is already an allowed access method in
`core/providers.py`, but no provider uses it. Providers without a reader are
already supported by `/job-search`: the agent follows the file and imports
records with `jt postings import`. The import already de-duplicates by
provider + external id and flags possible duplicates across providers.

## Goals / Non-Goals

**Goals:** openings published on companies' own channels and reputable sites
without a provider file; clear, checkable rules for which sources are used;
bounded effort per run.

**Non-Goals:** a crawler; reading sites that already have a provider file
(they are searched by their own provider, or not at all if the user turned
them off); signing in anywhere; storing discovered companies.

## Decisions

### D1. Instructions, not code

The recipe lives in the provider file and is binding like any other. The
agent uses Claude Code's web search and web fetch tools (or the browser
extension only when a careers page needs JavaScript and the user is present).
No reader is written.

### D2. Sources the user turned off stay off

The agent never reads a domain that belongs to a provider file (LinkedIn,
Indeed, Bumeran, Glassdoor, Greenhouse, …), whether that provider is enabled
or not: enabled ones are searched by their own recipe; disabled ones were
turned off by the user. A posting found only on such a domain is skipped.
Company ATS boards (for example `job-boards.greenhouse.io/<company>`) count as
the provider's domain once that provider exists.

### D3. Records

`provider` = `agentic-search`; `external_id` = the canonical URL of the
posting without tracking parameters; `url` = that URL; `source_site` = the
site's host (e.g. `careers.example.com`). `posted_at` only when the page states
it; otherwise empty and a flag "publication date not shown" (panel language).
A posting whose page says it is closed is not imported.

### D4. Budget

Front matter `max_results_per_query: 40` (postings per title) and
`min_seconds_between_requests: 3`. The recipe adds a cap of 15 companies
expanded per title. When a cap is reached the agent stops and says so in the
run report.

### D5. Reputation rules (in the provider file)

Allowed, in order of preference: the company's own careers page; the
company's applicant-tracking board; government or university job portals;
established national or professional job sites. Not used: aggregators that
republish others' postings (use the original instead), pages without a
company name, pages that ask for payment or personal data to show the
posting, postings older than the run's window when the date is shown.

## Risks / Trade-offs

- [Web search results vary between runs] → Accepted; the import's seen and
  duplicate logic keeps the panel consistent.
- [Careers pages built with JavaScript] → Web fetch may see no postings; the
  agent records the company as "not readable" in the capture file and moves
  on.
- [Cost and time] → Budget caps in D4.
