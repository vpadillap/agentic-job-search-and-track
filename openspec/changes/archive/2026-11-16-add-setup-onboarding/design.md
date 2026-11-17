## Context

Implements D1, D6, D13, and D16 of `define-foundation-architecture` for the
first run. The agent drives the conversation; the CLI does every deterministic
step so the result is identical on every machine.

## Goals / Non-Goals

**Goals:** a resumable, idempotent first run; a profile precise enough to
filter and score postings; the user ends up knowing every command.

**Non-Goals:** profile editing UI; job search.

## Decisions

### S1. Fixed step order, resumable

1. `jobtracker doctor` (works with the standard library before anything is
   installed) → install what is missing (`uv sync`, or venv + pip).
2. Ask panel language (en/es). From here on the agent talks in that language.
3. `jobtracker init`; register private terms (name, email, phone) for the
   privacy guard.
4. Resume intake: copy the file as given to `profile/resume-base.<ext>`,
   extract text to `resume-base.md`, show the user a short summary to confirm
   it was read correctly.
5. Questionnaire (S2).
6. Target titles (S3).
7. Provider selection: show providers matching the user's region; install the
   dependencies each enabled provider declares.
8. Record standing preferences as user rules (resume layout consent, cover
   letter policy).
9. Install Spanish aliases if language is Spanish; start the panel; guided tour.

Each completed step is recorded in settings, so re-running `/setup` resumes at
the first incomplete step and offers to revise completed ones.
*Alternative:* one free-form conversation (not resumable, steps get skipped).

### S2. Questionnaire content

Work mode (onsite, hybrid, remote; any combination), contract types
(full-time, part-time, contractor), country and locations/zones for onsite and
hybrid, remote scope (country, region, worldwide), minimum monthly salary and
currency (optional), languages and levels, seniority, industries to prefer or
avoid, companies to exclude, availability, work authorization, and default
posting age (7 days). Answers are stored as structured fields; free-text
nuances become user rules.

### S3. Target titles: ask, research, propose, confirm

The agent asks which titles the user wants, then uses the resume, the answers,
and a preliminary web search of real postings in the user's market to propose
alternates with a one-line reason each. The user includes or excludes each.
States: `included`, `excluded` (kept as negative signal for filtering),
`suggested` (proposed, undecided), `under_review` (set later by the learning
loop). Research results are suggestions only; nothing is included without the
user's answer.
*Alternative:* agent decides titles from the resume alone (misses the user's
intent and market naming).

### S4. Profile is versioned, never edited in place

Any change to needs or titles creates a new profile version inside the active
season; the previous version stays for analysis. Changing the base resume keeps
the old file as `resume-base-v<N>` and enqueues rescoring of open postings.

### S5. Alias installation is a CLI command

`jobtracker skills sync` copies `i18n/skill-aliases/<lang>/*` into
`.claude/skills/` and removes aliases of other languages. Deterministic and
testable; the agent does not hand-write skill files.
*Alternative:* the agent writes the wrappers (drifts between runs).

### S6. Guided tour and README

The tour explains, in the chosen language: what each panel tab is for, each
command with an example, where the data lives and why it is private, and what
to do next (`/job-search`). The README carries the same content permanently,
with an English main body and a Spanish section.

### S7. Changes made after verification

The skill was dry-run end to end by a separate agent with the fictional
persona. It completed, and its friction report led to these changes:

- Titles are set in bulk (`profile titles`), so setup creates a handful of
  profile versions instead of one per title. A proposal's reason is dropped
  when the title's state changes; a mistyped title can be removed.
- The profile gained `remote_region` (which region "region" means) and
  `additional_facts` (things the user confirmed that are not on the resume).
  The truthful-documents system rule now explicitly allows those facts.
- The cover-letter default became a system rule, so it exists in the rule
  list and not only in skill text. The skill stores a preference only when it
  adds something to the listed rules.
- System rules are shown in the panel language, and their text is refreshed
  from the code on initialization. User and learned rules can be reworded and
  retired (`rules edit`, `rules retire`); system rules cannot.
- `privacy terms list` exists; extra terms found in the resume are registered
  in the resume step.
- Messages name the command the user actually runs (`python scripts/jt.py`).
- A command that is not built yet is shown under the name it will have in the
  panel language; a built command is shown by its alias only when the alias is
  installed.
- Skipped questions are simply left out; an earlier answer is cleared by
  sending `null` explicitly.

Deferred: when the base resume changes the system records the moment
(`rescore_since` in the context bundle). Turning that into one pending item per
open posting needs postings, so it is a task of `add-job-search`.

*Alternative considered for aliases of unbuilt commands:* showing English
names until each is built (the tour would teach names that later change).

## Risks / Trade-offs

- [Scanned or image-only resume yields no text] → detect empty extraction and
  ask for a text-based file or let the agent read it visually and confirm.
- [Dependency installation fails on a locked-down machine] → doctor reports the
  exact failing step; providers needing the missing tool are left disabled.
- [Long questionnaire fatigue] → sensible defaults, grouped questions,
  everything revisable by re-running `/setup`.
