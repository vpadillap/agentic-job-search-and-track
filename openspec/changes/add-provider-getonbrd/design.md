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

### D3. Get on Board: a plain-HTTP reader over the public API

`readers/getonbrd.py`, standard library only, injectable `get(url)`.
`providers/getonbrd.md`: `regions: [global]`, `access: http`,
`dependencies: []`, no login, `max_results_per_query: 60`.

```
jt providers read getonbrd <run_id> --title "<title>"
```

Per title, two searches (`GET /api/v0/search/jobs`, `per_page=120`,
`expand=["company","seniority","modality"]`, `lang` from the panel):

1. `query=<title>&country_code=<profile country, lowercase>`: postings in the
   country and remote postings open to it (the API applies the scope);
2. `query=<title>&remote=true`: postings remote from anywhere
   (`fully_remote`), which the country search leaves out.

Merged by posting id; more pages (`page=2…`) only while new postings in the
window keep coming and the cap is not reached. Without a profile country,
only the second search runs and the summary says so.

Kept: title matches (seniority words aside, as Greenhouse's matcher, shared),
`published_at` inside the window, not handled in this run, not stored by an
earlier run (then seen).

### D4. Get on Board drafts

`external_id` = the API `id` (a slug); `url` = `links.public_url`; `title`;
`company` = the expanded company name; `location` = the posting's countries
and cities as given ("Remote" for remote postings); `country` = the profile's
country; `posted_at` = `published_at`'s date; `description` = the sections in
the site's order, each headline followed by its text as plain text
(`description`, `projects`, `functions`, `desirable`, `benefits`); hints
`site_remote` (`remote_modality`), `site_seniority`, `site_modality`
(full time…), `site_salary` (`{min, max}` as given; the API does not state
the currency, so the agent decides it from the description or records it
with a flag), `site_perks`, `site_category`. Work mode, contract type,
language, flags, and the published salary are the agent's reading.

Terms (D7 of the proposal's study): "Get on Board" is the provider name shown
next to each posting, the panel links each posting to its page and shows the
date it was read; the provider file states the terms, including the 24-hour
clause accepted as personal use.

### D5. Stop rules for Get on Board

Blocked: 403 or 429. Error: an answer that is not the expected JSON
(`data` list), three in a row. A search with no results is not an error.

### D6. Bumeran and Indeed move to a headless Scrapling session

Both readers keep their logic (URLs, captured data, side-panel clicks,
parsing, pacing, stop rules); only the browser adapter changes, from a
visible Playwright Chromium to `scrapling.fetchers.StealthySession(headless=
True, solve_cloudflare=True, locale=…)`, one session per call:

- **Bumeran**: the response listener is attached before each page loads
  (`page_setup`) and the page action waits for `searchV2` /
  `fichaAvisoNormalizada` as the current adapter does.
- **Indeed**: the search page is loaded once per results page; the page action
  runs the current side-panel clicks (`a.jcs-JobTitle[data-jk]`, wait for
  `vjk=<id>` and `.simple-job-description-html`). Posting pages (`/viewjob`)
  stay unused (slow under Scrapling, sign-in without it). The second results
  page asked to sign in under Scrapling, so the reader treats a sign-in page on
  page 2 as the end of the results for that title (not a block) and says so
  in the summary.

Provider files: `access: scrapling`, `dependencies: [scrapling]`; "A browser
window opens" becomes "no window opens"; the forbidden list keeps "the user's
account or browser" and drops "a headless browser" (allowed now through
Scrapling). Users who had Playwright only: `jt doctor` names the install
command for Scrapling (as for Glassdoor); the old Playwright adapters are
removed, there is no fallback. Tests keep using fake browsers; the adapter
change is checked by a real run.

### D7. The agentic web search

`providers/agentic-search.md` gains the Get on Board row in "Sites you never
read here" (`getonbrd.com`).

## Open Questions

None after the owner's decisions of 2026-11-18.

## Risks / Trade-offs

- [The site changes its pages or API] → stop rules name what is missing; the
  provider is revisited in its own change.
- [Terms restrict automated access] → stated in the provider file before the
  user turns it on; the owner decides with the study.
