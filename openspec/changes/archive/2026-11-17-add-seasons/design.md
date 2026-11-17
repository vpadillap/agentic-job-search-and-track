## Context

Implements D15 of `define-foundation-architecture`; visual reference is board 4
of `design/panel-ux.html`. Seasons already exist as a table from the
foundation (season 1 is created by `/setup`); this change makes them
manageable.

## Goals / Non-Goals

**Goals:** a clean restart in one command; no data loss; learning carried over
by choice.

**Non-Goals:** deletion; panel-based profile editing.

## Decisions

### N1. New season keeps one database

`/new-season` closes the active season (end date), creates the next one, and
runs the profile part of setup again with the previous answers as defaults
(new resume optional, questionnaire, title research). Previous applications
stay in the same database, hidden from default views and shown under "earlier
seasons", read-only except for status updates and the offered salary (a late
reply, or a late offer, can still be recorded; both feed learning).
*Alternative:* a new database file per season (cleaner separation, but
cross-season learning and viewing need multi-database queries).

### N2. Three restart levels, chosen explicitly

| Level | Applications | Lessons and model | Preferences (user rules) |
|---|---|---|---|
| New season (default) | archived in place | kept | kept |
| New season + reset learning | archived in place | lessons retired, model withdrawn | kept |
| Full reset | whole home moved to `archive/<date>-<label>/` | gone from the new home | gone from the new home |

The agent explains the three, recommends the default, and requires an explicit
confirmation for full reset. A full reset is a directory move plus
`jobtracker init`, so it is reversible by moving the folder back. The user's
private terms are copied back into the new home so the privacy guard keeps
protecting them.

### N3. Open applications at season change

Applications still active (applied, interview, offer) are listed and the user
chooses per item or in bulk: carry into the new season, or leave in the old
one. Carried applications keep their history.

### N4. Learning across seasons

Kept lessons stay active but are marked "from an earlier season" so the next
analysis re-examines them against new data. The prediction model keeps using
older outcomes with recency weighting. When the new season's target titles
differ substantially from the old ones, the agent recommends resetting
learning.

### N5. Profile & agent board is read-mostly

Shows: active season with the new-season command and a link to earlier
seasons; profile version, base resume, titles by state (included, under
review, excluded, suggested but not included), and job needs; pending work
with the batch command; the command reference in the panel language; agent
memory (active rules with origin); providers with status, access method, file
name, and an enable/disable switch. The only writes from this board are the
provider switch and actions on suggested titles (include or exclude), each of
which creates a new profile version.

### N6. Export

`jobtracker export` writes applications, events, and rules as JSON and CSV into
`exports/`. It is offered before any restart.

### N7. `/panel`

Starts the server in the background if not running, reports the address,
and stops it on request. Checks the port and proposes another when busy.

## Risks / Trade-offs

- [User picks full reset by mistake] → explicit confirmation, export offer,
  reversible move.
- [Old lessons misguide a new direction] → marking, re-examination, and the
  reset-learning recommendation.
- [Confusion about which season is shown] → season name in the header profile
  chip and on every board when an earlier season is viewed.
