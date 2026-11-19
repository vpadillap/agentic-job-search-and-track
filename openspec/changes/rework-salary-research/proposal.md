## Why

The salary column shows one thing: a suggestion built from two comparable,
linked sources, or "no reliable data". In practice the agent researches each
posting on its own: the evidence cache reuses data only when company, role,
and location all match (60 days), so market data for a role (role, level,
country) found for one company is never reused for the next company, and the
same Glassdoor and web searches are repeated for every posting. And what a
job seeker needs is an informed suggestion, not only a count of sources. The
owner wants the agent to analyse everything available (including what similar
companies offered the user), search only what is missing, justify its
suggestion in a short note, reuse what it already found, and more salary
sources studied and added over time.

## What Changes

### The agent analyses, then suggests with a short note

The salary research becomes the agent's analysis, not a rule applied posting
by posting:

1. **It gets all the data available** for the posting, gathered by one
   command: the salary the posting offers (monthly); the user's own history,
   meaning salaries **offered to the user** (recorded on applications) and
   salaries published in stored postings, each with its company's profile
   (industry, size, type), level, country, work mode, and date; and the
   salary evidence already stored and still fresh for the posting's keys
   (below).
2. **It searches only what is missing**: the same company's salary references
   on the web first (for example Glassdoor's reports for that company and
   role), then the market (similar positions and industries, same country and
   level) from the salary sources; never a source already checked for the same
   key recently.
3. **It proposes a suggested range with a short note** that justifies it in
   one or two sentences, for example: "Close to what similar large banks
   offered you (2 offers, 2026) and to Glassdoor's reports for this company (7
   reports; one far above the rest set aside)". Data from the same company
   weighs more; otherwise the agent extrapolates from **similar companies**
   (industry, size, type, level), which is the usual case, and says so.

The salary column shows the **offered** salary when the posting has one, and
the **suggested** range with its note and how many sources of which kind
support it; the detail lists every input it used (each history item and web
source, with its link or reference), what was set aside and why.

**The evidence rule** (owner's decision, 2026-11-19; `AGENTS.md` rule 3
changes accordingly): every suggestion cites at least one source. When it
rests on references for the same company or on the user's own history, one
source can be enough, and the note says how many and what kind. When it rests
only on the market, at least two comparable sources are needed, as today.
Without any source: "no reliable data", with what was checked. Nothing comes
from the model's own knowledge.

### Company profiles

To compare companies, each company the user meets gets a short profile:
industry, size band (for example "1,001–5,000 employees"), and type (bank,
consultancy, outsourcing, startup, public sector…), taken from the posting's
own text or from a source with a link (for example the company's page on a
job site); otherwise "unknown". The agent fills it in when it reads a posting
or researches a salary, through the CLI; it is reused for every later posting
of that company.

### Research once, reuse everywhere

- **Market evidence** is kept by role family, level, country, and currency
  and reused for every posting that matches, whatever the company, for a
  limited period (30 days, configurable later).
- **Company evidence** is kept by company, role family, and country (60
  days).
- **"Nothing found"** is remembered the same way, so the agent does not search
  again for the same key in that period.
- The agent groups a run's postings by these keys and researches each key once
  per run, not once per posting.

### More salary sources

A study, logged out with real requests, of salary sources for Peru first and
the other countries the job sources cover: Indeed's salary pages,
Computrabajo, Bumeran, Payscale, Talent.com, SalaryExpert, Levels.fyi (tech),
official occupational data (for example Peru's labour ministry), and published
salary surveys. Each source chosen by the owner becomes a provider file
(`kind: salary` or `both`), with a salary reader when it is mechanical, and
says whether it gives company-level data (for a) or market data (for b).
Sources can keep being added later the same way, including through
`/add-provider`.

#### Study results (2026-11-19; Peru, "data engineer", logged out, plain HTTP)

| Source | Answer | What it gives | Scope | Notes |
|---|---|---|---|---|
| Indeed salaries (`pe.indeed.com/career/<title>/salaries`) | 200, data in the HTML and in structured data | average and typical range, sample ("50 salaries taken from Indeed postings"), country | market (role, country; no level) | The Spanish text says "S/ 61,698 por mes" while its structured data says per **year**: the reader must take the period from the structured data. Cheapest to read |
| Computrabajo (`pe.computrabajo.com/salarios/<title>`) | 200, page without the figure | median per month and the number of salaries it is based on, filled in by JavaScript | market | Needs the browser (Scrapling, as Bumeran) |
| Bumeran (`/salarios`) | 200, application shell | — | — | Needs the browser; not studied further |
| Glassdoor | 403 by plain HTTP | company and role reports (already a salary reader with Scrapling) | company and market | Already integrated |
| SalaryExpert | 403 (bot wall) | estimates by job and country | market (modelled, not reported) | Modelled figures; weak evidence |
| Levels.fyi | 405 (bot wall) | tech compensation by company and level | company | Little coverage for Peru |
| Payscale | 404 for Peru | — | — | No Peru page at the usual address |
| Talent.com | 404 for this query | — | — | Address format to be found |
| Ponte en Carrera (MTPE, official) | 200, JavaScript redirect | salaries by occupation | market (occupation, not title or level) | Needs the browser to study |

Recommendation: add **Indeed salaries** first (plain HTTP, sample size, a
reader is simple; period from the structured data) and **Computrabajo** second
(Scrapling). Leave SalaryExpert, Levels.fyi, Payscale, and Talent.com out for
Peru; study the official data later with the browser. The owner chooses.

## Capabilities

### New Capabilities

- One `provider-<source>` capability per salary source the owner chooses
  after the study.

### Modified Capabilities

- `salary-suggestions`: the agent's analysis of all available data with a
  justifying note; the evidence rule per kind of source; outliers recorded;
  evidence reused by role and country; company profiles.
- `search-results-board`: the salary column shows the offered salary and the
  suggestion with its note; the detail lists every input.

## Impact

- `core/salary.py` (keys and reuse, the user's history with company profiles,
  the evidence rule per kind, set-aside records, the note), a migration
  (company profiles; scope, role family, and level on evidence; set-aside
  reasons; the suggestion's note and kinds of sources), CLI (`jt salary
  lookup` returns everything available; `jt salary set` takes the note;
  `jt companies profile` records a company's profile), `AGENTS.md` rule 3, the salary guide and `job-search` skill, the Search board's
  salary cell and detail (en/es), new provider files and readers after the
  study; tests.
