## Why

Some job sites work in many countries (LinkedIn, Indeed) and others only in
one (Bumeran Perú). Provider files already carry `regions` (`[global]` or
country codes), but nothing checks the value, the panel does not show it, and
a search still queries a one-country site when the user's profile is in
another country. Before more sites arrive (Glassdoor, Greenhouse, an agentic
web search), every provider must say clearly whether it is global or local,
and the tool must act on it.

## What Changes

- **Coverage from `regions`.** No new front-matter field: `regions: [global]`
  makes a provider *global*; a list of two-letter country codes
  (`[PE]`, `[PE, CL]`) makes it *local* to those countries. Validation now
  rejects anything else (mixed `global` and codes, lowercase codes, an empty
  list, other words).
- **Each country verified.** A local provider with more than one country must
  have a `## Countries` section with one table row per country: its code, the
  site address used there, and the date the recipe was last verified in that
  country. Validation reports every country in `regions` without a row or
  without a valid date. A site that works in several countries is only
  claimed for the countries someone actually checked.
- `jt providers list` (and the panel API) adds `coverage` (`global` or
  `local`) and `countries` (the codes, empty for global) to each provider.
- **Search.** At `jt run start`, an enabled local provider whose countries do
  not include the profile's `country` is skipped with the new reason
  `other_country` (nothing is queried). When the profile has no country, local
  providers are searched as before.
- **Setup.** Once the user's country is known, step 8 offers the global sites
  plus the local sites of that country; local sites of other countries are
  not offered.
- **Panel.** The job-site lists (Profile & agent board, and the job-site
  switches in the Search tab) show "Global" or "Local · <country>" next to each
  name, and have a country filter: by default the global sites plus those of
  the profile's country; the user can pick another country or all sites. The
  new skip reason is localized (en/es).
- `providers/_template.md` and `providers/README.md` explain the two kinds.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `provider-recipes`: provider files declare global or local coverage, which
  is validated and reported.
- `job-search`: a local provider for another country is skipped with a reason.

## Impact

- `core/providers.py` (validation, `coverage`/`countries`), `core/search.py`
  (skip reason `other_country`), panel `boards/profile.js`,
  `boards/search.js`, `app.css`, locales en/es.
- `.claude/skills/setup/SKILL.md` step 8, `.claude/skills/job-search/SKILL.md`
  (the new skip reason), provider template and README.
- Existing provider files are already valid (`linkedin`, `indeed`: global;
  `bumeran`: `[PE]`).
- Tests: validation cases, list output, run start with matching, other, and
  missing country; a browser test for the tag.
