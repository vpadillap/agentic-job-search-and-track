## Context

`core/salary.py` stores evidence (`jt salary evidence add`) with source, URL,
range, currency, basis, period, sample size, date, country, level, and
context fields, and suggests a figure only from two or more comparable items.
`providers/glassdoor.md` is `kind: both` with a salary reader that returns an
evidence draft; `.claude/skills/job-search/salary-guide.md` tells the agent
how to research.

## Goals / Non-Goals

**Goals:** more comparable, linked evidence per posting, so fewer "no
reliable data"; every figure traceable to a source.

**Non-Goals:** lowering the two-source rule; estimating from the model's own
knowledge; paid sources or sources that need the user's account.

## Decisions

### D1. Study before choosing

No source or integration is decided here. The study produces the table; the
owner chooses; D2+ are written then.

### D2. Rules that hold for every source

- Logged out; read-only; no account of the user at risk.
- Each item is one source with its link, sample size when stated, and date;
  figures only from the source's data, never from prose that may name the
  wrong period (as Glassdoor's FAQ did).
- Comparability is checked by the existing rules (country, level, currency,
  basis, last 18 months); a source that does not state the level or basis is
  recorded with what it states, and the CLI decides whether it counts.

## Open Questions

All of the proposal's study points.

## Risks / Trade-offs

- [Sources disagree widely] → Each stays visible with its link; the panel
  shows the range and confidence the CLI computes.
- [Sites forbid automated access] → Stated per source, as for job sites.
