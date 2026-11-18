# Salary research guide

A salary suggestion is a monthly figure backed by at least two comparable,
linked sources. Without them the answer is "no reliable data". Never
extrapolate across countries, levels, currencies, or gross/net, and never
estimate from your own knowledge.

## Where to look, in order

1. The posting itself: a published salary counts as one source (record it
   with `"from_posting": true`, the posting URL, and the posting date).
2. Reports for the same company and role.
3. Reports for the same role and level in comparable companies (same country,
   similar industry and size).

Use only the salary sources the enabled provider files describe (`kind:
salary` or `both`), following their instructions.

Some providers have a **salary reader** (their file says so, for example
`jt providers salary glassdoor --title "<title>"`). It returns an `evidence`
draft taken from the site's own data: source, URL, range, currency, period,
sample size, date, country. It is **one** source. Add only what you decide
(`basis`, `level`, `posting_id` or `research`, and the context fields below),
check that it is comparable, and store it with `jt salary evidence add -`.
Never change its figures. When it answers `"data": false`, list that site in
`--checked` if you end with `jt salary none`.

## What makes a source comparable

The CLI counts a source only when all of these hold, and tells you which ones
failed:

- same **country** as the posting;
- same **level** (seniority) as the posting;
- same **currency** and the same **basis** (gross or net);
- reported in the **last 18 months**.

Also record `work_mode`, `industry`, and `company_size` for every report: they
do not gate the suggestion but they set its confidence and the user sees them.

## Recording evidence

`jt salary evidence add -` with a list of reports:

```json
[{
  "posting_id": 12,
  "source": "Site name", "url": "https://…",
  "summary": "Senior Data Engineer · same company · 4 reports",
  "amount_min": 14000, "amount_max": 16500, "currency": "PEN", "basis": "gross",
  "period": "month", "sample_size": 4, "observed_on": "2026-10-01",
  "country": "PE", "level": "Senior",
  "work_mode": "remote", "industry": "Retail", "company_size": "1,000+"
}]
```

- `period` is `month` or `year` (yearly figures are divided by 12). Other
  periods are not converted: skip that report.
- A single figure can be sent as `"amount"`.
- `observed_on` is the date of the report, not today.

## Suggesting or recording the absence

- Two or more comparable sources: `jt salary set <posting_id> -` with
  `{"evidence_ids": [...], "criteria": {"currency": "PEN", "basis": "gross",
  "industry": "Retail", "company_size": "1,000+"}}`. Country and level come
  from the posting. The CLI computes the median, range, and confidence.
- Fewer: `jt salary none <posting_id> --checked "Site A: no reports for this
  company" --checked "Site B: one report, different level"`.

Evidence is reused for 60 days for the same company, role, and location; see
`jt salary lookup` in the skill.
