# Providers

One Markdown file per job site or salary source. The agent reads the file for
each enabled provider before touching that site and follows it literally.

Each provider is added by its own OpenSpec change, after an individual study
of that site. How a site is accessed is decided there, not in advance.

- Copy `_template.md` to `<provider-id>.md` (lowercase, e.g. `linkedin.md`).
- Keep instructions concrete and verified: which tool to use, exact URL
  patterns, what to extract, how fast to go, and what must not be done.
- Update `last_verified` whenever you confirm the recipe still works. Sites
  change; a stale recipe should say so rather than guess.
- No personal data, cookies, or credentials in these files.

## Global and local providers

`regions` says where a site works:

- `regions: [global]`: a **global** site that serves many countries (LinkedIn,
  Indeed). The file explains how it picks the country, if it does.
- `regions: [PE]` or `[PE, CL]`: a **local** site that works only in those
  countries (Bumeran Perú). Codes are uppercase ISO 3166 two-letter codes.

Setup offers the global sites plus the local sites of the user's country, and
a search skips an enabled local site when the profile's country is another one
(reason `other_country`). The panel shows each site as "Global" or
"Local · PE" and filters the list by country.

A local site with two or more countries needs a `## Countries` table with one
row per country: the site address used there and the date the recipe was last
verified **in that country**. Claim a country only after a real search there
works; `jt providers validate` reports any country without a dated row.

Whether a provider is enabled for a given user is stored in that user's
database (toggled from the panel), not here.
