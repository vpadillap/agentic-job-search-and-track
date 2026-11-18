## Why

Get on Board (getonbrd.com) is a job board focused on technology roles in
Latin America, with many remote postings open to the region. It appeared in
the web searches of the Glassdoor, Greenhouse, and agentic-search studies
(for example "Senior Data Engineer" postings in Lima), and it has no provider
file yet, so today it is only reachable as one more site of the agentic web
search. The owner wants it as a provider of its own. How it is read is not
known yet: it is decided by a study inside this change, as for every
provider.

## Study (first section of this change; nothing is built before it)

Logged out, with real requests, scratch scripts only, at a person's pace:

1. **Public structured data.** Does Get on Board offer a public API or
   embedded structured data for searches and postings (JSON, JSON-LD)? Which
   address, which filters (title or keywords, country or remote, posting
   date), how many results per page, how paging works, and whether the
   complete description comes with it. Any address found in write-ups is
   verified with a real request before it is used.
2. **Pages.** If there is no usable structured source: the search page and
   a posting page over plain HTTP, then a headless browser, then a visible
   browser; what each one returns and whether any check or sign-in appears.
3. **Fields.** Where each posting's id, link, title, company, location and
   remote terms, publication date, salary (the site often states a range),
   seniority, and complete description come from; whether application
   questions are visible without applying (never start an application).
4. **Coverage.** Which countries the site serves and how a posting states
   its country or remote scope; whether the provider is global (`[global]`)
   or local to a list of countries, each verified (dated `## Countries` row).
5. **Terms of use** and `robots.txt`, recorded with the date read.
6. **Scrapling** (owner's addition): the same search and posting through
   Scrapling's fetchers, compared with the other routes in time per title and
   in what comes back.
7. **Scrapling on the existing providers** (owner's addition, study only):
   Indeed, Bumeran, and LinkedIn read with Scrapling, compared with their
   current readers (time per title, postings per title, descriptions, blocks,
   visible window or not). The results are recorded here; changing any of
   those providers is done in its own change afterwards, as `AGENTS.md`
   requires, and only if the owner decides so.

The results go into this proposal and the design as a table (route →
result), and the owner chooses the route before section 2 starts.

### Study log (2026-11-18)

| Route | Result |
|---|---|
| **Public API** `GET https://www.getonbrd.com/api/v0/search/jobs?query=<title>&country_code=<cc>&per_page=120&expand=["company","seniority","modality"]`, plain HTTP (standard library) | **200 in 1.7 s, no key, no check**: "data engineer" in Peru → 13 postings, each with the complete description in sections (`description`, `projects`, `functions`, `benefits`, `desirable` with their headlines, HTML), `title`, `published_at` (epoch), `remote`, `remote_modality` (`remote_local`, `fully_remote`, `hybrid`, `no_remote`), `countries`, `min_salary`/`max_salary` (7 of 13), `perks`, `category_name`, and, expanded, company name, seniority ("Semi Senior"), modality ("Full time"); `links.public_url` is the posting page. `meta.total_pages` for paging (120 per page) |
| Same without `country_code` | 45 postings, mostly Chile and remote; 20 of them from the last 30 days |
| Query matching | full text: "data engineer" also returns ".NET" or "Full-Stack" roles, so a title filter is needed (as for Greenhouse) |
| `GET /api/v0/jobs/<id>` | 401: needs a key (private API); not needed, the search carries everything |
| `GET /api/v0/countries` | countries worldwide (`country_code` takes any ISO code); postings are mostly Latin America and remote |
| Search page `/jobs?q=…`, plain HTTP | 200 (580 KB HTML); not needed |
| Scrapling `Fetcher` on the API | 200 in 1.2 s, same data: no gain over the standard library |
| Scrapling stealth browser on the search page | 200 in 8.4 s, 118 posting links, no descriptions: slower and less complete than the API |
| Application questions | not in the public data; never start an application |

**Terms.** The OpenAPI document (getonbrd.com/doc/openapi.yaml, read
2026-11-18): "The public API is free and needs no API key." Using it means
agreeing to Section 7.1 of the Terms: show "Get on Board" as the source and
link each job to its page (`public_url`), send applicants to Get on Board,
show job data unchanged and refreshed at least every 24 hours, and not resell
the data or train models with it. `robots.txt`: `Allow: /` for every agent,
`Content-Signal: search=yes, ai-train=no, use=reference` (no `ai-input`
signal), and training crawlers (ClaudeBot, GPTBot, CCBot…) disallowed; as
decided for Glassdoor, this tool is not a crawler.

Decision for the owner: the "refreshed at least every 24 hours" clause is
written for sites that republish Get on Board's jobs; in this tool a posting
stays as it was on the day of the search. Options: accept it as personal use,
or have the panel link to the posting page and show the date it was read.

## What Changes (expected; revised after the study)

- `providers/getonbrd.md`: coverage, the access method the owner chooses,
  recipe, fields (including the published salary as a hint when the posting
  states one), terms, stop conditions, pitfalls.
- A reader (`jt providers read getonbrd …`) if the chosen route is fixed and
  mechanical (an API or embedded data); otherwise a step-by-step recipe.
- Tests with fictional pages or responses; a real check with one title.

## Capabilities

### New Capabilities

- `provider-getonbrd`: how Get on Board is searched and read, and what is
  never done there.

### Modified Capabilities

None expected.

## Impact

- `providers/getonbrd.md`; possibly `src/jobtracker/core/readers/getonbrd.py`
  and its registry entry; tests.
- `providers/agentic-search.md`: Get on Board joins its "Sites you never read
  here" table (its test requires every provider to be listed there).
- The provider starts switched off for every user.
