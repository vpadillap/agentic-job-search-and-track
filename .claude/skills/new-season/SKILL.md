---
name: new-season
description: "Starts a new job-search season (campaign) with a new or updated profile; the earlier season stays viewable and nothing is deleted. Use when the user returns after a long pause, changes field, or wants to start over, such as “I'm back after six months”, “start fresh with a new profile”, “new season, reset what it learned” (also in Spanish: “nueva temporada”, “volví a buscar trabajo, empecemos de nuevo”, “cambio de rubro”). Not for changing one profile answer (that is setup)."
---

# New season

A season is one job-search campaign. Starting a new one closes the current
season, hides its applications from the default views (they stay viewable as
an earlier season, and a late reply can still change their status), and gives
the new season its own profile. Every action is a CLI command; never edit data
by hand and never delete anything.

**The CLI.** From the repository root run `python scripts/jt.py <command>`
(use `python3` if `python` is not available). It prints JSON:
`{"ok": true, ...}` or `{"ok": false, "error": {"code", "message", "details"}}`.
Below, `jt` means `python scripts/jt.py`.

**Privacy.** Personal data is written only by `jt` commands, inside the
private home. Pass JSON through standard input (`jt profile set -`). Do not
commit anything.

Talk to the user in the panel language (`jt context` → `language`).

## When the request is in plain words

The user may ask without the command ("I'm back after six months, let's start
again", "cambio de rubro, quiero empezar de nuevo"). There are no arguments.

- If the request already points to a level ("reset what it learned" → new
  season + reset learning; "completely clean start" → full reset), recommend
  that level in step 2, but still explain the three and ask; never pick one
  without the user's answer.
- If the user only wants to change one part of the profile (a title, the
  minimum salary, the work mode) and is not starting a new campaign, that is
  `/setup`, which revises single answers: say so and offer it instead.

## 1. Where things stand

1. `jt context`. If `setup_required` is true and there is no profile yet, this
   is a first run: tell the user to run `/setup` instead and stop.
2. `jt season show` → the active season (number, start date, counts), its
   profile, and `open_applications` (applications that have not ended).
3. `jt season list` → earlier seasons, if any.
4. `jt rules list` → the rules in force. Learned lessons have origin
   `learned`; the user's own preferences have origin `user`.

Summarize in three or four lines: the current season, how many applications
it has and how many are still open, and how many learned lessons are active.

## 2. Choose the restart level

Explain the three levels in plain words, recommend the first, and ask which
one the user wants:

| Level | Applications | Learned lessons and estimates | Preferences the user stated |
|---|---|---|---|
| **New season** (recommended) | stay in the earlier season, viewable | kept, marked as coming from an earlier season | kept |
| **New season + reset learning** | stay in the earlier season, viewable | lessons stop applying, estimates withdrawn until new outcomes arrive | kept |
| **Full reset** | the whole private home is moved to `archive/<date>-<label>/` | not in the new home | not in the new home |

Help them choose:

- If the target titles they now want differ substantially from the active
  profile's included titles (a different field or role family, not a
  seniority step), recommend **resetting learning**: lessons learned on other
  roles can mislead.
- Recommend a **full reset** only when they ask for a completely clean start
  (for example a different person will use this copy). Say that nothing is
  deleted and that moving the archive folder back restores everything.

## 3. Offer an export

Before any restart, offer: "Do you want a copy of your applications, history,
and rules as spreadsheet (CSV) and JSON files first?" If yes, `jt export` and
give them the returned `folder`.

## 4a. Full reset

1. Ask for an explicit confirmation, naming the consequence: "Everything in
   your private folder will be moved to an archive folder and the tool will
   start empty; you will run setup again. Type yes to confirm." Anything other
   than a clear yes means no: change nothing and say so.
2. Ask for a short label for the archive (default `reset`), then
   `jt reset --confirm RESET --label "<label>"`.
3. Tell them where the archive is (`archived_to`) and that their identifying
   terms were kept so the privacy guard still protects them.
4. Continue with `/setup` from the start (follow `.claude/skills/setup/SKILL.md`).
   Stop here.

## 4b. New season (with or without learning reset)

### Open applications

If `open_applications` is not empty, list them (job id, title, company,
status, applied date) and ask, for each or in bulk, whether it **continues in
the new season** (they are still interviewing, waiting for an answer they
care about, or have not applied yet but still want to) or **stays in the
earlier season**. Carried applications keep their full history. Applications
left behind can still get a status change later, from the earlier season's
view.

### Start it

Optionally ask for a short label for the new season (for example the focus of
the campaign). Then run one command:

`jt season new --learning <keep|reset> [--carry J0007 J0012] [--leave-open] [--label "<label>"]`

- `--carry` lists the applications that continue; `--carry-all-open` carries
  every open one.
- `--leave-open` is required when some open applications are not carried:
  it records that the user chose to leave them in the earlier season.
- An `open_applications` error means some open application was not decided:
  ask about it, nothing was changed.

Report the result: the new season number, what was carried, and, if learning
was reset, how many lessons stopped applying (`retired_lessons`).

### The profile, with the previous answers as defaults

The new season starts with a copy of the previous profile. Go through the
profile steps of setup again, each time showing the current value and asking
only what changed:

1. **Resume.** Ask whether they have an updated resume (in each language they
   apply in). For each new file follow step 5 of
   `.claude/skills/setup/SKILL.md` (`jt resume import "<path>" --language <code>`).
   The earlier season keeps its own resume. If nothing changed, skip.
2. **Job needs.** Follow `.claude/skills/setup/questionnaire.md`, but present
   the stored answers (`jt profile show`) and ask in small groups whether each
   still holds. Store only the changes with one `jt profile set -` call
   (fields not sent keep their value).
3. **Target titles.** Follow `.claude/skills/setup/title-research.md`, starting
   from the current titles: ask which to keep, which to drop, and whether to
   research new ones. Record decisions with `jt profile titles -`.
4. **Preferences.** Show the user's own rules (`jt rules list`, origin
   `user`) and ask whether each still applies; reword with
   `jt rules edit <id> --text "<rule>"`, drop with `jt rules retire <id>`.
   With learning kept, mention that lessons from the earlier season stay
   active and the next `/analyze-results` re-examines them against the new
   season's data.

## 5. Finish

1. `jt season show` and summarize the new season's profile in a few lines.
2. Tell them the panel's Profile & agent tab shows the active season and a
   link to view earlier ones.
3. Suggest the one next step: run the job search (`job-search` in
   `jt context` → `commands`, using its listed name).

## When something goes wrong

- A command fails twice with the same error: stop, show the message, and ask.
- The user stops midway after the season was created: everything is saved;
  running this command again is not needed. They can finish the profile with
  `/setup` (redo a step) or by asking for a change.
