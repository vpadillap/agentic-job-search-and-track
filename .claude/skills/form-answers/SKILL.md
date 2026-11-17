---
name: form-answers
description: Proposes answers to the application-form questions of one or more tracked jobs (ids=J0007,J0012), grounded only in the user's resume, profile, and stored data, in the posting's language. Questions it cannot answer truthfully are left for the user with a note. With `alternative` it proposes another version to pick from, without replacing the current answers. Never fills in or submits a form.
---

# Form answers

You propose answers the user will copy into application forms. Only facts the
user's data supports go in an answer; the user reviews everything.

**The CLI.** From the repository root run `python scripts/jt.py <command>`
(`python3` if `python` is missing). JSON in and out; on an error read the
message, fix the cause, retry. Below, `jt` means `python scripts/jt.py`.

**Arguments.** `ids=J0007,J0012` (required: which applications). Add
`alternative` to propose other versions instead of replacing current answers
(Spanish alias: `alternativa`).

## 1. Load the context

1. `jt context`. If `setup_required` is true, stop and suggest `/setup`.
2. Follow every rule in `rules`; note the ids of rules with area `form` or
   `salary` that you follow.
3. Read the base resume text (`base_resume.text_path`) and the profile,
   including `additional_facts`, `availability`, `work_authorization`,
   `languages`, and `minimum_salary`.

## 2. Read the questions

For each id: `jt answers list <job_id>`.

- `questions` empty: tell the user there is no captured form to answer for that
  application and continue with the next id.
- Otherwise note each question's `position`, `text`, `kind`, `options`,
  `required`, and any current `answer` (with its `origin`) and `alternatives`.

Also `jt applications show <job_id>` for `posting.language`, `description`
(the posting's text, at the top level), and `salary` (the stored suggestion).

## 3. Write each answer

Write in the posting's language. One answer per question.

**Grounding.** An answer may only use:

- the base resume and the profile (including `additional_facts`),
- the stored salary suggestion for salary questions,
- the posting itself (to understand the question).

If the answer needs a fact that is not there (a portfolio link, a notice
period that is not in `availability`, a reference, a certification number),
do not guess: send it with `"needs_user": true`, an empty `text`, and a `note`
(panel language) saying exactly what is missing. The panel shows it as
needing their input.

**Kinds of questions.**

| Question | How to answer |
|---|---|
| years of experience with X | count from the dates in the resume; if X is not in the resume, say so plainly or leave it for the user, never inflate |
| yes/no or choice (`options` present) | pick exactly one of the `options` text as given; if none is truthful, leave it for the user |
| salary expectation | if `salary.status` is `suggested`, use its amount, currency, and basis, within any active salary rule (for example a cap over the median), and set `"basis"` to say it is based on the suggested salary; if there is no reliable salary data, leave it for the user (`needs_user`) and say so in the `note`; never invent a figure |
| availability / start date | from the profile's `availability`; otherwise leave it for the user |
| work authorization, visa | from the profile's `work_authorization`; otherwise leave it for the user |
| motivation, "tell us about you" | short, from the resume and the posting, same rules as the cover letter |
| free text with a length limit | respect it |

Keep answers short and direct. No placeholders.

`applied_rules` lists the ids of rules that shaped that answer (for example a
salary cap you applied). An answer left for the user normally cites none.

## 4. Store the answers

```
jt answers set <job_id> - <<'JSON'
[
  {"position": 1, "text": "5 years, maintaining production Airflow pipelines.", "language": "en"},
  {"position": 2, "text": "PEN 15,000 gross per month.", "language": "en",
   "basis": "Based on the suggested salary", "applied_rules": [12]},
  {"position": 3, "text": "", "needs_user": true, "language": "en",
   "note": "Your resume and profile do not include a portfolio link."}
]
JSON
```

With `alternative`, use `jt answers alternative <job_id> -` instead: your
versions are stored next to the current ones for the user to pick.

The CLI never replaces an answer the user edited: your new answer for that
question is kept as an alternative (the result lists it under
`alternatives`). Tell the user when that happens.

## 5. Report

Per application: how many answers were proposed, which ones need the user and
what each needs, and which questions already had the user's own answer. Point
them to the Applications tab of the panel to review, edit, and copy answers.
