## Context

`0006_applications.sql` gives every status a `stage` (to_apply, applied,
interview, offer, closed_positive, closed_negative). Stages drive: the applied
date and the application snapshot (on entering an "applied" stage), the next
step (prepare documents, follow up, ghost, set a date), the attention summary,
the open-applications counter, the pending documents and rescore lists, the
"apply next" ranking, the learning outcome flags (`insights._progress`, which
was written as the single place to change when stages go), the board's funnel,
hide-closed, sort and filter, the status chips' colors, and the CLI/API
(`--stage`, `stage` fields). The owner wants statuses flat, each saying only
whether the application ended, and the agent to read full status names.

## Goals / Non-Goals

**Goals:**

- No stage in the database, CLI, API, panel, or agent output.
- Every behavior that used a stage keeps working with an explicit rule.
- Custom statuses ask for a name and "ended?" only.

**Non-Goals:**

- The learning history's status names, an offered-salary field, and whether
  the application snapshot stays: a later change, by the owner's decision.
  This change only keeps learning working.
- Reordering statuses, colors per status, or any new grouping.

## Decisions

### D1. `statuses.ends` replaces `statuses.stage`

Migration `0012_status_ends.sql` adds
`ends INTEGER NOT NULL DEFAULT 0 CHECK (ends IN (0, 1))`, sets it to 1 for the
built-in keys accepted, rejected, ghosted, offer_declined,
no_economic_alignment, withdrawn and for custom statuses whose stage was
closed_positive or closed_negative, then drops `stage` (SQLite 3.35+, already
required by earlier migrations; if not, rebuild the table the way earlier
migrations did). Old `status_changed` events keep their `from_stage` and
`to_stage`; nothing reads them any more.

### D2. Built-in keys keep their meaning; custom statuses carry name and ends

The built-in statuses always exist and cannot be renamed, so their key is a
stable meaning, not a grouping. The system reads a key only where it has to
act:

| Purpose | Rule |
|---|---|
| Fill in the applied date | keys applied, interview, offer, accepted, rejected, ghosted, offer_declined, no_economic_alignment |
| Next step "set the date" | keys interview, offer |
| Learning: reached interview | keys interview, offer, accepted (same as before) |
| Learning: reached offer | keys offer, accepted (same as before) |
| Learning: no response | keys ghosted, withdrawn (same as before) |

A custom status is only a name and `ends`. Learning treats it as "closed with
a response" when it ends (as custom closed statuses were before) and as
pending otherwise. Custom statuses that used to sit in the interview or offer
stage no longer count as interviews or offers in the statistics; the agent
still sees their full names (and the later change gives them to the learning
history by name).

Alternative considered: an order or "progress level" per status. Rejected:
it is a stage by another name, and the owner asked for none.

### D3. Applied = has an applied date

`set_status` fills `applied_on` with today when it is empty and the new status
is one of the keys in D2's first row. New, Withdrawn (may happen before
applying), and custom statuses never fill it, because a custom status may come
before applying (for example "Waiting for a referral"). The user edits or
clears the date in the table as today. The snapshot is taken the first time
`applied_on` goes from empty to a date, whether by `set_status` or by
`update_details`; clearing the date later keeps the snapshot (as today).

### D4. Rules that replace each stage use

| Before (stage) | After |
|---|---|
| next step: to_apply → prepare documents / apply | no applied date and not ended |
| next step: applied → follow up / ghost | applied date, not ended, status key not interview/offer; timing from the later of the applied date and the last status change, as before |
| next step: interview/offer → set a date | applied date, not ended, key interview or offer |
| next step: closed → none | ended |
| user next step shown while open | not ended |
| attention: open items | not ended; missing resume and unanswered form need no applied date |
| board counter "applications" (open) | not ended |
| pending documents (`_document_items`) | no applied date and not ended |
| rescore after a weights lesson | tracked and not ended |
| "apply next" ranking | no applied date and not ended |
| Search row "tracked, applied" label | has an applied date |
| `tracking.track --applied` sets Applied | when the application has no applied date |
| funnel | count per status (D5) |
| hide closed negative | hide ended (D5) |
| sort by status | status list order |

### D5. Board: one card per status, ended hidden

`applications.funnel` returns a list `[{status_id, key, name, ends, count}]`
for statuses with at least one application, ordered like the status list
(`position`, then `id`: built-ins in their fixed order, then custom statuses,
which all have the default position, in creation order). The cards show the
full name and count; selecting one filters by that status id. Ended
applications are hidden unless "show ended" is on or the selected card is an
ending status; the hidden note names the statuses. Status chips drop the
`stage-*` classes; an `ended` class mutes them. The new-status form asks the
name and a checkbox "The application ended with this status" (unchecked by
default).

### D6. CLI, API, and agent output

- `applications list --status <id|key|name>` replaces `--stage`;
  `--hide-ended` replaces `--hide-closed`.
- `applications statuses create NAME --ends yes|no` (required) replaces
  `--stage`; `applications set-status JOBS --to NAME --ends yes|no` creates a
  status inline (`--to` also accepts a status id).
- API: `StatusRequest.ends: bool | None` and `CreateStatusRequest.ends: bool`
  replace `stage`.
- Status objects: `{id, key, name, name_en, name_es, ends, builtin, retired}`;
  applications: `status` as that object plus `ended` (bool); no `stage` key.
- History: new `status_changed` events store `from`/`to` (key or name, as
  before) plus `from_id`, `to_id`, `from_name`, `to_name` (panel-independent
  English and Spanish names are resolved at read time by id, falling back to
  key or stored name for old events). `history()` adds `from_name`/`to_name`
  in the requested language.

### D7. Learning, minimal

`insights._progress(key, ends)` implements D2's learning rows; `outcomes()`
reads `s.ends` instead of `s.stage` and resolves each event's status by id,
key, or stored name to get `ends`. The outcome record replaces `stage` with
`ended`. `recommend.apply_next` uses D4's rule. Nothing else in learning
changes here.

Because Rejected now fills in the applied date and a date entered by hand
takes the snapshot, two applications of the base demo (Altiplano, rejected;
Tika, "Position frozen" with a date) now count as outcomes. The collecting
level of the learning demo shrinks from 10 to 8 fictional applications so it
stays below the descriptive threshold, as before.

## Risks / Trade-offs

- [Custom statuses that meant "interview" no longer count as interviews in
  the statistics] → The agent sees full names; the later learning change can
  use them. Built-in Interview is the first choice in the list.
- [A custom status set straight from New leaves no applied date] → The user
  enters the date in the table (owner: this is how it should work); until
  then the application counts as not applied and its documents stay pending.
- [Hiding all ended applications also hides Accepted] → Its card still shows
  the count and lists them on selection.

## Migration Plan

Forward-only migration 0012; the existing backup runs before it. No rollback.

## Open Questions

None.
