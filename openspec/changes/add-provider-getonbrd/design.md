## Context

Providers so far: LinkedIn (HTTP reader), Bumeran and Indeed (visible
Chromium readers), Glassdoor (Scrapling reader), Greenhouse (public API
reader plus discovery), and the agentic web search (recipe only). Get on
Board is a regional tech job board; it is currently reached only through the
agentic web search.

## Goals / Non-Goals

**Goals:** Get on Board postings with complete descriptions, the salary the
posting states, and the remote scope, by a route the owner chose from a real
study.

**Non-Goals:** signing in or using the user's Get on Board account; applying
or saving anything on the site; company pages and articles.

## Decisions

### D1. Study before route

No access method is decided here. The study (proposal, "Study") produces a
table of routes and results; the owner picks one; D2+ are written then.

### D2. Rules that hold whatever the route

- Logged out. No credentials through automation; if a route needs a
  sign-in, the user signs in themselves in their own browser and is present.
- Read-only; at least 5 seconds between requests for a reader (shared
  `readers/common.py`); one call at a time per run; a posting stored by an
  earlier run is not read again.
- Descriptions copied verbatim; dates only as the site states them; a
  salary the posting states is kept as a hint for the agent's reading.
- Once Get on Board has its own provider, the agentic web search never reads
  it (its "Sites you never read here" table gains the row).

## Open Questions

All of the proposal's study points. Answered in section 1 of the tasks.

## Risks / Trade-offs

- [The site changes its pages or API] → stop rules name what is missing; the
  provider is revisited in its own change.
- [Terms restrict automated access] → stated in the provider file before the
  user turns it on; the owner decides with the study.
