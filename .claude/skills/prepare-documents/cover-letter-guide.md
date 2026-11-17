# Cover letter guide

## 1. Is one needed?

Write a cover letter only when one of these is true:

1. The posting asks for one (look for "cover letter", "carta de presentación",
   "motivation letter", "carta de motivación", or equivalent in the
   description).
2. One of the form questions asks for one, or asks for a free-text
   "why do you want this job / tell us about yourself" of a letter's length.
3. An active user rule (area `cover_letter`) says to write one in this case,
   for example "always for Lead roles".

Otherwise record it as not needed, with the reason in the panel language:

`jt documents cover-letter <job_id> --need not_required --reason "The posting does not ask for one"`

The system rule `cover_letter_default` says the same; follow user rules that
change it.

## 2. What it says

Use only facts from the base resume, the profile's `additional_facts`, and the
posting. The truthfulness rule of `tailoring-guide.md` applies in full: every
claim must be backed, and you list the backing in `support` when registering.

Structure (in the posting's language):

1. **Opening** (1–2 sentences): the role, where it was seen, and the single
   strongest reason this person fits.
2. **Fit** (1–2 short paragraphs): two or three of the posting's main
   requirements, each matched to concrete experience from the resume.
3. **Why this company** (1–2 sentences): only from what the posting itself
   says about the company or the team. Do not invent knowledge of the company.
4. **Close** (1 sentence): availability to talk.

Do not mention salary unless the posting asks for an expectation in the letter;
then use only the stored suggestion (see the form-answers rules for salary).
Do not mention what the user lacks.

## 3. Length and format

- 150 to 250 words. Shorter is better than padded.
- Plain Markdown, no headings, no placeholders. Use the user's name as it
  appears on the resume to sign; if the company's contact name is unknown, use
  a neutral greeting ("Dear hiring team," / "Estimado equipo de selección:").
- Write it at the path from
  `jt documents path <job_id> --kind cover-letter --ext md`.

## 4. Registering

`jt documents register <job_id> cover-letter <file_name> -` with:

```json
{"language": "es", "summary": "Focused on the dbt and BigQuery requirements.",
 "support": [{"term": "dbt", "source": "Designed and maintained Airflow and dbt pipelines."}],
 "applied_rules": []}
```

Registering a letter marks the application's cover letter as required.
