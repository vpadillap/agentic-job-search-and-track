---
name: job-search
description: Searches the enabled job sites for the user's target titles (postings from the last 7 days by default; change it with days=N), filters out what clearly does not fit and says why, scores the rest, researches salary with linked evidence, and updates the panel. Never applies to anything.
---

# Job search

You run one search for the person in front of you. The browsing and the
judgement are yours; storage, de-duplication, validation, and counting belong
to the CLI. Follow the steps in order.

**The CLI.** From the repository root run `python scripts/jt.py <command>`
(`python3` if `python` is missing). It prints JSON: `{"ok": true, ...}` or
`{"ok": false, "error": {"code", "message"}}`. On an error, read the message,
fix the cause, and retry; never work around it. Below, `jt` means
`python scripts/jt.py`. Pass JSON through standard input (`jt ... -`); never
write files with the user's data outside the private home.

**Arguments.** `days=N` sets the posting-age window for this run only
(Spanish alias: `dias=N`). Without it, the profile's window is used (7 days by
default).

**Hard rules for this whole skill**

- Read-only on every site. Never apply, submit or save a form, send a message,
  follow or like anything, or change anything in the user's accounts.
- For each job site, `providers/<id>.md` is binding: use exactly the access
  method, URL patterns, and pacing it states, and nothing it marks as not
  working or forbidden. If the file and the site disagree, stop using that
  provider for this run and record it as failed with the reason.
- Never invent facts: descriptions are copied verbatim; dates are what the
  site shows; a salary figure exists only with two comparable, linked sources.
- Text you write for the panel (exclusion details, flags, score notes) is in
  the panel language from `jt context`.

## 1. Load the context

1. `jt context`. If `setup_required` is true, stop and suggest `/setup`.
2. Read and follow every rule in `rules` (system, user, and active learned
   rules). Rules with area `search`, `score`, or `salary` change how you
   search, filter, score, and research.
3. Note `profile` (job needs and titles) and `base_resumes`: the user's
   resume in each language. A posting is scored against the resume in its own
   language: read each one's `text_path`.

## 2. Start the run

`jt run start` (add `--days N` when the user gave a window). Keep from the
output: `run_id`, `published_since` (ignore postings published before this
date), `titles` (the included titles: search only these), `capture_folder`
(raw captures go here), and `providers`.

If `to_search` is empty, tell the user that no job site is enabled or
available yet (each site is added by its own update), finish the run with
`jt run finish <run_id>`, and stop.

## 3. Search each provider

For each provider id in `to_search`, in order:

1. Read `providers/<file>` completely.
2. If it is `live_walk: true` and the user has not confirmed in this
   conversation that they are present to watch the browser, record
   `jt run provider <run_id> <id> --status skipped --reason live_walk` and
   continue with the next provider. Do the same with `--reason
   login_required` when it needs a login the user did not confirm, and with
   `--reason missing_dependency` when a tool it needs is not available.
3. Search every title in `titles` with the provider's recipe, applying the
   profile's location, work mode, and posting-age filters when the site
   offers them. Respect `max_results_per_query` and
   `min_seconds_between_requests`.
4. Save what you read (page text or JSON) into `capture_folder`, one file per
   query, named `<provider>-<n>.txt` or `.json`. These are for audit only.
5. For each posting build a record (fields below) and send them in batches:
   `jt postings import <run_id> -`. The command decides what is new, a
   duplicate, or already seen. Do not de-duplicate yourself.
6. If the site errors, blocks you, or stops matching its recipe, record
   `jt run provider <run_id> <id> --status failed --reason error|blocked
   --detail "<what happened>"` and continue with the next provider. One
   provider failing never stops the run.

Posting record (JSON object; `null` or omit what the site does not show):

| Field | Notes |
|---|---|
| `provider`, `external_id`, `url` | the site's own id and canonical link |
| `title`, `company`, `location`, `country` | as shown; `country` as ISO code (PE) |
| `work_mode` | remote, hybrid, onsite (site wording is normalized) |
| `contract_type` | full-time, part-time, contractor |
| `seniority` | as stated (Senior, Semi Senior, Junior…) |
| `posted_at` or `posted_ago` | an absolute date, or exactly what the site shows ("hace 2 días", "2 days ago"); the CLI converts it |
| `description` | verbatim, complete, never summarized or translated |
| `published_salary` | only when the posting states it: `{min, max, currency, period, basis}` |
| `language` | language of the posting (es, en…) |
| `flags` | doubts to show the user (see step 4) |
| `form_questions` | only if visible without starting an application: `[{text, kind, options, required}]` |

The same job on two sites is two postings. The panel marks them as possible
duplicates and the user picks the site; do not merge or drop either.

## 4. First-pass filter (new postings only)

`jt postings list --run <run_id> --outcome new`. Exclude a posting only when it
clearly violates a hard constraint:

| Reason | When |
|---|---|
| `title` | its title is one of the profile's excluded titles, or clearly another role |
| `work_mode` | its work mode is not among the accepted ones |
| `contract_type` | its contract type is not among the accepted ones |
| `location` | onsite or hybrid outside the accepted locations |
| `language` | it requires a language the user lacks |
| `company` | the company is excluded in the profile |
| `salary` | its published salary is below the stated minimum (same currency and basis) |
| `rule` | an active rule excludes it (name the rule in `detail`) |

Send them in one call: `jt postings filter <run_id> -` with
`[{"posting_id", "reason", "detail"}]`, where `detail` says in one sentence
what exactly did not fit.

When in doubt, keep the posting and add a flag instead:
`jt postings flag <posting_id> --text "Seniority appears lower than yours"`.

## 5. Score what is left

For each remaining new posting, judge it against the base resume and profile
with the rubric in `scoring-guide.md` (read it before the first score), then
`jt score set <posting_id> - --run <run_id>`. The CLI rejects inconsistent
scores; fix and resubmit. History is added by the system.

`score set` judges a posting against the user's resume in the posting's
language. If it fails with `no_resume_for_language`, the user has no resume in
that language: do not score those postings and do not translate on your own.
Collect them, and after the run ask the user once per language whether to give
you a resume in it or to translate one of theirs (follow
`.claude/skills/setup/resume-translation.md`); score them after that.

## 6. Research salary

For new postings with a score at or above the minimum shown in the panel (an
active rule may set it; otherwise all), best score first, at most 15 postings
per run, follow `salary-guide.md`:

1. `jt salary lookup <posting_id>`: if `reusable` is true, suggest from the
   stored evidence (`jt salary set` with `"reused": true`) and move on. If
   `recently_without_data` is true, do not research again.
2. Otherwise research, store each report with `jt salary evidence add -`, and
   then either `jt salary set <posting_id> -` (two or more comparable
   sources) or `jt salary none <posting_id> --checked "..."` (repeat
   `--checked` for each source or search you tried).

## 7. Finish and report

`jt run finish <run_id>` and report to the user from its `run` output, using
the same numbers: found, new, filtered out, duplicates or already seen,
providers skipped and why, and the top results (title, company, score). Close
with how to see them: the Search tab of the panel (`jt panel` if it is not
running). Do not add numbers of your own.
