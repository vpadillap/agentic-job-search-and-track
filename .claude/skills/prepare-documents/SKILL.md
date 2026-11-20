---
name: prepare-documents
description: "Prepares what tracked job applications are missing: a tailored resume, a cover letter where one is needed, and form answers, then rescores them. Use when the user asks to prepare, complete, or tailor documents for their applications, such as “complete the missing documents for J0007”, “get the resumes and cover letters ready”, “tailor my resume for all my applications” (also in Spanish: “completa los documentos faltantes de la J0007”, “prepárame el CV y la carta”, “hazme lo pendiente”). Arguments: pending (default), ids=J0007,J0012, all. Not for general questions about resumes or letters. Never applies to anything."
---

# Prepare documents

You prepare application documents for the person in front of you. Writing and
judgement are yours; storage, versioning, and validation belong to the CLI.
The user reviews everything and applies; you never submit anything.

**The CLI.** From the repository root run `python scripts/jt.py <command>`
(`python3` if `python` is missing). It prints JSON: `{"ok": true, ...}` or
`{"ok": false, "error": {"code", "message"}}`. On an error, read the message,
fix the cause, and retry; never work around it. Below, `jt` means
`python scripts/jt.py`. Pass JSON on standard input (`jt ... -`). Write
documents only at the paths the CLI gives you; never put the user's data
anywhere else.

**Arguments.**

| Argument | What to do |
|---|---|
| `pending` or nothing | everything in `jt pending`: resumes, cover letters, form answers, rescores, and scores of postings the user restored |
| `ids=J0007,J0012` | the same, only for those applications (`jt pending --ids J0007 J0012`) |
| `all` | only tailored resumes, for every application not yet applied to that has none |

Spanish alias: `pendientes` means `pending`, `todas` means `all`.

## When the request is in plain words

The user may ask without the command ("complete the missing documents for
J0007", "prepárame el CV y la carta para la J0012"). Read the request:

- Ids it states (J0007, J0012) become `ids=`. "Everything pending",
  "lo que falta", or no application named: `pending`. "A tailored resume for
  every application" / "CV para todas": `all`.
- An application named by company or title instead of id ("my application at
  the bank"): find it with `jt applications list --hide-ended`. One match: use
  its id. Several: ask which one, naming each (id, company, title), before
  preparing anything. None: say so and stop.
- Only form answers asked for: that is `/form-answers`; use it instead.
- Before preparing for more than three applications, say how many and what
  will be made (from `jt pending`), and ask to continue.

**Hard rules for this whole skill**

- **Truthful.** Never state experience, skills, employers, titles, dates,
  degrees, or results that are not in the base resume or in the profile's
  `additional_facts`. What the posting asks for and the user lacks is
  reported as a gap, never claimed. See `tailoring-guide.md`.
- **Design untouched by default.** Content changes only, unless an active rule
  or the user's answer in this conversation allows more. See the change levels
  in `tailoring-guide.md`.
- **Language of the posting.** Resumes, letters, and answers are written in
  the language of each posting (`posting.language`; if missing, the language
  the description is written in), whatever the panel language is.
- **Never overwrite.** The base resume and earlier versions are never edited;
  every document is a new version. An answer the user edited is never
  replaced (the CLI keeps your new one as an alternative).
- **Never apply** to anything, never fill in or submit a form on a site.

## 1. Load the context

1. `jt context`. If `setup_required` is true, stop and suggest `/setup`.
2. Read every rule in `rules` and follow it. Note the ids of rules with area
   `resume`, `cover_letter`, `form`, or `salary`: you record the ones you
   followed with each document (`applied_rules`).
3. `base_resumes` lists the user's resume per language: each is the source
   for postings in its language. If one has `language: null`, ask the user its
   language and run `jt resume language <code>` before tailoring. Read the
   profile, including `additional_facts`. Only a DOCX resume can be tailored
   without touching its design.
4. Refresh learning before tailoring: `jt learning refresh`. Follow the active
   lessons and `effects` it lists: `resume_emphasis` (terms the user approved to
   highlight, only where the base resume already supports them) and
   `salary_cap_pct` (the most a suggested salary answer may exceed the
   suggestion, in percent). Candidates are not rules; ignore them here.
   Read the complete history file at `history.path`: it shows which postings
   reached interview and with which resume and cover letter. Use it to judge
   what to emphasize, never to claim anything the resume does not support.

## 2. Decide the work

- `pending`: `jt pending` (with `--ids ...` for `ids=`). Items come most
  promising first; keep that order. If `nothing_pending_for` lists ids the
  user gave, tell them those have nothing pending (or are not tracked).
- `all`: `jt applications list --hide-ended` and take every application
  without an `applied_on` date (not applied yet) whose
  `documents.resume_proposed` and `documents.resume_sent` are both empty.

If there is nothing to do, say so and stop.

Group the items by application and handle one application at a time, in the
order above: resume first, then cover letter, then form answers, then the
rescore. If one application fails, note why and continue with the next.
Items of kind `score` (postings the user restored from the filtered-out list,
usually not tracked) are handled after the applications, in step 3e.

## 3. For each application

Start with `jt applications show <job_id>`, and
`jt learning refresh --posting <posting_id>` to get the same complete history
ordered by similarity to this posting (most similar first) with its interview
estimate when one is available. Then read `description` (the posting's
text, at the top level), `posting` (`language`, title, company),
`form_questions`, `score`, `salary`, `cover_letter`, and documents.

### 3a. Tailored resume (item `resume`)

Follow `tailoring-guide.md`. In short:

1. Compare the posting with the base resume. Decide what to emphasize, reorder,
   or reword, staying at the allowed change level.
2. The base is the user's resume in the posting's language. Read its text
   (`jt resume show` → `by_language`, its `text_path`): your `find` texts must
   come from it. If the user has no resume in that language, `documents tailor`
   fails with `no_resume_for_language`: skip this application's resume, and at
   the end ask the user once per language whether to give you a resume in it or
   to translate one of theirs (`.claude/skills/setup/resume-translation.md`).
   DOCX base: send the edits with `jt documents tailor <job_id> -` as
   `{"edits": [...]}`. The result says which `base` was used. Read `layout`
   in the result: if `same_shape` is false,
   or `characters.change_pct` is beyond ±10, look at why and correct it before
   registering. The result is a DOCX: the user opens it in Word, adjusts it,
   and saves it as PDF if the application asks for one.
3. Not a DOCX base: see "When the base resume is not a DOCX" in the guide.
4. Read the text of what you produced before registering it: a registered
   version cannot be removed, only replaced by a newer one.
5. Register it:
   `jt documents register <job_id> resume-proposed <file_name> -` with
   `language`, `summary`, `level`, `support`, `gaps`, `applied_rules`, and
   `base` (the `base.language` from the tailor result). `applied_rules` lists
   the ids of the active lessons and rules you followed; when an applied lesson
   or similar past cases shaped an edit, mention it in `summary` in one plain
   phrase.
6. Registering adds a `rescore` item for this application: run
   `jt pending --ids <job_id>` to get it (and its `resume`), and do 3d after
   the cover letter and answers.

### 3b. Cover letter (item `cover_letter`)

Follow `cover-letter-guide.md` to decide whether one is needed.

- Needed: `jt documents path <job_id> --kind cover-letter --ext md`, write the
  letter there, then `jt documents register <job_id> cover-letter <file_name> -`
  with `language`, a one-line `summary`, `support`, and `applied_rules`.
- Not needed: `jt documents cover-letter <job_id> --need not_required --reason
  "<why, in the panel language>"`.

### 3c. Form answers (item `form_answers`)

Follow `.claude/skills/form-answers/SKILL.md`, steps 2 to 4, for this
application.

### 3d. Rescore (item `rescore`)

Judge the posting again against the resume named in the item: the tailored
resume you just registered, or the one the user uploaded. Use the rubric in
`.claude/skills/job-search/scoring-guide.md` and send
`jt score set <posting_id> -` with `"resume"` set to the item's `resume`
object exactly as `pending` gives it (`{"kind": ..., "ref": ...}`).

Start from the current score (`score.components`) and change only what the
new resume really changes, usually `skills` and sometimes `title`; keep the
points and notes of components it does not affect (`seniority`, `conditions`).
Do not re-judge the whole posting more strictly or more generously: the panel
shows the difference as the effect of the resume. A translated resume with the
same content normally keeps the same score. History is kept.

### 3e. Score a restored posting (item `score`)

The user brought this posting back from the search's filtered-out list, so it
has no score yet. Follow `.claude/skills/job-search/batch-worker.md`, job
`score`, for this posting only: read what it says to read before you start,
skip its filter step (a restored posting is never filtered again; the CLI
refuses it), and score it with `jt score set <posting_id> -`. If it fails
with `no_resume_for_language`, report it and leave it pending.

## 4. Report

Run `jt pending` (with the same `--ids`) once more. Then report to the user,
per application (job id, title, company):

- what was produced (resume version and its summary, cover letter or "not
  required" with the reason, number of answers),
- the gaps you did not claim,
- answers left for them and what each needs,
- the new score, if it changed, and the score of each restored posting
  (title, company, score),
- anything that failed and why.

End with what is still pending (should be nothing but what needs the user) and
where to review it: the Applications tab of the panel (`jt panel` if it is not
running). Remind them to review each document before sending it.
