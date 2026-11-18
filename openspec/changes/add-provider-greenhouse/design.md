## Context

Providers so far: LinkedIn (HTTP reader), Bumeran and Indeed (visible
Chromium readers), Glassdoor (in progress, visible Chromium). All read
logged out. Greenhouse may be the first provider whose best route needs the
user's own sign-in, which the project allows only through the user's own
browser (Claude in Chrome), never by passing credentials to Playwright.

## Goals / Non-Goals

**Goals:** Greenhouse postings with complete descriptions and, when visible,
the application-form questions; a route the owner chose from a real study.

**Non-Goals:** signing in for the user or storing credentials or cookies;
applying or saving anything in the user's Greenhouse account; reading
companies' private boards.

## Decisions

### D1. Study before route

No access method is decided here. The study (proposal, section "Study")
produces a table of routes and results; the owner picks one; D2+ are written
then.

### D2. Rules that hold whatever the route

- Logged out whenever the route allows it. If a sign-in is unavoidable, it
  happens only in the user's own Chrome through the Claude in Chrome
  extension, the user signs in themselves, and the provider is
  `requires_login: true`, `live_walk: true` (skipped in unattended runs).
- Same pacing and stop rules as the other readers (`readers/common.py`) when
  a reader is built.
- Descriptions and form questions are copied verbatim.
- Postings from company boards that also appear on other providers are left
  to the existing possible-duplicate logic; the reader does not de-duplicate.

## Open Questions

All of the proposal's study points. Answered in section 1 of the tasks.

## Risks / Trade-offs

- [The candidate search needs a sign-in] → Extension route with the user
  present, or company boards only; the owner decides with the study.
- [Company list for boards] → May depend on `add-provider-agentic-search`;
  if so, this change says so and does not build discovery itself.
