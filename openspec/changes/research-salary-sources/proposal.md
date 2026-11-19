## Why

A salary is suggested only with two comparable, linked sources (same country,
level, currency, basis, last 18 months). Today the agent has two kinds: a
salary the posting itself publishes, and Glassdoor's salary pages. For many
titles and countries that is not enough, so the panel shows "no reliable
data" more often than it should. The owner wants more salary sources studied
and integrated, without lowering the two-source rule.

## Study (first section; nothing is built before it)

For Peru first, then the other countries the job sources cover, each source
tried with real requests, logged out, and recorded as a table (source → what
it gives, how it is read, sample size, recency, level and currency, terms):

1. **Salary sites**: Indeed's salary pages (`/career/<title>/salaries`),
   Computrabajo's salary pages, Bumeran's salary content, Payscale,
   Talent.com, SalaryExpert, Levels.fyi (tech), and others the study finds.
2. **Official and survey data**: Peru's labour ministry occupational data
   (for example "Ponte en Carrera" salary by occupation), national statistics,
   and published salary surveys (for example Get on Board's or a recruiter's
   yearly study), with their dates.
3. **Postings already stored**: published salary ranges in the user's own
   captured postings (Get on Board ranges, Bumeran and Indeed published pay)
   for the same title, level, and country, as evidence that is already
   comparable and linked.
4. **Integration options**: a salary reader per source (as Glassdoor's), a
   `kind: salary` provider file the agent follows, or evidence computed from
   stored postings; how each fits `jt salary evidence add` and the
   comparability checks.

The results go into this proposal and the design; the owner chooses which
sources and how before section 2 starts.

## What Changes (expected; revised after the study)

- New salary sources as provider files (`kind: salary` or `both`), with a
  salary reader where the source is fixed and mechanical, each returning
  evidence drafts the agent checks, as Glassdoor does.
- Possibly a command that builds evidence from the user's stored postings with
  published salaries (same title family, level, country, currency, recent).
- `job-search` salary guide: the order of sources and how many to try before
  "no reliable data".
- The two-source rule and the comparability checks stay as they are.

## Capabilities

### New Capabilities

- One `provider-<source>` capability per salary source chosen (named after
  the study).

### Modified Capabilities

- `salary-suggestions`: more kinds of evidence (expected; revised after the
  study).

## Impact

- `providers/<source>.md`, readers, salary guide, tests with fictional pages;
  a real check per source. Decided after the study.
