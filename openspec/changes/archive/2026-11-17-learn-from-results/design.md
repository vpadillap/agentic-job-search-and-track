## Context

`application_snapshots` (0001) stores one JSON per application, written when
it first gets an applied date: score and score id, score components, title,
site, channel, work mode, contract type, resume kind, cover letter, posting
age, applied date, suggested and asked salary. `_update_snapshot` keeps the
applied date and asked salary in sync with the table. Readers:
`insights.outcomes` (joins it; only snapshotted applications are outcomes),
`insights.features_of`, `predict` (training features and the estimate of an
applied posting), `refresh.write_history`, `scoring.at_application`,
`applications.application` (`snapshot` key, read by the board's suggested
salary), `tracking.untrack`, and both demos. `scores` and
`salary_suggestions` keep every version (`is_current` flag, `created_at`).
Status changes already store ids and both names (since
`remove-status-stages`); `insights.outcomes` still builds `status_path` from
keys, and `status` is the English name.

## Goals / Non-Goals

**Goals:**

- One source of truth: the history plus the current data.
- The offered salary is a fact the user records and learning uses.
- The agent reads statuses as the user names them.

**Non-Goals:**

- Predicting offers or offered amounts (too few cases for one person, as in
  `add-learning-loop`).
- Changing what the statistics count as interview or response.
- Anything in `add-seasons`.

## Decisions

### D1. The moment of applying is an `applied` event

When an application first gets an applied date (a status that fills it, or
the date entered by hand), an `applied` event is written with `{"on":
<applied date>, "score_id", "salary_suggestion_id"}`: the date and the ids
of the score and salary suggestion versions current at that moment (pointers
to versions that are kept anyway, not copies of facts). Only the first time:
clearing and re-entering the date does not move it. The moment of applying
is that event's `created_at`. Migration 0013 turns each existing snapshot
into such an event, with the snapshot's `captured_at`, applied date, and
score id, so existing applications keep their moment and their score. The
panel's history shows it ("Applied on {date}").

The ids matter: timestamps have one-second resolution, so a rescore in the
same second as applying could not be told apart by time alone (a test caught
it).

### D2. Facts at application time are derived

`applications.at_application(conn, job_id)` returns, for an application with
an applied date, the same fields the snapshot had plus the offered salary:

- score: the version the `applied` event names; without one, the latest
  `scores` row created at or before the moment; if none, the earliest row;
  with its id and components;
- suggested salary: the same rule over `salary_suggestions`, counted only
  with status `suggested`;
- resume kind from the current documents (sent, else tailored, else base),
  cover letter from the current documents, channel, applied date, asked and
  offered salary from the application;
- title, site, work mode (current, so corrections count), contract type from
  the posting; posting age = applied date − publication date.

It returns `None` without an applied date. Learning code reads it under the
key `at_application` (renamed from `snapshot`), with the same field names, so
the statistics keep their meaning.

### D3. Offered salary

Columns `offered_salary_amount`, `offered_salary_currency`,
`offered_salary_basis` on `applications`, validated like the asked salary
(positive whole amount, 3-letter currency, gross or net, monthly). It is a
detail field (`offered_salary`), so it is edited in the details form, saved
with a `field_changed` event, and returned on the application.

### D4. Learning uses the offered salary

- `insights.outcomes`: `offer` is also true when an offered salary is
  recorded; the record carries `offered_salary`.
- `insights.summary` adds `offered_salary`: `{offers_with_amount,
  vs_asked: {median_pct, cases}, vs_suggested: {median_pct, cases}}`,
  comparing only the same currency (and the same basis when both state it).
- The Learning board's offers card adds one line with the median offered
  versus asked when there are cases.
- The agent's history record carries `offered_salary` next to the asked and
  suggested salaries.

### D5. Statuses by name in learning

`insights.outcomes(conn, today, language)` gives `status` as the full name in
that language, `status_key` (built-ins), `ended`, and `status_path` as
`[{status: <full name>, key, on}]`, resolved with
`applications.status_names` (names stored in the event, or by key or stored
name for older events). `refresh.write_history` passes the panel language.
The statistics still use the keys and `ends` (`insights._progress`).

### D6. Readers updated

`predict` takes components from the score at application time; its estimate
for an applied posting uses `at_application`. `scoring.at_application`
returns the derived score. The board's suggested salary uses
`at_application.suggested_salary`, else the current suggestion. `untrack` no
longer deletes a snapshot. The base demo, which sets past applied dates
directly, writes those dates into its `applied` events (their moment stays
when the demo was loaded, after the postings were found) and records an
offered salary on its offer. The learning demo registers a fictional
tailored resume for the applications it marks as tailored, backdates their
`applied` events with their status history, and records an offered salary on
some interviews (with its own random generator, so the outcomes and levels
stay the same).

## Risks / Trade-offs

- [A score created later on the same day as applying, but after the moment]
  → It is not the score at application time, as with the snapshot.
- [Older applications whose sent resume was uploaded after applying change
  from "base"/"tailored" to "sent" in the breakdowns] → That is the
  correction the owner asked for.
- [`add-seasons` may also touch insights] → Small, separate functions; merge
  conflicts, if any, are resolved by whoever merges second.

## Migration Plan

`0013_learn_from_results.sql`: add the offered salary columns; insert one
`applied` event per snapshot (`created_at` = `captured_at`, data with the
snapshot's applied date); drop `application_snapshots`. Forward only; the
usual backup runs first.

## Open Questions

None.
