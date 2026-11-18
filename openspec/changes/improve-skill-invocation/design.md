## Context

Claude Code loads a skill when the request matches its `description`. The
project's descriptions summarise what each skill does ("Searches the enabled
job sites…"), which helps, but they list few of the words users actually say
and no Spanish phrasing. Skills take arguments as `key=value` text
(`days=7`, `ids=J0007,J0012`), which a plain request does not give.

## Goals / Non-Goals

**Goals:** plain requests in English or Spanish reach the right skill; the
agent asks for what is missing; commands keep working.

**Non-Goals:** new features in any skill; merging skills; changing the panel.

## Decisions

### D1. Use skill-creator for descriptions and evals

The `skill-creator` skill (Anthropic's) is used to write each description and
run its triggering evals. The eval requests are fictional and generic.
Before/after trigger rates are recorded in this design when the change is
applied.

### D2. Description shape

"<What it does in one sentence>. Use when the user asks to <plain verbs>,
such as \"…\", \"…\" (also in Spanish: \"…\"). <What it never does>."
Kept under the length Claude Code shows in full.

### D3. Argument gathering

A common short section in each skill: read the request; take values it
states (dates, ids such as J0007, "all", "pending"); use the skill's default
where one exists (7 days; `pending`); ask one question only when a required
value is missing (for example which application, when there are several and
the user said "the documents for my last application"); before a run that
takes long, say what will happen and ask to continue.

### D4. Routing table in AGENTS.md

User mode gets a table of typical requests → skill. It complements the
descriptions; it does not replace them.

## Risks / Trade-offs

- [Over-triggering: a skill loads for a question that only needs an answer]
  → Near-miss evals ("what is a cover letter?" must not start
  `prepare-documents`).
- [Description length] → D2 keeps them short.
