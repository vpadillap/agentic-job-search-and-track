## Context

Docs today: `README.md` (English + Spanish sections), `AGENTS.md`
(`CLAUDE.md` imports it), `docs/workspace-layout.md`, `docs/backlog.md`,
`providers/README.md`, `design/` (panel UX reference). The README title was
changed by the owner in the working tree and not committed; this change
commits it together with the rest.

## Goals / Non-Goals

**Goals:** a newcomer can install, use, and contribute from the docs alone;
nothing documented is missing from the code and nothing shipped is missing
from the docs.

**Non-Goals:** a documentation website; translating `CONTRIBUTING.md` or
`AGENTS.md` (repo content is English; the README keeps its Spanish section).

## Decisions

### D1. Runs last

It documents the results of `add-provider-glassdoor`,
`add-provider-greenhouse`, `add-provider-agentic-search`,
`add-provider-contribution`, and `improve-skill-invocation`. If one of them is
dropped, its parts are left out, not described as planned.

### D2. One source for the job-site list

The README's job-site table is written from `jt providers list` (name,
coverage, access, login, presence) at the time of the change; a test checks
that every provider file in `providers/` appears in the README.

### D3. Command check

A test parses the README's command tables and checks that each `/command`
exists in `.claude/skills/` (or as a Spanish alias template).

## Risks / Trade-offs

- [Docs drift again] → D2 and D3 tests fail when a site or command is added
  without docs.
