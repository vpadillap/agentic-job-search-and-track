---
name: job-search
description: "Searches the enabled job sites for new postings that match the user's target titles, filters and scores them, researches salary with linked evidence, and updates the panel. Use when the user asks to search for jobs, look for new postings or openings, or check the job sites, such as “do a job search for this week”, “any new postings?”, “find openings from the last 3 days” (also in Spanish: “busca trabajo”, “haz una búsqueda de empleos”, “hay vacantes nuevas?”). Window: days=N (7 by default). Never applies to anything."
---

# Job search

You run one search for the person in front of you. The browsing and the
judgement are yours; storage, de-duplication, validation, and counting belong
to the CLI. Follow the steps in order; steps 3 and 4 run together: batches
are filtered and scored while you go on searching, so the user can start
reviewing results in the panel long before the search ends.

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

## 2b. Refresh learning once

Learning feeds on results, so it is refreshed once per run, here, before any
posting is scored, and never again during the search: `jt learning refresh`.
It recomputes what the user's results show, refits the estimates only when
enough new outcomes arrived, writes the complete history file, and lists
`effects`, `active_lessons`, and `candidates`. Keep `history.path`, the
effects, and the active lessons: every batch of this run is judged with them
(step 4). Candidates are not rules: never act on them; they are for
`/analyze-results` and the panel's Learning tab.

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
   duplicate, or already seen. Do not de-duplicate yourself. Import each
   title as soon as it is read, and add its new postings to the queue of
   step 4 before going on. When the
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
   the site. Import what it wrote and queue it, and go on with the other
   providers and titles while the helpers keep working on the queue; a
   cool-down never holds up the rest of the search. Once its `resume_after`
   has passed, call the reader again for the titles it did not finish (a
   finished title answers `already_done`), in the same run. If nothing else
   is left to search before that time, tell the user when that site may go
   on and ask whether to wait. If they want to wait, keep the run open and
   resume it then; otherwise finish the run once step 5 is done, which
   records the site as failed with reason `throttled`. Never try to get past
   a throttle any other way.

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
| `flags` | doubts to show the user (see `batch-worker.md`) |
| `form_questions` | only if visible without starting an application: `[{text, kind, options, required}]` |

The same job on two sites is two postings. The panel marks them as possible
duplicates and the user picks the site; do not merge or drop either.

## 4. Filter, score, and price each batch while you search

A **batch** is what one import brought in: the new postings of one title on
one site (`outcome: new` in the import report). The user watches the panel
while you search, so every batch is filtered and scored right away, not
after the last site. The panel shows imported postings as "Scoring…" until
they have a score.

Keep a **queue** of batches in import order. After each import, add its new
posting ids to the queue and go on searching. The work on the queue is done
by background helpers that follow `batch-worker.md` in this folder:

- **At most 3 helpers at the same time**, whatever the number of titles and
  sites. This cap protects the user's usage limit: never go over it, and
  never start a helper per batch just because batches are waiting.
- A **score** helper takes every batch waiting in the queue when it starts,
  up to 25 postings in all, oldest first. When a helper finishes and the
  queue is not empty, start the next one.
- At most **one salary helper** at a time, counted in the 3. It takes the
  scored postings at or above the minimum shown in the panel (an active rule
  may set it; otherwise all), best score first, at most 15 postings per run
  in all, and never a posting it or an earlier salary helper already took.
  Start it when enough scored postings wait for it, or when the search is
  done.
- Start each helper with your background-agent tool (in Claude Code, the
  Agent tool with `run_in_background: true`), and give it in its message:
  the path `.claude/skills/job-search/batch-worker.md` to read and follow,
  its job (`score` or `salary`), the `run_id`, the posting ids it takes, the
  panel language, and from step 2b the history file's path with the
  `effects` and `active_lessons`. Do not wait for it: you are told when it
  finishes, and you go on searching meanwhile.
- Read each helper's report. Postings it left unscored with
  `no_resume_for_language` are collected for step 5. A posting left
  unscored for another reason goes back to the queue once.

**Without background helpers** (your tools cannot start agents that run on
their own): do the same work yourself, in the same order. Right after each
import, follow `batch-worker.md` (job `score`) for that batch, then go on
with the next title. Research salary between sites and while a site is
cooling down (job `salary`, with the same limits).

If the user tells you a posting's real work mode (for example after opening it),
record it with `jt postings work-mode <posting_id> --mode remote|hybrid|onsite|none
--detail "..."`. It is kept as the user's and no later search overwrites it.

## 5. Before finishing

1. Wait until the queue is empty and no helper is running. Then
   `jt postings list --run <run_id> --outcome new`: any new posting without a
   score that was not left aside for `no_resume_for_language` goes through
   the queue once more.
2. Start the salary helper for the scored postings it has not taken yet, if
   any remain within the run's 15, and wait for it.
3. If postings were left unscored with `no_resume_for_language`, the user has
   no resume in that language: ask the user once per language whether to
   give you a resume in it or to translate one of theirs (follow
   `.claude/skills/setup/resume-translation.md`), and score them after that
   (job `score`).

## 6. Finish and report

`jt run finish <run_id>` and report to the user from its `run` output, using
the same numbers: found, new, filtered out, duplicates or already seen,
providers skipped and why, and the top results (title, company, score). Close
with how to see them: the Search tab of the panel (`jt panel` if it is not
running). Do not add numbers of your own.
