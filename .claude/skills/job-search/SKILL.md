---
name: job-search
description: "Searches the enabled job sites for new postings that match the user's target titles, filters and scores them, researches salary with linked evidence, and updates the panel. Use when the user asks to search for jobs, look for new postings or openings, or check the job sites, such as “do a job search for this week”, “any new postings?”, “find openings from the last 3 days” (also in Spanish: “busca trabajo”, “haz una búsqueda de empleos”, “hay vacantes nuevas?”). Window: days=N (7 by default). Never applies to anything."
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

## When the request is in plain words

The user may ask without the command ("do a job search for this week",
"busca trabajo de los últimos 3 días"). Read the request:

- A window it states becomes `days`: "this week" / "esta semana" is 7, "the
  last N days" / "los últimos N días" is N, "this month" / "este mes" is 30.
  No window stated: use the profile's window; do not ask.
- The search covers the profile's included titles only. If the user names a
  title that is not among them, say so and offer to add it with `/setup`
  (titles step) before searching; do not search it on the side.
- "Only on <site>" / "solo en <portal>" (for example right after turning a
  new site on): start the run as usual and search only that provider; the
  run records the other enabled sites as not searched. The site must be on;
  if it is not, ask before turning it on (`/setup`, job sites).
- A search visits each enabled site in turn and takes a while. Before step 2
  (starting the run), say in one line the window you will use and that it
  will take a while, and ask to continue.

**Hard rules for this whole skill**

- Read-only on every site. Never apply, submit or save a form, send a message,
  follow or like anything, or change anything in the user's accounts.
- For each job site, `providers/<id>.md` is binding: use exactly the access
  method, URL patterns, and pacing it states, and nothing it marks as not
  working or forbidden. If the file and the site disagree, stop using that
  provider for this run and record it as failed with the reason.
- Never invent facts: descriptions are copied verbatim; dates are what the
  site shows; a salary figure always cites its sources (see `salary-guide.md`).
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
about 150 MB"). Then search as usual. If a reader later answers
`missing_dependency` (for example its browser could not start), run
`jt providers install <id>` once: it checks that the browser really starts
and installs it again when it does not; then read that site again. Only a
provider whose install failed is skipped later, with
`--reason missing_dependency` and the failure in `--detail`.

## 2. Start the run

`jt run start` (add `--days N` when the user gave a window). Keep from the
output: `run_id`, `published_since` (ignore postings published before this
date), `titles` (the included titles: search only these), `capture_folder`
(raw captures go here), `providers`, and `group` (the panel page the run is
shown on).

**One page per day.** A search on the same day as the latest one joins its
page by itself. If you already ran a search **in this conversation** on an
earlier day (remember each `group` you got here), ask once per conversation,
before starting: "Add today's search to the one from <day>, or keep it on its
own page?" Then start with `jt run start --group <that group's id>` or
`jt run start --new-group`, and use the same answer for later searches in this
conversation. Searches from earlier conversations are not asked about.

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
   A provider with `access: web-search` (such as `agentic-search`) is
   searched by you: you discover postings with your web-search tools as its
   file says, then pass the links you found to its reader (`jt providers
   read agentic-search <run_id> --title "<title>" --found <file>`), which
   reads the pages and writes drafts (with `source_site`, the host the
   posting came from). Remember the companies with `jt companies record -`,
   and never invent a publication date (leave it out and add the flag the
   file names). Say in the report when one of its limits (postings or
   companies per title) was reached, and which sites refused to be read.
6. If the site errors, blocks you, or stops matching its recipe, record
   `jt run provider <run_id> <id> --status failed --reason error|blocked
   --detail "<what happened>"` and continue with the next provider. One
   provider failing never stops the run. A reader that answers
   `title_problem` (with `stopped` empty) has not failed: only that title
   ended. Go on with its next title, and name the titles that ended early in
   the report, saying the site has probably changed when the summary sets
   `site_may_have_changed`. Titles with no results are not problems.
7. A reader that answers `stopped.reason: throttled` (the site asked to slow
   down) has not failed: it is cooling down until `resume_after`, and any
   call before then is refused with `provider_cooling` without contacting
   the site. Import what it wrote, go on with the other providers, and then
   tell the user when that site may go on. If they want to wait, keep the
   run open and call the reader again after `resume_after` for the titles it
   did not finish (a finished title answers `already_done`); otherwise
   finish the run, which records the site as failed with reason
   `throttled`. Never try to get past a throttle any other way.

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

1. Group the postings by role family, level, and country: research each such
   market key once per run, and each company once.
2. For each posting, `jt salary lookup <posting_id>` gathers everything
   available: the offered salary, the user's history (offers they received and
   salaries published in stored postings, with company profiles), fresh stored
   evidence, and what was already checked. If `recently_without_data` is true
   and nothing new is in the history, do not research again.
3. Record missing company profiles, search only what is missing, analyse (the
   same company first; otherwise similar companies), and record either
   `jt salary set <posting_id> -` with the range, its inputs, and a short note,
   or `jt salary none <posting_id> --checked "..."`.

## 7. Finish and report

`jt run finish <run_id>` and report to the user from its `run` output, using
the same numbers: found, new, filtered out, duplicates or already seen,
providers skipped and why, and the top results (title, company, score). Close
with how to see them: the Search tab of the panel (`jt panel` if it is not
running). Do not add numbers of your own.
