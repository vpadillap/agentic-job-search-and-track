# Scoring guide

The score says how well one posting fits the user, from 0 to 100. You judge
four components; the system adds the fifth (history). The maximums come from
the active weights version (`score_weights` in `jt context`); the defaults are
below. Judge only from the posting text, the user's resume in the posting's
language, and the profile.

| Component | Default max | What it measures |
|---|---|---|
| `title` | 25 | how close the role is to an included target title |
| `skills` | 35 | required and desirable skills found in the resume |
| `seniority` | 15 | years and level asked vs what the resume shows |
| `conditions` | 15 | work mode, contract, location, language, published salary vs the profile |
| `history` | 10 | from the user's own outcomes: follows the interview estimate once the estimates are validated (predictive level), neutral (half) before. Never send it |

## How to judge each component

- **title**: full points for the same role as an included title (wording
  differences like "Sr." or "Ingeniero de Datos" count as the same); about
  half for an adjacent role (Analytics Engineer for a Data Engineer); low for
  a different role that survived the filter.
- **skills**: list the posting's required and desirable skills. `matched` are
  the ones present in the resume (or confirmed facts in the profile);
  `missing` are the rest. Points follow the share of required skills matched;
  a missing desirable skill costs less than a missing required one. The note
  must name every missing skill.
- **seniority**: full points when the asked years/level match the resume;
  fewer when it asks for clearly more, or clearly less (also flag the posting
  in that case).
- **conditions**: start from the maximum and subtract for each condition that
  only partly fits (for example hybrid when remote is preferred, or a language
  level above the user's).

Notes are one or two plain sentences in the panel language, specific to this
posting. Do not repeat the points in words.

## Submission

```json
{
  "components": {
    "title": {"points": 25, "note": "Same role as the target title “Senior Data Engineer”."},
    "skills": {"points": 27, "note": "Matches Python, SQL, Airflow, dbt, BigQuery. Missing: Kafka (desirable).",
               "matched": ["Python", "SQL", "Airflow", "dbt", "BigQuery"], "missing": ["Kafka"]},
    "seniority": {"points": 15, "note": "Asks for 5+ years; the resume shows 7."},
    "conditions": {"points": 14, "note": "Remote and full-time as requested; intermediate English."}
  }
}
```

The total is computed by the CLI (here 25 + 27 + 15 + 14 + 5 neutral history
= 86). If you include `"total"`, it must match. `resume` defaults to the
user's current resume in the posting's language. When scoring against another
resume (a rescore item from `jt pending` or `jt context`), send that item's
`resume` object exactly as given, for example
`"resume": {"kind": "tailored", "ref": "resume-proposed-v2.docx#v2"}`; never
build the reference yourself.

## Rescoring

`jt context` lists `pending` items of kind `rescore` when the resume changed
after a score, or when the user applied a lesson that changed the score
weights. Score those postings again the same way; the previous
score stays in history and the panel shows the change.
