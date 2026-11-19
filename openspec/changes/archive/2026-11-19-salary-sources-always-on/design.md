## Context

`providers_state` stores on/off per provider; `start_run` searches only job
providers (`kind: jobs` or `both`) that are on. Salary readers run through
`jt providers salary <id>` with no check of on/off; the salary guide told the
agent to use only enabled sources.

## Decisions

### D1. Which sources serve a posting

A provider is a salary source when `kind` is `salary` or `both` and it has a
`## Salary data` section; it serves a country when its coverage is global or
its countries include it. `providers.salary_sources(country)` returns them
with `reader` (a salary reader exists) and `ready` (its dependencies are
available).

### D2. The switch

`set_enabled` refuses `kind: salary` (`salary_source`). Existing stored
states for those providers are ignored. The panel shows switches for job
sites only and one line naming the salary sources, always used.

### D3. Tools

`install(enabled=True)` adds the salary sources of the profile's country;
`doctor` checks them under `salary:<id>`.

## Risks / Trade-offs

- [More automated requests to salary sites] → Paced and cooled down per
  source as before; each source's terms note stays in its file and README.
