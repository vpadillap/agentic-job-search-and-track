## Why

The salary column shows one thing: a suggestion built from two comparable,
linked sources, or "no reliable data". In practice the agent researches each
posting on its own: the evidence cache reuses data only when company, role,
and location all match (60 days), so market data for a role (role, level,
country) found for one company is never reused for the next company, and the
same Glassdoor and web searches are repeated for every posting. And what a
job seeker needs to see is more than one number. The owner wants the column to
show three things, the research to follow a clear order and reuse what it
already found, and more salary sources studied and added over time.

## What Changes

### The salary column shows three things

1. **Offered**: the salary or band the posting publishes, as a monthly figure
   (unchanged source: the posting's `published_salary`).
2. **This company before**: what the same company offered for similar roles,
   from the user's own data, no web research: the salaries it published in
   earlier postings the user stored, and the salary it **offered the user**
   (recorded on an application), each marked as such, with how many and when.
3. **Suggested range**: a reasonable amount to ask for, from, in this order:
   - **a) the same company's references on the web** (for example Glassdoor's
     salary reports for that company and role). When a source shows several
     reports, the agent decides what is normal, may set aside reports far from
     the rest, and records why. **One source is enough here, and it is shown
     as "1 source"**;
   - **b) only when (a) finds nothing: the market** (similar positions, similar
     industries, same country and level), with **at least two** comparable
     sources, as today. **The user's own data comes first**: salaries offered
     to the user and salaries published in stored postings, by similar
     companies for similar positions under the same conditions (country,
     level, currency, gross or net, work mode), each counting as one source
     with its reference (the application or posting and its link). Web sources
     only complete what is missing.
   Each part says where it comes from; the detail lists every source with its
   link and what was set aside.

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

## Capabilities

### New Capabilities

- One `provider-<source>` capability per salary source the owner chooses
  after the study.

### Modified Capabilities

- `salary-suggestions`: three parts per posting, company references before the
  market, the agent's judgment on outliers recorded, and evidence reused by
  role and country.
- `search-results-board`: the salary column and its detail show the three
  parts.

## Impact

- `core/salary.py` (keys for market and company evidence, reuse, the
  company-history query, single-source company references, set-aside records),
  a migration (role family and level on evidence, set-aside reasons), CLI
  (`jt salary lookup` returns all three parts; `jt salary set` takes the kind of
  suggestion), the salary guide and `job-search` skill, the Search board's
  salary cell and detail (en/es), new provider files and readers after the
  study; tests.
