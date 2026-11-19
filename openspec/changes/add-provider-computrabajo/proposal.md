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

### Study results (2026-11-19; logged out, plain HTTP, 6 s or more between requests)

| Check | Result |
|---|---|
| Search page `/trabajo-de-<title>` | 200 over plain HTTP in PE, MX, CO, CL, AR, EC; 20 results per page in `<article data-id='<id>'>` cards: title and link, company, place, work mode ("Presencial y remoto"), relative date ("Hace 2 horas", "Ayer"), salary when stated ("$ 15,000.00 (Mensual)") |
| Filters | `?pubdate=1/3/7/15/30` (today to last month), `?by=publicationtime` (newest first), `?p=2` (next page: 20 more, no repeats in CO) |
| `robots.txt` | Disallows parameters only under `/ofertas-de-trabajo/` (and `/empresas/`, CVs, Ajax); the search addresses with `pubdate`, `p`, `by` and the posting pages without parameters are allowed |
| Posting page | 200 over plain HTTP; `JobPosting` structured data in every country: title, company, place and country, `datePosted`, `employmentType`, `industry` (the posting's category), `baseSalary` with currency and period (`0` when "A convenir"; the list's stated salary matches it), and the complete description (1,200–3,600 characters) |
| Dates | The list's relative date can be newer than `datePosted` (a republished posting: "Hace 2 horas" for one posted four days earlier); `datePosted` is the one to keep |
| Blocks | None in about 20 requests across six countries; no browser check over plain HTTP |
| Application questions | Applying needs an account (`candidato.<country>.computrabajo.com`): questions are not visible logged out |

Recommended route: **plain HTTP** (no browser), search with `pubdate` set
from the run's window and `by=publicationtime`, paging with `p` until the
window or the provider's cap ends, then each new posting's page for its
`JobPosting` (the description and the stated salary). Work mode from the
card ("Presencial y remoto" seen; the label of a fully remote posting is to be
confirmed while building) as a hint for the agent's reading. Pacing as for the other readers (at least 5 s), with
the shared throttle handling.

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
