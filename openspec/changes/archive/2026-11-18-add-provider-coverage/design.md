## Context

`regions` is a required list field in every provider file, parsed by the flat
front-matter reader in `core/providers.py`. Its values are not checked.
`/setup` step 8 already says "providers whose `regions` cover the user's
country (or `global`)" in prose; nothing else reads the field. The profile
stores `country` as a two-letter ISO code or null.

## Goals / Non-Goals

**Goals:** one clear rule for global vs local, enforced by validation, visible
to the user, and respected by searches.

**Non-Goals:** per-country URLs inside a global provider (each provider file
already handles that, e.g. Indeed's `<cc>.indeed.com`); regions smaller than
a country; changing which providers a user has enabled.

## Decisions

### D1. Derive coverage from `regions`, no new field

A separate `scope` field would repeat what `regions` says and could disagree
with it. The rule: `[global]` alone → global; one or more uppercase
two-letter codes → local. Validation message:
`field 'regions' must be [global] or a list of two-letter country codes such as [PE]`.

The format check is shape only (`[A-Z]{2}`), like the profile's `country`;
no country table is shipped.

### D2. Computed fields in the list

`list_providers()` adds `coverage` and `countries` for valid `regions`
(`countries` is `[]` for global). For an invalid value both are `null`; the
file is already reported invalid and skipped by searches.

### D3. Skip at run start, not at enable time

The user may keep a local site enabled while the profile's country changes
(for example in a new season). Enabling stays free; `run start` marks it
`skipped` with reason `other_country` and a detail naming the provider's
countries and the profile's country. A profile without `country` does not
skip anything. Demo runs are not affected.

### D4. Panel label and country filter

A small tag after the provider name: `Global` / `Local · PE`. The country is
shown as its code to avoid shipping country names; the same markup is used in
both lists.

Above each list, a select: "Global + <profile country>" (default when the
profile has a country), "All", then one entry per country that appears in any
provider's `countries`. With a country chosen, the list shows global
providers plus local providers of that country. Without a profile country the
default is "All". The filter only hides rows; it never changes which
providers are enabled. Both lists need the profile country: the providers
endpoint returns it as `profile_country` next to the list.

### D5. Per-country verification for multi-country local providers

A front-matter field cannot hold one date per country in the flat format, so
the record is a section:

```
## Countries

| Country | Site | Last verified |
|---|---|---|
| PE | https://www.bumeran.com.pe | 2026-11-17 |
| CL | https://www.laborum.cl | 2026-11-20 |
```

Required when `regions` has two or more codes; allowed (and checked the same
way) for any local provider. Validation reads the table rows whose first cell
is a two-letter code and reports, per country in `regions`:
`country 'CL' has no row in '## Countries'` or
`country 'CL' needs a 'Last verified' date like 2026-11-15`. Rows for countries
not in `regions` are reported too, so the two never drift apart. A global
provider does not need the section; it is verified per its own recipe.

## Risks / Trade-offs

- A contributor who wrote `regions: [pe]` gets a validation error instead of
  silent acceptance → the message says how to fix it.
