---
id: payscale
name: Payscale
kind: salary
regions: [global]
access: scrapling
requires_login: false
live_walk: false
dependencies: [scrapling]
domains: [payscale.com]
max_results_per_query: 1
min_seconds_between_requests: 20
last_verified: 2026-11-19
---

# Payscale

A salary source only: Payscale's salary pages per title and country. Not a job
source.

## Access method

A **headless Scrapling stealth session**, logged out: no cookies, no account,
no sign-in, a new session per call. Every page is opened by the reader
command, never by you:

```
jt providers salary payscale --title "<title>" [--title "<variant>" …]
```

A study on 2026-11-19 found the pages answer through a Scrapling session (`/research/<country>/Job=<Title_Words>/Salary`); the country code for the United Kingdom is `UK` in its addresses (the reader maps `GB`).

## Search recipe

Not a job source: no searches. See "Salary data".

## Fields to extract

Salary data only (see "Salary data").

## Application form questions

Not applicable.

## Salary data

Payscale publishes pay estimated from salary profiles its users submit, per job title and country, with base and total pay; the reader uses base pay and names total pay in the summary.

1. `jt providers salary payscale --title "<title>"` (the profile's country).
   Titles in English, as Payscale names jobs ("Data Engineer", "Brand Manager"), also in Spanish-speaking countries. Up to three variants; `tried` lists every page opened.
2. With `"data": true`, the `evidence` draft holds `amount_min`/`amount_max`
   (the 25th–75th percentile when the page gives it, else the 10th–90th),
   `currency`, `period`, `sample_size` when shown, `observed_on` (the page's
   last update), `country`, and a `summary` with the median. Figures and
   period come only from the page's structured data. It is **market** data
   for all levels.
3. Read `warnings`: a very wide range, a small sample, or an old update
   means weak evidence. The study found useless spreads where few profiles exist (Colombia, 17 profiles: 25th–75th percentile from 42 thousand to 112 million COP a year). Set such a figure aside with the reason, or
   use it as supporting only. Add `basis` (gross unless the page says
   otherwise), `level` (all levels: say so in your note), and `posting_id`
   or `research`; then `jt salary evidence add -`.
4. `"data": false` → no page or no distribution for those titles in this
   country: record it as checked with `found: false`. `"throttled": true` →
   cooling down until `resume_after`; not checked; do not call it again
   before then.

## Limits and etiquette

- **Terms of use.** Not reviewed in the study; the reader gets past the site's browser check, so the realistic risk is that the site limits the user's IP address for a while (no account is involved). Tell the user this before turning it on.
- At least 20 seconds between salary pages, also from one call to the next.
  A 429, a security page, or a 403 starts a cool-down (15, 30, then 60
  minutes), kept in the user's `provider-settings/payscale.json`. Waiting is the
  only answer to a refusal: no proxy, no changed browser, no account.
- Read only the salary pages; do not crawl the site.

## Known pitfalls

- No page exists for some countries (Peru: 404).
- Latin American pages often rest on few profiles: read `sample_size`.
