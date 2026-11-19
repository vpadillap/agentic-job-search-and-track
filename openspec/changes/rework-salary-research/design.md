## Context

`core/salary.py` stores evidence (`salary_evidence`: source, URL, range,
currency, basis, period, sample size, date, country, level, context) keyed for
reuse by `research_company/role/location`; a suggestion (`salary_suggestions`)
needs two comparable items (country, level, currency, basis, 18 months);
`lookup` reuses evidence only for the same company, role, and location (60
days). The Search board's salary cell shows the suggestion or "no reliable
data". Glassdoor has a salary reader (`jt providers salary glassdoor`).

## Goals / Non-Goals

**Goals:** a suggestion the agent justifies from all available data; research done once per key
and reused; company data before market data; every figure traceable.

**Non-Goals:** figures from the model's own knowledge; converting currencies;
paid sources or sources that need the user's account.

## Decisions

### D1. One command gathers, the agent analyses

`jt salary lookup <posting>` returns, without searching anything:

- `offered`: the posting's published salary as monthly figures;
- `history`: every salary offered to the user (`applications.offered_salary_*`)
  and every published salary of the user's stored postings, each with its
  company and company profile (D2), title, title family, level, country,
  currency, basis, work mode, date, and reference (application id or posting
  id, and the posting's link), the same company first;
- `evidence`: stored, fresh evidence for the posting's company key and market
  key (D3), with what each source found or did not find;
- `checked`: which sources were already searched for these keys and when.

The agent reads it all, decides what is comparable and how much each item
weighs (the same company more; otherwise companies of similar industry, size,
and type, the same level, country, currency, basis, and work mode), searches
only what is missing, and records the suggestion with `jt salary set`:
range, currency, basis, the items it used (history references and evidence
ids, each with its weight: `main`, `supporting`), the reports it set aside
with reasons, and a **note** of at most 300 characters in the panel language.

### D2. Company profiles

Table `company_profiles (company_key, name, industry, size_band, kind,
source, source_url, updated_at)`, keyed by the normalized company name.
`jt companies profile <company> -` records or updates it; any field may be
"unknown". The values come from the posting's text or a linked source, never
from the model's own knowledge; the source is stored. `lookup` attaches the
profile to every history item and to the posting.

### D2b. The evidence rule

`jt salary set` refuses a suggestion with no source. It accepts one source
when that source is a company reference (same company) or the user's own
history (an offer or a published salary); it requires two or more when every
source is market evidence. The suggestion stores the count of sources by kind,
shown next to the note. `AGENTS.md` rule 3 is reworded to say this.

### D3. Keys and reuse

- Title family: the title lowercased, accents removed, seniority words
  removed (the shared `title_matches` words), so "Senior Data Engineer" and
  "Data Engineer II" share "data engineer".
- Market key: (title family, level, country, currency); reused 30 days.
- Company key: (company, title family, country); reused 60 days.
- "No data" is logged per key and source; a key with a recent "no data" for a
  source is not searched again in that period.
- `jt salary lookup <posting>` returns the fresh evidence for the posting's
  keys and which sources were already checked for each (D1).
- The skill groups a run's postings by key before researching, so one key is
  researched once per run.

### D4. Board

The salary cell shows the offered salary when there is one ("Offered
4,000–6,000 PEN") and the suggested range with the count of sources by kind
("Ask 5,000–6,500 PEN · 1 company, 2 your history"); the note is shown in the
detail and as the cell's tooltip. The detail lists every input with its link
or reference, its weight, what was set aside and why, and the dates. When
there is no suggestion: "No salary data" with what was checked.

### D5. Study of new sources (before implementing them)

Sources tried logged out with real requests, recorded as a table: what each
gives (company-level or market), how it is read, sample size, recency, level,
currency, terms. The owner chooses which become provider files; each is added
like a job site (provider file, reader when mechanical, tests on fictional
pages, real check). The rework of the column and the cache (D1–D4) does not
wait for new sources: it works with the posting, the user's history, and
Glassdoor.

## Risks / Trade-offs

- [A single source can be unrepresentative] → The note and the counts say
  how many and of what kind; its sample size is shown in the detail.
- [Company profiles are incomplete] → "unknown" is allowed; the note says
  when the comparison rests on few known attributes.
- [Title families merge different roles] → The family is shown in the detail;
  the agent can record that a source does not fit.
- [Reused market data ages] → 30-day reuse, 18-month evidence limit as today.
