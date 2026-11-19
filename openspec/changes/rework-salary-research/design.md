## Context

`core/salary.py` stores evidence (`salary_evidence`: source, URL, range,
currency, basis, period, sample size, date, country, level, context) keyed for
reuse by `research_company/role/location`; a suggestion (`salary_suggestions`)
needs two comparable items (country, level, currency, basis, 18 months);
`lookup` reuses evidence only for the same company, role, and location (60
days). The Search board's salary cell shows the suggestion or "no reliable
data". Glassdoor has a salary reader (`jt providers salary glassdoor`).

## Goals / Non-Goals

**Goals:** the three figures a job seeker needs; research done once per key
and reused; company data before market data; every figure traceable.

**Non-Goals:** figures from the model's own knowledge; converting currencies;
paid sources or sources that need the user's account.

## Decisions

### D1. Three parts, three kinds of record

- **Offered** — the posting's `published_salary`, shown as monthly (yearly ÷
  12, as today). No new storage.
- **Company history** — computed on demand: the user's stored postings of the
  same company (normalized name), same title family (D3), level within one
  step, same country and currency, with a published salary; shown as a range
  with the number of postings and the latest date. No new storage.
- **Suggested range** — a `salary_suggestions` row with `kind`:
  `company` (from company references; one source allowed, shown as "1
  source" or "N sources") or `market` (two or more comparable sources, as
  today). Evidence rows gain `scope` (`company` or `market`).

### D2. Order and the agent's judgment

For a posting without a reusable suggestion: (a) company references, from the
salary sources that give company-level data (Glassdoor's company salaries
first); the agent reads all reports of the source, decides the normal range,
and may set reports aside as outliers, recording each with its reason
(`set_aside: [{value, reason}]` on the evidence); (b) only if (a) finds
nothing, market evidence, at least two comparable sources. Both are stored;
the suggestion records its kind and the evidence used.

### D3. Keys and reuse

- Title family: the title lowercased, accents removed, seniority words
  removed (the shared `title_matches` words), so "Senior Data Engineer" and
  "Data Engineer II" share "data engineer".
- Market key: (title family, level, country, currency); reused 30 days.
- Company key: (company, title family, country); reused 60 days.
- "No data" is logged per key and source; a key with a recent "no data" for a
  source is not searched again in that period.
- `jt salary lookup <posting>` returns: offered, company history, a reusable
  company suggestion or market evidence for the posting's keys, and which
  sources were already checked for each key.
- The skill groups a run's postings by key before researching, so one key is
  researched once per run.

### D4. Board

The salary cell shows up to three short lines: "Offered 4,000–6,000 PEN",
"This company: 4,500–5,500 PEN (3 postings)", "Ask: 5,000–6,500 PEN (company,
1 source)" or "(market, 3 sources)". The detail lists every source with its
link, what was set aside and why, and the dates. When none exists: "No
salary data" with what was checked.

### D5. Study of new sources (before implementing them)

Sources tried logged out with real requests, recorded as a table: what each
gives (company-level or market), how it is read, sample size, recency, level,
currency, terms. The owner chooses which become provider files; each is added
like a job site (provider file, reader when mechanical, tests on fictional
pages, real check). The rework of the column and the cache (D1–D4) does not
wait for new sources: it works with the posting, the company history, and
Glassdoor.

## Risks / Trade-offs

- [A single company source can be unrepresentative] → It is labelled "1
  source", its sample size is shown, and the market range can be shown next to
  it when known.
- [Title families merge different roles] → The family is shown in the detail;
  the agent can record that a source does not fit.
- [Reused market data ages] → 30-day reuse, 18-month evidence limit as today.
