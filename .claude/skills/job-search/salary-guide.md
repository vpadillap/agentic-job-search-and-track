# Salary research guide

The salary of a posting is **your analysis**, not a count: you get everything
available, search only what is missing, and propose a monthly range to ask for
with a short note that justifies it. Every figure rests on cited sources (the
user's own data or linked reports). Never estimate from your own knowledge, and
never convert across countries, currencies, or gross/net.

## 1. Gather: `jt salary lookup <posting_id>`

It searches nothing and returns:

- `offered`: what the posting itself publishes, as monthly figures (shown to
  the user as "Offered"). It is not a suggestion.
- `posting.profile`: the company's profile (industry, size band, type), or
  null when nobody recorded it yet.
- `history`: the user's own data, the same company first: salaries **offered
  to the user** (`kind: offer`, recorded on applications) and salaries
  **published** in stored postings (`kind: published`), each with its company,
  `profile`, title, level, country, work mode, date, and whether it is the same
  company (`same_company`) and the same role family (`same_family`).
- `evidence.company`: stored reports for this company and role family in this
  country (fresh for 60 days); `evidence.market`: stored reports for this role
  family, level, and country at any company (fresh for 30 days);
  `evidence.earlier`: older evidence for the same job.
- `checked`: which sources were already searched for these keys, found or
  not. Do not search them again.
- `current`: the suggestion stored now, if any.

## 2. Company profiles

To compare companies you need their profiles. When a posting's company has no
profile, record what you can **from the posting's text** (`source: "posting"`)
or from a linked page (for example its company page on a job site):

`jt companies profile "<company>" -` with
`{"industry": "Banking", "size_band": "1,001-5,000 employees", "kind": "bank",
"source": "Example Jobs company page", "source_url": "https://…"}`.

Anything you cannot support stays out (or `"unknown"`). Never fill a profile
from what you believe about a company. Do the same for the companies of the
history items you will rely on when their `profile` is null.

## 3. Search only what is missing

In this order, skipping every source listed in `checked`:

1. **References for the same company** (for example Glassdoor's reports for
   that company and role). Store them with `"scope": "company"`. When a source
   shows several reports, decide what is normal; you may set aside reports far
   from the rest and record why (step 5).
2. **The market**: the same role family and level in the same country, at
   comparable companies. Store with `"scope": "market"` (the default).

**Salary sources are always available**: they are never switched on or off
(a job site's switch is about searching its postings only). `jt salary lookup`
lists in `sources` every salary source that serves the posting's country,
with `ready` (its tools are installed), `reader`, and `checked` (what it
already answered for this posting's keys). Ask the ones that fit the posting
(its country, its language for titles, company references before market
data), skip the ones already checked, and follow the "Salary data" section of
each one's file. When `ready` is false, run `jt providers install <id>` first;
never ask the user to install anything. Each source has a **salary reader** (for
example `jt providers salary indeed --title "<title>"`): it returns an `evidence`
draft from the site's own data. Add only what you decide (`basis`, `level`,
`scope`, `posting_id` or `research`, context fields), check that it is
comparable, and store it with `jt salary evidence add -`. Never change its
figures. `"data": false` → record it as checked with `found: false`. Read the
reader's `warnings` (a very wide range, a small sample, an old or missing
update date): such a figure is weak evidence; set it aside with the reason
or use it as supporting only.
`"throttled": true` → the site was not checked: do not record it, do not call
it again before `resume_after`, and tell the user.

Record what you searched, found or not, in `checked` of `salary set` or
`salary none` (`{"source": "Glassdoor", "scope": "company", "found": false}`),
so the next posting with the same key does not search it again.

```json
[{
  "posting_id": 12, "scope": "company",
  "source": "Site name", "url": "https://…",
  "summary": "Senior Data Engineer · same company · 4 reports",
  "amount_min": 14000, "amount_max": 16500, "currency": "PEN", "basis": "gross",
  "period": "month", "sample_size": 4, "observed_on": "2026-10-01",
  "country": "PE", "level": "Senior",
  "work_mode": "remote", "industry": "Retail", "company_size": "1,000+"
}]
```

`period` is `month` or `year` (yearly is divided by 12); skip other periods.
`observed_on` is the date of the report, not today.

## 4. Analyse

Weigh what you have:

- **The same company weighs most**: its references, what it offered the user,
  what it published.
- Otherwise, which is the usual case, **extrapolate from similar companies**:
  the same industry, a similar size band and type, the same level, country,
  currency, basis, and work mode. Say which attributes make them similar, and
  say when the comparison rests on few known attributes.
- Offers the user received are strong evidence of what similar companies pay
  them; published salaries show what companies offer for the role.
- The market fills what the user's own data does not cover.

A source counts only with the same country, level, currency, and basis, and
no older than 18 months; the CLI says which ones fail and why.

## Currency

The project serves every country, and salaries are not always in the local
currency. Choose the currency of each suggestion (`criteria.currency`, any
ISO code):

1. the currency the posting publishes, when it publishes one;
2. otherwise the one this employer pays in for this country: the local
   currency for a local employer; often USD (sometimes EUR) for a foreign
   employer hiring remotely, or for a contract paid abroad;
3. when it is not the local currency, say why in the note ("a US company
   hiring remotely: USD").

Evidence counts only in the same currency: never convert. If the sources are
in another currency than the one that fits, say so in the note or record
`salary none`. The user records the salaries they asked for and were offered
in whatever currency they were discussed; the form prefills the most likely
one.

## 5. Record

**A suggestion**: `jt salary set <posting_id> -`

```json
{
  "criteria": {"currency": "PEN", "basis": "gross", "industry": "Banking",
               "company_size": "1,001-5,000"},
  "range_min": 13000, "range_max": 15500,
  "inputs": [
    {"kind": "offer", "application": "J0007", "weight": "main"},
    {"kind": "published", "posting_id": 31, "weight": "supporting"},
    {"evidence_id": 54, "weight": "main"}
  ],
  "set_aside": [{"source": "Glassdoor", "value": "45,000 PEN",
                 "reason": "three times the other six reports"}],
  "note": "Close to what two similar large banks offered you (2026) and to Glassdoor's 7 reports for this company; one far above the rest set aside.",
  "checked": [{"source": "Glassdoor", "scope": "company", "found": true}]
}
```

- **The evidence rule**: at least one input. One is enough when it is a
  reference for the same company (`scope: company`) or from the user's
  history (`offer`, `published`). When every input is market evidence, at
  least two comparable ones are needed. The CLI refuses otherwise.
- `note`: one or two sentences, at most 300 characters, in the panel
  language: what the range rests on, how many sources of which kind, what was
  set aside. The user sees it next to the range.
- `weight`: `main` or `supporting`. Without `amount`, the CLI takes the median
  of the main inputs within your range.

**No reliable data**: `jt salary none <posting_id> --checked "Glassdoor: no
reports for this company" --checked "Example Salaries: one report, other
level"`.
