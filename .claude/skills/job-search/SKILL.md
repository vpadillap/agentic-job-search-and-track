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

## 1b. Make sure every enabled job site can run

The user never installs anything by hand: you do. `jt doctor`. For every
`provider:<id>` check that fails because a tool is missing (an update can
change what a site needs), run `jt providers install --enabled`. It installs
the missing tools into the project's environment and checks they work. Tell
the user in one line what was installed and why, with its size (for example:
"Bumeran and Indeed now read without opening a window; I installed Scrapling,
about 150 MB"). Then search as usual. Only a provider whose install failed is
skipped later, with `--reason missing_dependency` and the failure in
`--detail`.

## 2. Start the run

`jt run start` (add `--days N` when the user gave a window). Keep from the
output: `run_id`, `published_since` (ignore postings published before this
date), `titles` (the included titles: search only these), `capture_folder`
(raw captures go here), and `providers`.

If `to_search` is empty, finish the run with `jt run finish <run_id>` and
stop. Tell the user why: if `providers` lists sites with status `disabled`,
name them and say that job sites start switched off and are turned on in
`/setup` or with the job-site switches in the panel's Search tab. Never turn
a site on yourself. If there are no sites at all, say that none is available
yet (each site is added by its own update).

A local site that works only in other countries than the profile's arrives
already `skipped` with reason `other_country` (its `detail` names its
countries): do not search it, and name it in the report. If every enabled site
was skipped this way, say that the user can turn on the global sites or the
sites of their country in the panel.

## 3. Search each provider

For each provider id in `to_search`, in order:

1. Read `providers/<file>` completely.
2. If it is `live_walk: true` and the user has not confirmed in this
   conversation that they are present to watch the browser, record
   `jt run provider <run_id> <id> --status skipped --reason live_walk` and
   continue with the next provider. Do the same with `--reason
   login_required` when it needs a login the user did not confirm, and with
   `--reason missing_dependency` when a tool it needs could not be installed
   in step 1b.
3. Search every title in `titles` with the provider's recipe, applying the
   profile's location, work mode, and posting-age filters when the site
   offers them. Respect `max_results_per_query` and
   `min_seconds_between_requests`.
4. Save what you read (page text or JSON) into `capture_folder`, one file per
   query, named `<provider>-<n>.txt` or `.json`. These are for audit only.
5. For each posting build a record (fields below) and send them in batches:
   `jt postings import <run_id> -`. The command decides what is new, a
   duplicate, or already seen. Do not de-duplicate yourself. When the
   provider file uses a reader (`jt providers read <id> …`), the reader
   writes the records as drafts: read them, write only your reading of each
   one, and import with `jt postings import <run_id> <drafts> --readings
   <file>` as the provider file says. Never retype a captured description.
   Some readers add **hints** to each draft (fields starting with `site_`,
   such as `site_work_mode` or `site_salary`): what the site itself states.
   Start your reading from them, check them against the title and the
   description, and when they disagree follow the description and add a
   flag saying so (in the panel language). Hints are never imported as they
   are; only your reading is.
   A provider with `access: web-search` (such as `agentic-search`) has no
   reader: you search and read the web yourself as its file says, build each
   record (with `source_site`, the host the posting came from), remember the
   companies with `jt companies record -`, and never invent a publication
   date (leave it out and add the flag the file names). Say in the report
   when one of its limits (postings or companies per title) was reached.
6. If the site errors, blocks you, or stops matching its recipe, record
   `jt run provider <run_id> <id> --status failed --reason error|blocked
   --detail "<what happened>"` and continue with the next provider. One
   provider failing never stops the run.

Posting record (JSON object; `null` or omit what the site does not show):

| Field | Notes |
|---|---|
| `provider`, `external_id`, `url` | the site's own id and canonical link |
| `title`, `company`, `location`, `country` | as shown; `country` as ISO code (PE) |
| `work_mode` | remote, hybrid, onsite: decide it by reading the title and the complete description, not by matching words (a "remote" in a benefits list or in another job's title is not this posting's mode); `null` when the posting does not say, and then add the flag "work mode not stated" (in the panel language) |
| `work_mode_detail` | how the posting describes the arrangement when it says more than the mode, in the posting's language and close to its words ("Híbrido: 2 días presencial por semana", "Summer hours: Fridays until noon"); at most 200 characters; `null` otherwise. Never invented |
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
| `work_mode` | its stated work mode is not among the accepted ones (a posting whose work mode is not stated is never excluded for this) |
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

If the user tells you a posting's real work mode (for example after opening it),
record it with `jt postings work-mode <posting_id> --mode remote|hybrid|onsite|none
--detail "..."`. It is kept as the user's and no later search overwrites it.

## 5. Refresh learning, then score what is left

Learning feeds on results, so it is refreshed here, after filtering and before
scoring, never during the search itself:

1. `jt learning refresh`. It recomputes what the user's results show, refits
   the estimates only when enough new outcomes arrived, writes the complete
   history file, and lists `effects`, `active_lessons`, and `candidates`.
   Follow the active lessons and effects (they are the user's decisions).
   Candidates are not rules: never act on them; they are for `/analyze-results`
   and the panel's Learning tab.
2. Read the history file at `history.path` completely. It holds every
   application with its outcome so far, every posting the user tracked or
   dismissed (with the reason), and every work-mode reading the user corrected.
   Nothing is left out; decide yourself what is relevant. For a posting you are
   scoring, `jt learning refresh --posting <id>` orders the same complete
   history by similarity to it (most similar first) and adds the posting's
   interview estimate and fit when they are available.
3. Corrections of your own readings (records of type `correction`) tell you
   how this site's postings mislead you; read work modes more carefully where
   the user had to correct them.

For each remaining new posting, judge it against the user's resume and profile
with the rubric in `scoring-guide.md` (read it before the first score), then
`jt score set <posting_id> - --run <run_id>`. The CLI rejects inconsistent
scores; fix and resubmit. History is added by the system. When similar past
cases or an applied lesson informed your judgement, say so in the note in one
plain phrase (for example "Similar postings you applied to reached interview
3 of 4 times" or "Applied lesson: …"); never cite a pattern the history does not
show.

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
