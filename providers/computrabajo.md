---
id: computrabajo
name: Computrabajo
kind: both
regions: [PE, MX, CO, CL, AR, EC]
access: scrapling
requires_login: false
live_walk: false
dependencies: [scrapling]
domains: [computrabajo.com]
max_results_per_query: 60
min_seconds_between_requests: 5
last_verified: 2026-11-19
---

# Computrabajo

A job site and a salary source, with one site per country. Postings are read
over plain HTTP; salary pages through a headless Scrapling session.

## Access method

Logged out: no cookies, no account, no sign-in. Every page is opened by the
reader commands, never by you:

```
jt providers read computrabajo <run_id> --title "<title>"
jt providers salary computrabajo --title "<title>" [--title "<variant>" …]
```

- **Postings**: plain HTTP. A study on 2026-11-19 read the search and posting
  pages in all six countries this way, with no browser check.
- **Salary pages**: a headless Scrapling session, because their figures are
  filled in by JavaScript. Scrapling's browser is installed with `jt
  providers install computrabajo`.

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

`jt providers read computrabajo <run_id> --title "<title>"`, once per
included title, in the profile's country (the whole country: `--location` is
not used). The reader:

1. opens `<cc>.computrabajo.com/trabajo-de-<title>` with `pubdate` (1, 3, 7,
   15, or 30 days: the smallest that covers the run's window; none beyond 30)
   and `by=publicationtime` (newest first), then `p=2`, `p=3`… while pages
   are full (20 cards), up to 60 postings per title;
2. skips cards outside the window, postings already seen, and repeats;
3. opens each new posting's page and takes its `JobPosting` data.

Titles are searched in the words people use in that country; Spanish titles
often bring more results than English ones ("analista de datos").

**Republished postings count.** A company that republishes a posting is still
hiring. The card shows the latest publication ("Hace 2 horas"), which decides
the window and becomes `posted_at`; the first publication date, when older,
comes as `site_first_posted_at`. Add a flag saying it was republished and
when it was first published (in the panel language).

## Fields to extract

From the posting's `JobPosting` data (a **confidential** posting, whose
company shows as "Importante empresa del sector", has none: its description
and tags come from the page's description block instead, `site_tags` lists
the tags such as salary, contract, and schedule): title, company, the complete
description (verbatim), the first publication date, the employment type
(→ `contract_type`), and the salary when stated (`site_salary`: amount,
currency, period; `0` on the site means "A convenir" and is left out). From
the card: the place, the work-mode text (`site_work_mode`, for example
"Presencial y remoto"), and the latest publication. `site_category` is the
posting's category on the site (for example "Salud / Medicina"); it is not
the company's industry, so do not record it as the company's profile without
checking. Your reading: `work_mode` (from `site_work_mode` and the
description), `work_mode_detail`, `language`, `flags`, and
`published_salary` from `site_salary`.

## Application form questions

Applying needs a Computrabajo account: the questions are not visible logged
out. Leave them empty; never start an application.

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

- Postings: at least 5 seconds between requests, at most 60 postings per
  title, each posting opened once per run. A 429 or a 503 with
  `Retry-After` is waited out (the shared throttle handling); a 403 stops
  Computrabajo for the run.
- **Terms of use.** On 2026-11-19 its `robots.txt` did not disallow the
  salary pages (`/salarios/…`), the search pages (`/trabajo-de-…`, with
  `pubdate`, `by`, and `p`), or posting pages without parameters (it
  disallows parameters only under `/ofertas-de-trabajo/`, `/empresas/`, and
  CVs); its terms pages
  (`/condiciones-de-uso`, `/terminos-y-condiciones`) showed no rule on
  automated access in the text a plain request returns; that check is not
  conclusive. The salary reader gets past the site's browser check, so the
  realistic risk is that Computrabajo limits the user's IP address for a
  while (no account is involved). Tell the user this before turning it on.
- At least 20 seconds between salary pages, also from one call to the next.
  A 429, a security page, or a 403 starts a cool-down (15, 30, then 60
  minutes), kept in the user's `provider-settings/computrabajo.json`. Waiting
  is the only answer to a refusal: no proxy, no changed browser, no account.
- Read only the salary pages; do not crawl the site.

## Known pitfalls

- A posting removed after it was listed answers with a normal page saying
  "Esta oferta ya no está disponible": the reader lists it as "no longer
  available", not as a page problem.
- Confidential postings ("Importante empresa del sector") hide the company:
  never guess it.
- The card's date can be newer than the posting's own date: that is a
  republication (see "Search recipe"), not an error.
- "No hay suficientes datos para mostrar salarios" means no figure for that
  title: the page still names a large number of "fuentes", which is the
  site's total, not this title's sample.
- Figures cover every level: a junior-heavy title can sit well below a
  senior posting's range.
- Title pages use the words of the title (`/salarios/analista-de-datos`); an
  English title rarely has a page.
