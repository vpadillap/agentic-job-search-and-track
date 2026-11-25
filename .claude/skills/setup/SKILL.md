---
name: setup
description: "First-run setup of Job Tracker and later revisions of it: requirements, panel language, resume, job needs, target titles, job sites, and the user's own rules. Use when the user is starting out or wants to change any of those, such as “I just cloned this, how do I start?”, “set up the job tracker”, “change my target titles”, “turn on LinkedIn” (also in Spanish: “configura el proyecto”, “cambia el idioma del panel”, “actualiza mi perfil”). Not for starting a whole new campaign (that is new-season)."
---

# Setup

You are setting up Job Tracker for the person in front of you. Follow the steps
in order. Every deterministic action is a CLI command; do not improvise file
locations or write data by hand.

**The CLI.** From the repository root run `python scripts/jt.py <command>`
(use `python3` if `python` is not available; once the project's `.venv` exists
the script uses it automatically). It prints JSON:
`{"ok": true, ...}` or `{"ok": false, "error": {"code", "message"}}`. On an
error, read the message, fix the cause, and retry; do not work around it.
Below, `jt` means `python scripts/jt.py`.

**Privacy rules for this whole skill**

- Personal data is written only by `jt` commands, which store it in the private
  home (`user-data/`, gitignored). Never create or edit files in the repository
  with the user's data, and never write temporary files containing it outside
  the private home. To pass JSON to a command, pipe it through standard input
  (`jt profile set -`).
- Never put the user's data in commit messages, and do not commit anything
  during setup.
- Ask before installing anything.

**Resuming.** Start with `jt context`.

- `initialized: false` → begin at step 1.
- Otherwise read `setup.steps`. Continue at `setup.next_step`. If setup is
  complete, the user wants to revise something: ask what, run `jt setup redo
  <step>`, and do that step again. Completed steps are not repeated unless the
  user asks.
- When the workspace exists, also run `jt offers list`: present each pending
  one-time offer once, in its `text`, and record the answer with `jt offers
  accept <id>` or `jt offers decline <id>` (see `/update`, step 5).

## When the request is in plain words

The user may ask without the command ("I just cloned this, how do I start?",
"cambia mis títulos objetivo", "quiero el panel en inglés"). Read the request:

- First time, or setup not complete: resume as above.
- Setup complete and the request names what to change: run
  `jt setup redo <step>` for that step and do it, without asking again what
  to revise: the panel language → `language`;
  a new base resume → `resume`; work mode, location, salary, availability, and
  other job needs → `questionnaire`; target titles → `titles`; job sites →
  `providers`; the user's own rules → `preferences`.
- Starting a whole new campaign (a new field, a long pause) is `/new-season`,
  not a revision: say so and offer it. Adding a job site the project does not
  have yet is `/add-provider`.

Mark each step when it is finished with `jt setup done <step>` (several steps
can be given at once). Steps 1–3 happen before the workspace exists, so mark
all three right after step 3.

**Language of what you store.** Values the user gives (locations, industries,
availability, company names) are stored as the user said them. Text you write
yourself (rules, reasons for proposed titles) is written in the panel
language.

**Skipped questions.** Leave the field out of what you send. Never send a
guess, and never ask twice.

## 1. Environment (`environment`)

1. Run `jt doctor`. It changes nothing.
2. If there is no working Python 3.11+ (the `python` check fails, or `python`
   is not found, or it opens the Microsoft Store or answers "Python was not
   found": that is only the Store's alias, not Python), install it. Tell the
   user first, then:
   - **Windows**: `winget install --id Python.Python.3.13 -e --scope user
     --accept-package-agreements --accept-source-agreements`. Never install
     from the Microsoft Store, and do not rely on `python` afterwards: an open
     shell does not see the new PATH. Use the interpreter by its full path,
     `%LOCALAPPDATA%\Programs\Python\Python313\python.exe` (check it with
     `--version`), for every command until `.venv` exists. If `winget` is
     missing, ask the user to install Python 3.13 from python.org with "Add
     python.exe to PATH" checked, then use its full path the same way.
   - **macOS**: `brew install python@3.13` when Homebrew exists; otherwise
     ask the user to install it from python.org.
   - **Linux**: the distribution's package (`python3`, `python3-venv`), with
     the user's permission for `sudo`.
   Then create the project's environment with that interpreter (step 3) and
   use `.venv` from then on: `scripts/jt.py` and the privacy guard both pick it
   first, so no PATH change is needed.
3. If any `package:*` check fails, tell the user what will be installed (the
   packages listed in `pyproject.toml`, into a `.venv` folder inside this
   project, nothing system-wide) and ask to proceed. Then:
   - if `uv --version` works: `uv sync`
   - otherwise: `<python> -m venv .venv` (the interpreter of step 2, by its
     full path when it was just installed), then
     `.venv/Scripts/python -m pip install -e .` (Windows) or
     `.venv/bin/python -m pip install -e .` (macOS/Linux)
4. If the `privacy_guard` check is not `pass`, run
   `git config core.hooksPath .githooks`.
5. Run `jt doctor` again. Only `workspace` and `schema` may still fail at this
   point. If something else fails, show its `fix` to the user and resolve it
   before continuing.

## 2. Language (`language`)

This is the first question about the user themselves (permission to install
in step 1 may have come before it). Ask it in both languages:

> Should the panel be in English or Spanish? / ¿Quieres el panel en inglés o en español?

From here on, talk to the user in the language they chose.

## 3. Workspace (`workspace`)

1. `jt init --language <en|es>`
2. `jt skills sync` (installs the Spanish command names for Spanish users;
   does nothing for English).
3. `jt setup done environment language workspace`

If Spanish command names were installed, tell the user they become available
the next time Claude Code starts in this folder.

## 4. Privacy (`privacy`)

Explain in two sentences: everything personal stays in the `user-data/` folder
of this project, which git ignores; a guard also refuses any commit containing
their name, email, or phone.

Ask for their full name, email, and phone number as they appear on the resume
(they may skip any). Record the full name; it also names the resumes and cover
letters they download from the panel (`<Full Name> - J0007.docx`), and the
command registers it for the guard in the same step:

`jt privacy name set "<full name>"`

Then register the email and phone, one argument per term:

`jt privacy terms add "<email>" "<phone>"`

More terms can be added at any time with `jt privacy terms add`, and
`jt privacy terms list` shows what is registered if the user asks. The name is
changed with `jt privacy name set` again (`jt privacy name show` shows it).

## 5. Resume (`resume`)

Each resume is the source for its own language: postings in Spanish are
scored and tailored against the Spanish resume, postings in English against
the English one.

1. Ask in which languages they will apply for jobs (for example English and
   Spanish). If `jt context` → `base_resumes` has one whose `language` is null
   (imported before languages were recorded), ask which language it is in and
   run `jt resume language <code>` first.
   Then, for each of those languages, ask for the path to their resume in that
   language (PDF or DOCX; DOCX is better because later tailoring can keep its
   exact layout). For a language they have no resume in, offer to translate one
   of theirs (step 7).
2. For each file: `jt resume import "<path>" --language <code>` (2-letter code:
   en, es, pt…).
   - `no_text_extracted`: the file is probably a scan. Offer two options: a
     text-based file instead, or you read the file visually, show the full text
     to the user for confirmation, save the confirmed text with
     `jt paths` → `profile` folder as `resume-visual-draft.md`, and run
     `jt resume import "<path>" --language <code> --text "<that file>"`.
   - `unsupported_resume` / `unreadable_resume`: ask for another file.
3. Read the extracted text at the returned `text_path` of each resume.
4. Show the user a short summary of each so they can confirm it was read correctly:
   current or latest role, total years of experience, main skills, education,
   languages. Ask them to correct anything wrong or missing. Corrections that
   are facts about them (for example "I also know Kafka, it is just not on the
   resume") are important: note them for step 9.
5. If the resume shows identifying strings that were not registered in step 4
   (a second email, a LinkedIn or GitHub handle, a national ID number), add
   them now with `jt privacy terms add`.
6. If the file is a PDF, mention once that providing the DOCX version later
   allows tailoring without touching the layout.
7. A language they will apply in but have no resume for: offer to translate
   one of their resumes into it, following `resume-translation.md` in this
   folder. The translation is a draft they review in Word; it becomes their
   resume for that language only when they confirm it.
8. Tell them they can add a language, or replace the resume of a language, at
   any time by asking.

## 6. Questionnaire (`questionnaire`)

Follow `questionnaire.md` in this folder: it lists the questions, the allowed
values, and how to store the answers. Rules:

- Pre-fill what the resume makes obvious and ask the user to confirm instead of
  asking from scratch (country, languages, seniority).
- Ask in small groups, not one long form.
- Every question can be skipped; leave skipped fields out.
- Store everything with one `jt profile set -` call. Its output is the stored
  profile: present that to the user for confirmation.
- Facts the user confirmed in step 5 that are not on the resume go in
  `additional_facts`, so later documents may use them.

## 7. Target titles (`titles`)

Follow `title-research.md` in this folder. In short: ask which titles they
want, research the market, propose alternates with a reason each, and record
the user's decisions with `jt profile titles -`. A title is included only when
the user says so.

## 8. Job sites (`providers`)

1. `jt providers list`.
2. If the list is empty, say that job-site recipes are not included in this
   version yet and that searching will become available with them; continue.
3. Otherwise offer, using the profile's `country`, the providers with
   `coverage: global` first, then those with `coverage: local` whose
   `countries` include the user's country; label each "global" or "local
   (<countries>)". Do not offer local sites of other countries (if the profile
   has no country, offer every site and say which are local). Give a one-line
   note on how each is accessed (`access`, `requires_login`, `live_walk`).
   Read each one's file
   (`providers/<id>.md`, section `## Limits and etiquette`) and tell the user
   any terms-of-use risk it states, in a sentence. Ask which to use.
   Offer only job sites (`kind: jobs` or `both`). Salary sources (`kind:
   salary`, and the salary pages of job sites) are never switched: say in
   one line that they are always used for salary research, naming those
   that serve the user's country, with their terms note.
4. Every job site starts switched off. `jt providers enable <id>` for each one
   the user picks; leave the others off. A site added later by an update also
   arrives off, so nothing is searched without the user's choice.
5. For each enabled provider with `dependencies`, and each salary source of
   the user's country, tell the user what will be installed and its size,
   then run `jt providers install <id>` (or `jt providers install --enabled`
   for all of them at once): it installs the missing tools into the
   project's environment and checks they work. Confirm with `jt doctor` that
   its `provider:<id>` check passes. If installing a job site fails, run
   `jt providers disable <id>` and say why; a salary source that fails is
   skipped in research until it is fixed.

## 9. Preferences (`preferences`)

`jt rules list` shows the rules already in force: the system rules (the
defaults below are among them) and any rule the user gave before. Do not add a
rule that repeats one already listed. If this step is being redone, go through
the user's existing rules with them first: reword with
`jt rules edit <id> --text "<rule>"`, drop with `jt rules retire <id>`.

Ask the three questions below. Store an answer only when it says something the
listed rules do not, with `jt rules add --area <area> --text "<rule>"`:

1. Resume changes (area `resume`). The default is content only, never layout.
   Ask whether they also allow (a) changing length or which sections appear,
   (b) layout changes. If they are happy with the default, store nothing.
2. Cover letters (area `cover_letter`). The default is only when the posting
   or its form asks for one. Ask whether they want one in other cases (for
   example always, or for certain kinds of roles).
3. Anything the agent should always or never do (areas `search`, `general`,
   `salary`, …), for example "no outsourcing consultancies".

Write each rule as one short imperative sentence in the panel language, about
what the agent does. Do not put the user's name or contact details in a rule.

## 10. Tour (`tour`)

1. `jt context` to get `commands`, `panel`, and `home`.
2. If `panel.interface_ready` is true, start the panel in the background with
   `jt panel` and give the user `panel.url`. If it is false, say the panel
   interface is not included in this version yet.
3. Give the tour in `tour.md` (this folder), in the user's language, using the
   command names from `commands`. Mention only commands whose `available` is
   true as usable now; list the others as coming.
4. `jt setup done tour`.
5. Finish with the one next step. If the job search command (id `job-search`
   in `commands`) is available, suggest running it. If it is not, say that
   setup is complete and their profile is ready for when search is added.

## When something goes wrong

- A command fails twice with the same error: stop, show the user the error
  message, and ask how to proceed.
- The user wants to stop midway: everything done so far is saved; running
  `/setup` again continues where they left off.
