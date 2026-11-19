---
id: computrabajo
name: Computrabajo
kind: salary
regions: [PE, MX, CO, CL, AR, EC]
access: scrapling
requires_login: false
live_walk: false
dependencies: [scrapling]
domains: [computrabajo.com]
max_results_per_query: 1
min_seconds_between_requests: 20
last_verified: 2026-11-19
---

# Computrabajo

A salary source for now: Computrabajo's salary pages, per title and country.
Searching its job postings is a separate change (its own study); until then
it is not a job source.

## Access method

A **headless Scrapling stealth session**, logged out: no cookies, no account,
no sign-in, a new session per call. Every page is opened by the reader
command, never by you:

```
jt providers salary computrabajo --title "<title>" [--title "<variant>" …]
```

A study on 2026-11-19 found that the page's figures are filled in by
JavaScript: plain HTTP returns the page without them, so a browser session is
needed. Scrapling's browser is installed with `jt providers install
computrabajo`.

## Countries

One salary site per country (`<code>.computrabajo.com/salarios/<title>`).
Figures are monthly, in the country's currency.

| Code | Site | Currency | Last verified |
|---|---|---|---|
| PE | pe.computrabajo.com | PEN | 2026-11-19 |
| MX | mx.computrabajo.com | MXN | 2026-11-19 |
| CO | co.computrabajo.com | COP | 2026-11-19 |
| CL | cl.computrabajo.com | CLP | 2026-11-19 |
| AR | ar.computrabajo.com | ARS | 2026-11-19 |
| EC | ec.computrabajo.com | USD | 2026-11-19 |

## Search recipe

Not a job source yet: no searches. See "Salary data".

## Fields to extract

Salary data only (see "Salary data").

## Application form questions

Not applicable: no postings are read here yet.

## Salary data

Computrabajo publishes the median salary per title and country, estimated
from salaries companies, users, and employees reported in the last 12 months,
with the number of salaries behind it, the lowest and highest, and the median
at companies it lists for that title. It is **market** data with no
seniority level.

1. `jt providers salary computrabajo --title "<title>"` (the profile's
   country). Titles are in **Spanish**, as people name the job ("analista de
   datos", "jefe de marca"). Specialised titles often have no data: give up to
   three titles, from the posting's own title to the closest common one, for
   example `--title "ingeniero de datos" --title "analista de datos"`. The
   answer's `tried` lists every page opened.
2. With `"data": true`, the `evidence` draft holds the median as both
   `amount_min` and `amount_max`, `currency`, `period: month`,
   `sample_size`, `observed_on` (the page's last update), `country`, and a
   `summary` with the lowest and highest. `companies` lists the median and
   sample for that title at each company the page shows: when one of them is
   the posting's company, it is a **company** reference (store it as a second
   draft with `scope: company`, the same URL, and that company's figures).
3. Add what only you decide: `basis` (Computrabajo does not say; treat it as
   gross unless the page says otherwise), `level` (the page covers all
   levels: compare it with the posting's level and say so in your note), and
   `posting_id` or `research`; then `jt salary evidence add -`.
4. With `"data": false` and no `throttled`, Computrabajo has too few salaries
   for those titles: record it as checked with `found: false`.
5. With `"throttled": true`, Computrabajo is cooling down until
   `resume_after`; it was **not checked**. Do not call it again before then.

## Limits and etiquette

- **Terms of use.** On 2026-11-19 its `robots.txt` did not disallow the
  salary pages (`/salarios/…`), and its terms pages
  (`/condiciones-de-uso`, `/terminos-y-condiciones`) showed no rule on
  automated access in the text a plain request returns; that check is not
  conclusive. The reader still gets past the site's browser check, so the
  realistic risk is that Computrabajo limits the user's IP address for a
  while (no account is involved). Tell the user this before turning it on.
- At least 20 seconds between salary pages, also from one call to the next.
  A 429, a security page, or a 403 starts a cool-down (15, 30, then 60
  minutes), kept in the user's `provider-settings/computrabajo.json`. Waiting
  is the only answer to a refusal: no proxy, no changed browser, no account.
- Read only the salary pages; do not crawl the site.

## Known pitfalls

- "No hay suficientes datos para mostrar salarios" means no figure for that
  title: the page still names a large number of "fuentes", which is the
  site's total, not this title's sample.
- Figures cover every level: a junior-heavy title can sit well below a
  senior posting's range.
- Title pages use the words of the title (`/salarios/analista-de-datos`); an
  English title rarely has a page.
