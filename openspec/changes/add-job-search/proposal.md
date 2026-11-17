## Why

Finding relevant postings is the product's core input. The agent must search
several sites reliably, discard what is obviously wrong and say why, score the
rest against the user's profile, and research salary without ever inventing a
number.

## What Changes

- Add the `/job-search` skill (default: postings from the last 7 days,
  overridable per run): query enabled providers for included titles,
  de-duplicate, first-pass filter with recorded reasons, score, research
  salary evidence, capture visible application-form questions, and store the
  run for the panel.
- Add the scoring rubric with stored per-component breakdowns and versioned
  weights.
- Add evidence-gated salary suggestions.
- Add the provider mechanism: provider-file validation and per-user provider
  state. Provider files themselves are not part of this change.

## Non-goals

- Applying to jobs, messaging recruiters, or changing anything in the user's
  accounts on job sites.
- Scheduled or unattended background searches.
- Any provider file or any decision on how a specific site is accessed. Each
  provider is added by its own change after an individual study.
- Learning-based score adjustments (the history component stays neutral until
  `add-learning-loop`).

## Capabilities

### New Capabilities

- `job-search`: running a search across providers and producing a filtered,
  de-duplicated result set with reasons.
- `posting-scoring`: the alignment score, its components, and when it is
  recalculated.
- `salary-suggestions`: monthly salary recommendations backed by comparable,
  linked evidence, or an explicit absence of data.
- `provider-recipes`: per-site instruction files and per-user provider state.

### Modified Capabilities

None.

## Impact

- New: `.claude/skills/job-search/`, scoring and
  salary tables (migration), CLI commands `jobtracker run …`,
  `jobtracker postings import`, `jobtracker score set`, `jobtracker salary set`,
  `jobtracker providers …`.
- Depends on `add-setup-onboarding` (profile) and `add-panel-search-tab`
  (postings model and board).
