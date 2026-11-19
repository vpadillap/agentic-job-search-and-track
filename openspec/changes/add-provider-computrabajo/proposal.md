## Why

Computrabajo is one of the largest job boards in Latin America, with a site
per country. The project already reads its salary pages (`rework-salary-
research`, `kind: salary`), but not its job postings. The owner wants it as a
job provider too. How its postings are read is not known yet: it is decided
by a study inside this change, as for every provider.

## Study (first section of this change; nothing is built before it)

Logged out, with real requests, scratch scripts only, at a person's pace:

1. **Search.** The search page per country (for example
   `pe.computrabajo.com/trabajo-de-<title>`): plain HTTP, then a headless
   Scrapling session; how results are listed, how many per page, how paging
   works, and which filters exist (posting date, place, remote). Its
   `robots.txt` disallows some search parameters (`pubdate=`, `sal=`,
   `cont=`…): the study records which ones the search would need.
2. **Postings.** A posting page: id, link, title, company, location and
   remote terms, publication date, contract, salary when stated, and the
   complete description; structured data (JSON-LD `JobPosting`) or page text;
   whether application questions are visible without applying (never start
   an application).
3. **Limits.** Pacing, refusals, browser checks, and how a throttle shows;
   the terms of use as far as they can be read.
4. **Countries.** The same checks in each country of its salary file (PE,
   MX, CO, CL, AR, EC), one real search each; others only if the owner asks.

The study's results go into this proposal as a table, with a recommended
route; the owner approves before anything is built.

## What Changes (expected; revised after the study)

- `providers/computrabajo.md` becomes `kind: both` with a search recipe,
  fields, limits, and pitfalls per the study, and a verified row per country.
- A reader (`jt providers read computrabajo …`) when the route is
  mechanical, writing drafts as the other readers do, with tests on
  fictional pages and a real search per country.
- README job-site tables (en/es).

## Capabilities

### New Capabilities

- `provider-computrabajo`: searching Computrabajo's postings by the route the
  study chose.

### Modified Capabilities

None.

## Impact

- `providers/computrabajo.md`, `src/jobtracker/core/readers/` (a reader),
  tests, README. Salary reading is unchanged.
