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

The results go into this proposal and the design as a table (route →
result), and the owner chooses the route before section 2 starts.

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
