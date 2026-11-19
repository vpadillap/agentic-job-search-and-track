## Why

Salary sources start switched off, like job sites, so a user who never turns
them on gets no salary research, and the agent cannot pick the sources that
fit a posting. The owner's decision (2026-11-19): salary sources are never
switched on or off; the agent asks the ones that fit the posting's country
and receives what they have.

## What Changes

- **No switch for salary sources.** A salary-only provider (`kind: salary`:
  Payscale, Talent.com) cannot be turned on or off; `jt providers enable` and
  the panel refuse it and say why. The salary pages of a job site that is
  also a salary source (`kind: both`: Glassdoor, Indeed, Computrabajo) are
  used whether or not its job search is on: the switch is about searching its
  postings only.
- **The agent chooses.** `jt salary lookup` returns `sources`: every salary
  source that serves the posting's country (global, or local with that
  country), whether its tools are ready, and what each already answered for
  the posting's keys. The salary guide tells the agent to ask the ones that
  fit, skipping what was already checked.
- **Tools installed when needed.** `jt providers install --enabled` also
  installs the tools of the salary sources that serve the profile's country,
  and `jt doctor` checks them; a missing tool found during research is
  installed by the agent (`jt providers install <id>`), never by the user.
- **Setup and the panel** list salary sources as always used, without a
  switch; `/update` says a new salary source is used from the next search
  instead of asking to turn it on.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `salary-suggestions`: salary sources are always available and chosen by
  the agent per posting.

## Impact

- `core/providers.py` (refuse switching a salary source; salary sources per
  country), `core/salary.py` (`sources` in lookup), `core/installer.py`,
  `core/doctor.py`, the panel's provider list (en/es), the salary guide,
  `/setup` and `/update` skills, README (en/es), CHANGELOG, tests.
