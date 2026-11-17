# Target titles: ask, research, propose, confirm

The titles decide what gets searched, so they are worth doing carefully. The
user decides; you inform.

## 1. Ask

Ask which job titles they want to be found for. Accept them as written. Store
them immediately as included, all in one call:

```
python scripts/jt.py profile titles - <<'JSON'
[
  {"title": "Senior Data Engineer", "state": "included"},
  {"title": "Data Platform Engineer", "state": "included"}
]
JSON
```

## 2. Research

Goal: find how the market in the user's country and language actually names
the roles this person fits, so searches do not miss postings that use a
different title.

Use the web search and browsing tools you have. Keep it short: a handful of
searches, not an exhaustive study.

1. For each title the user gave, search real, current job postings in their
   country (and in the remote scope they chose). Search in the languages they
   work in: a market may use both "Data Engineer" and "Ingeniero de Datos".
2. From postings whose requirements match the resume, collect the titles that
   companies use for that same work: synonyms, translations, adjacent roles one
   step sideways or up, and common seniority variants.
3. Note titles that look similar but whose postings ask for a clearly different
   profile than the resume shows. These are candidates to exclude.

Do not invent market facts. For each title, say what you actually saw
("several current postings in Lima use this title for the same stack"). You
may also propose a title you did not see in this session when the resume
suggests it, or to offer excluding a common look-alike, but label it as not
verified against the market. With no web access at all, say so plainly and
label every proposal that way. A demand ranking or a salary figure is not part
of this step.

## 3. Propose

Present a short list (aim for 3 to 8), each with one line of reasoning tied to
the resume or to what you saw:

- **Analytics Engineer**: same stack as your last two roles (dbt, SQL
  modeling); used by several current postings in your market.
- **ETL Developer**: appears often, but postings ask mainly for tools that are
  not on your resume. Suggest excluding.

Record all proposals as suggested before asking, in one call, so nothing is
lost if the conversation is interrupted. Reasons are written in the panel
language:

```
python scripts/jt.py profile titles - <<'JSON'
[
  {"title": "Analytics Engineer", "state": "suggested", "reason": "Same stack as your last two roles; used by several current postings in your market."},
  {"title": "ETL Developer", "state": "suggested", "reason": "Common, but postings ask mainly for tools not on your resume. Not verified in this session."}
]
JSON
```

## 4. Confirm

Ask the user to decide on each proposal: include, exclude, or leave for later.

Record all decisions in one call:

```
python scripts/jt.py profile titles - <<'JSON'
[
  {"title": "Analytics Engineer", "state": "included"},
  {"title": "ETL Developer", "state": "excluded"}
]
JSON
```

| Decision | State to send |
|---|---|
| Include | `included` |
| Exclude | `excluded` |
| Later / no answer | nothing; it stays `suggested` |

The reason you gave for a proposal is dropped when its state changes, because
it described the proposal. To change a single title later use
`python scripts/jt.py profile title "<title>" <state>`; to delete a mistyped
one, `python scripts/jt.py profile remove-title "<title>"`.

Rules:

- Never mark a title `included` without the user's explicit yes.
- An excluded title is useful: searches skip it and postings matching it get
  flagged. Offer exclusion for look-alike titles the user does not want.
- If the user includes more than about eight titles, mention that searches
  take longer and results get noisier, and let them decide.
- There is a fourth state, `under_review`. It is set later by the learning
  loop when results suggest a title is not working; do not use it in setup.

## 5. Read back

The output of the last command is the stored profile. Show the user the final
lists: included, excluded, and suggested-for-later.
