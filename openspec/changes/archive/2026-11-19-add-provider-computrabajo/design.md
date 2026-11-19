## Context

Computrabajo has one site per country (`<code>.computrabajo.com`). Its salary
pages are read through a headless Scrapling session because their figures
are filled in by JavaScript; its job pages have not been studied.

## Goals / Non-Goals

**Goals:** Computrabajo's postings in the countries it serves, read as the
study shows works, logged out.

**Non-Goals:** applying, accounts, the salary reader (unchanged).

## Decisions

### D1. Study first

The route (plain HTTP or Scrapling), the search filters, and the fields are
decided from the study's results, approved by the owner.

## Risks / Trade-offs

- [Search parameters disallowed by robots.txt] → Recorded in the study; the
  owner decides with that in view.
