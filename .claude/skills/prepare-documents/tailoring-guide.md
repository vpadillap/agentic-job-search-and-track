# Tailoring guide

How to adapt the user's resume to one posting without inventing anything and
without touching the design they did not allow you to touch.

## 1. Truthfulness

You may **select, reorder, reword, and emphasize** what the base resume and the
profile's `additional_facts` already say. You may **not add** employers, job
titles, dates, degrees, certifications, skills, tools, numbers, or results that
are not there, and you may not stretch them (a tool used "in personal projects"
does not become "in production"; "contributed to" does not become "led").

When the posting asks for something the user does not have, leave it out of the
resume and list it in `gaps` (one short line each, in the panel language), for
example `"Kafka (asked as desirable): not in your resume"`. The user sees the
list and can decide to add it themselves if it is true.

### The support list

Every skill, tool, or achievement you **emphasize or add wording for** gets an
entry in `support`:

```json
{"term": "BigQuery", "source": "Modeled commercial and inventory data on BigQuery."}
```

`source` is the line of the base resume (or the additional fact) that backs the
term, quoted closely enough that the user can find it. If you cannot point to a
source, the term does not go in the resume.

## 2. Change levels

| Level | What it allows | Consent |
|---|---|---|
| `light` | the summary/profile paragraph; order of bullets within a section; order of skills; wording inside existing bullets; dropping a bullet that is irrelevant to this posting | none needed (default) |
| `medium` | adding or removing whole sections that exist in the base resume; changing the overall length (for example a one-page version) | once, stored as a user rule |
| `heavy` | layout, template, fonts, columns, structure; rebuilding the resume from its text | each time, unless a user rule says otherwise |

Before tailoring, read the active rules with area `resume`:

- A rule that forbids design changes (for example "never change my resume
  layout") means you stay at `light`, and you do not ask about more.
- A rule that allows `medium` changes lets you use them; record its id in
  `applied_rules`.
- Without such a rule, stay at `light`. If this posting really calls for more
  (for example the posting asks for a one-page resume), ask the user once,
  explain the change, and record their answer as a rule with
  `jt rules add --area resume --text "<their decision>"` so you never ask again.

Record the level you used in `level` when registering.

## 3. Writing the edits (DOCX base)

`jt documents tailor <job_id> -` copies the base resume and applies your edits
in place; formatting stays as it is. Edits are applied all or nothing: if one
fails, nothing is written and the error says which one.

```json
{"edits": [
  {"find": "Data engineer with seven years", "replace": "Data platform engineer with seven years"},
  {"move": "Modeled commercial and inventory data", "before": "Designed and maintained"}
]}
```

- `find` / `replace`: replace text inside one paragraph. `find` must appear in
  exactly one paragraph; quote more of it if it is not unique. Keep `replace`
  close in length so the resume keeps its length.
- `move` / `before`: move the paragraph containing `move` in front of the one
  containing `before` (reordering bullets or skills).
- Tables are included. Headers and footers are not edited.

After it runs, check `layout`:

- `same_shape: false`: shorten your replacements or drop an edit, and tailor
  again (a new version is created; that is fine, but register only the one you
  keep).
- `characters.change_pct` beyond ±10 when you are not translating: you are
  probably rewriting rather than tailoring; reconsider. A translation can
  legitimately change the length; then watch `same_shape`.
- Read the produced text before registering it. A registered version cannot
  be removed, only replaced by a newer one.

The tailored resume is delivered as a DOCX. Tell the user to open it in
Word, adjust anything they want, and save it as PDF if the application asks
for one.

## 4. When the base resume is not a DOCX

A PDF cannot be edited in place without changing its design.

1. Ask the user for the editable source (DOCX). If they give it, import it as
   the new base resume with `jt resume import <file> --language <code>` and
   tailor that.
2. If they have no editable version, a tailored resume means rebuilding it from
   its text: that is a `heavy` change. Do it only with their consent (or a user
   rule that allows it). Then write it as Markdown at
   `jt documents path <job_id> --kind resume-proposed --ext md`, keep the
   section order and headings of the original, and register with
   `"level": "heavy"`.
3. Without consent, skip the resume for this application and report it.

## 5. Language

Write in the posting's language. The user may have their own resume in
several languages; `jt documents tailor` starts from the one in the posting's
language when it exists, and says `translate: false`. Then do not translate:
tailor the user's own wording.

Only when `translate` is true (the user has no resume in the posting's
language, so the main one was used) is the tailored resume a translation plus
tailoring. Mention in your report that the user can give you a version in that
language to use next time. When translating:

- Translate faithfully, line by line; translate section headings too.
- Employer names, product names, and certifications stay as they are.
- Job titles: keep the original title when it is the usual term in the
  posting's market (many tech titles stay in English); otherwise translate it.
  Do not infer the user's gender from their name: if the language needs a
  gendered form, use the one the user already uses (profile, earlier
  documents) or a neutral wording, and mention it in the summary.
- Start the `summary` with "Translated from <language>." so the user knows.
- `characters.change_pct` beyond ±10 is expected when translating; watch
  `same_shape` instead.

If the base used is older than the main resume (compare `imported_at` in
`jt resume show`), say so in your report: the user may have updated only one
language version.

## 6. The summary

`summary` (required) tells the user, in the panel language and in one to three
sentences, what you changed and why, for example: "Profile paragraph rewritten
toward data platform work; BigQuery bullets moved to the top because the
posting leads with it; dropped the SSIS bullet, which this role does not use."
