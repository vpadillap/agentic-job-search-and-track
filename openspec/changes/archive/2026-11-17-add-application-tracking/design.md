## Context

Implements D7 and D8 of `define-foundation-architecture`; visual reference is
board 2 of `design/panel-ux.html`. Reuses the table, filter, and expandable-row
components from `add-panel-search-tab`.

## Goals / Non-Goals

**Goals:** recording an outcome takes one click; every change is captured as an
event; custom statuses never break filtering or analytics.

**Non-Goals:** document generation; external integrations.

## Decisions

### T1. Status and stage

Built-in statuses and stages:

| Stage | Built-in statuses |
|---|---|
| `to_apply` | New |
| `applied` | Applied |
| `interview` | Interview |
| `offer` | Offer |
| `closed_positive` | Accepted |
| `closed_negative` | Rejected, Ghosted, Offer declined, No economic alignment, Withdrawn |

Status names are localized for built-ins; custom statuses are shown as typed.
Inline creation: type a new name in the status picker, pick a stage (defaults
to the current one), done. Custom statuses can be renamed or retired, never
deleted while in use. Built-ins cannot be removed.
*Alternative:* free tags only (rejected in D8).

### T2. Default visibility

The default view shows every stage except `closed_negative`. "Show closed"
reveals them. The funnel cards act as stage filters. The footer states how many
are hidden.

### T3. Events and snapshot

Every change writes an event (status change with from/to, field edits,
document registered or replaced, score change, note added). When an
application first enters the `applied` stage the system stores the application
snapshot (D7) from the data current at that moment; later edits to the applied
date or asked salary update the snapshot's own fields but not the captured
score or resume kind.

### T4. Next step and reminders

`next step` is derived, with a user override: to apply → "prepare documents"
or "apply"; applied → "follow up" after the follow-up interval (7 days
default); applied with no response past the ghost threshold (21 days default,
adjustable by a rule) → "mark as ghosted?"; interview and offer → the
user-entered date. The agent never changes a status to Ghosted on its own; it
proposes, the user confirms (one click, or in bulk).

### T5. Sent resume upload

Uploading stores the file as `resume-sent.<ext>` in the application folder
(previous upload kept as `resume-sent-v<N>`), registers it, marks the
application as using a user-provided resume, and enqueues a rescore. Accepted
types: PDF, DOCX; size limit 10 MB; stored only inside the private home.

### T6. Editing model

Inline fields save on blur with optimistic update and visible save state.
Concurrent agent writes to the same field are resolved last-write-wins with an
event for each, so nothing is lost from history.

### T7. Salary asked

Stored with currency and period like suggestions, shown next to the suggestion
that was current when the user applied, with the percentage difference.

## Risks / Trade-offs

- [User forgets to update statuses, starving the learning loop] → "needs
  something" strip, ghost prompts, and one-click bulk updates.
- [Too many custom statuses] → stage mapping keeps views and analytics stable;
  statuses can be merged.
- [Upload of a wrong or malicious file] → type and size checks, stored and
  served as a download, never rendered inline.
