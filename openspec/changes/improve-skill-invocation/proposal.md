## Why

Today the user drives the project with commands (`/job-search days=7`,
`/prepare-documents ids=J0007`, …). Commands still work, but the owner wants
users to be able to just ask: "do a job search", "complete the missing
documents for application J0007", "how am I doing?". The agent should load
the right skill, ask for any detail it needs, and do the work. Claude Code
already picks a skill from its `description`; ours are written as summaries
of what the skill does, not as when to use it, so plain requests may not
reach them. The owner asked to use Claude's own skill-creator skill to tune
our skills.

## What Changes

- **Descriptions rewritten for triggering.** For each user skill (`setup`,
  `job-search`, `prepare-documents`, `form-answers`, `analyze-results`,
  `new-season`, `panel`, and `add-provider` once it exists) the description
  says when to use it, with the plain requests that should load it, in
  English and Spanish (for example "search for jobs", "busca trabajo",
  "find new postings"; "prepare the documents for J0007", "completa los
  documentos de la postulación J0007"). Done with the `skill-creator` skill's
  description optimisation.
- **Missing details are asked, not guessed.** Each skill gets a short
  "When the request is in plain words" step: map the request to the skill's
  arguments (`days`, `ids`, `pending`, `all`, `alternative`), ask only for what
  is missing and has no sensible default, and confirm before long or costly
  work (a search, documents for many applications).
- **Routing table for the agent.** `AGENTS.md` (user mode) gets a short table:
  request → skill, so an agent that did not auto-load a skill still picks the
  right one, and so requests outside every skill are answered with the
  closest command.
- **Trigger evals.** With `skill-creator`, a small eval set per skill
  (requests that must load it, and near-misses that must not, in English and
  Spanish), run before and after; the results are recorded in this change's
  design.
- Spanish alias skills keep working; their descriptions get the same
  treatment.

## Capabilities

### New Capabilities

- `natural-language-requests`: users can ask in plain words; the agent loads
  the right skill and asks for missing details.

### Modified Capabilities

None (each skill's steps are unchanged; only how it is reached and how its
arguments are gathered).

## Impact

- `.claude/skills/*/SKILL.md` front matter and one short section each;
  `i18n/skill-aliases/es/*`; `AGENTS.md` (user-mode routing table).
- Eval files under `tests/skill-evals/` (fictional requests only) and the
  skill tests that check each description and section exist.
- The commands documented in the README stay valid.
