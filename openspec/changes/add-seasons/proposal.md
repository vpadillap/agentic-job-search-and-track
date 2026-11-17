## Why

People search for jobs in campaigns. Someone who returns after many months, or
changes direction, needs a clean start with a new or updated profile without
losing what was learned or destroying their history. They also need one place
in the panel to see their profile, what the agent remembers, what is pending,
and which providers are in use.

## What Changes

- Add seasons: a search campaign with its own profile versions and
  applications. Add the `/new-season` skill, which starts a new season with a
  new or updated profile and archives the previous one from default views.
- Add the choice of what to carry over: learned lessons are kept by default
  and can be reset; a full reset moves all data to an archive and starts empty.
- Add the Profile & agent board (board 4 of the design): active season,
  profile summary, pending work, command reference, agent memory, and provider
  toggles.
- Add the `/panel` skill to start and stop the panel.

## Non-goals

- Deleting user data; nothing is ever deleted by the tool.
- Editing the profile through panel forms; it is changed by talking to the
  agent.
- Multiple simultaneous active seasons or multiple users.

## Capabilities

### New Capabilities

- `seasons`: search campaigns, starting a new one, archiving, and resets.
- `profile-agent-board`: the panel tab for profile, pending work, commands,
  agent memory, and providers.

### Modified Capabilities

None.

## Impact

- New: `.claude/skills/new-season/`, `.claude/skills/panel/`, Spanish alias
  `nueva-temporada`, `jobtracker season …`, `jobtracker export`, Profile &
  agent board frontend.
- Touches: default scoping of boards and insights to the active season.
- Depends on `add-setup-onboarding` and `add-application-tracking`; the agent
  memory card depends on `add-learning-loop` for learned rules.
