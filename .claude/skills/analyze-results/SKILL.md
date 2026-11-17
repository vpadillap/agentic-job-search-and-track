---
name: analyze-results
description: Optional deeper review of the user's job-search results. Reads the complete history (applications and outcomes, tracked and dismissed postings, corrected readings), checks what the numbers can and cannot support, proposes lessons with their evidence for the user to apply or ignore, and suggests experiments when the learning level allows. Never changes anything by itself and never applies to jobs.
---

# Analyze results

Learning already runs on its own: `/job-search` and `/prepare-documents`
refresh it before scoring and before tailoring. This command is the optional,
deeper review the user asks for (the Learning tab suggests it after ten new
outcomes). You read everything, think about what it really shows, and propose
lessons. The user decides; nothing you propose takes effect until they apply
it in the panel's Learning tab.

**The CLI.** From the repository root run `python scripts/jt.py <command>`
(`python3` if `python` is missing). It prints JSON: `{"ok": true, ...}` or
`{"ok": false, "error": {"code", "message"}}`. On an error, read the message,
fix the cause, and retry; never work around it. Below, `jt` means
`python scripts/jt.py`. Pass JSON on standard input (`jt ... -`). Never write
the user's data anywhere outside the private home.

**Hard rules for this whole skill**

- Read `analysis-guide.md` (next to this file) before concluding anything. It
  says what the numbers allow you to say and how to word it.
- Every lesson needs at least five cases and its evidence with counts. Fewer
  cases: say there is not enough data yet, and propose nothing.
- Never apply, ignore, or revert a lesson yourself, and never change the
  profile, the weights, or a rule directly. Lessons go in as proposed; the user
  decides in the panel (or tells you, and then you run
  `jt rules apply|ignore <id>` for exactly what they said).
- System rules are never overridden, and no lesson may change how searching
  works (which sites, in which order, which titles are searched): a title
  lesson is a profile suggestion (`title_state`), applied only by the user.
- Talk to the user in the panel language from `jt context`; lessons are
  written in that language too.

## 1. Load everything

1. `jt context`. If `setup_required` is true, stop and suggest `/setup`. Read
   `rules`, `learning` (level, what the next level needs), and `effects`.
2. `jt learning refresh`. Keep `level`, `summary`, `active_lessons`,
   `candidates`, and `history.path`.
3. Read the complete history file at `history.path`, every line. Records:
   - `application`: one per application, with its full status path, outcome so
     far (`pending` while unresolved), the snapshot of what was known when
     applying (score and its components, resume kind, cover letter, channel,
     salary asked and suggested, posting age), the posting's current work mode
     and language, and the description;
   - `tracked_not_applied` and `dismissal`: the user's decisions on postings,
     with the dismissal reason and note;
   - `correction`: a work-mode reading of yours that the user corrected, per
     job site.
   Nothing is filtered out for you: decide yourself what matters.
4. When the level is predictive or higher, also run `jt predict fit` (this is
   the deeper review's own check of the estimates; it may withdraw them) and
   read `jt learning level` again.

## 2. Look at the numbers

For each period that makes sense (start with `season`, compare with `all`):

- `jt insights summary --period <p>`
- `jt insights breakdown <dimension> --period <p>` for `score_band`, `title`,
  `channel`, `provider`, `resume_kind`, `cover_letter`, `salary_delta`,
  `work_mode`, `language`, and `posting_age`.

Groups marked `insufficient` (fewer than five cases) support no conclusion.
Compare ranges (`low`–`high`), not only rates. Look for confounding as the
guide describes before believing any difference.

Then read qualitatively what the numbers cannot hold: the work-mode details
of postings that reached interview versus those that did not, the notes of
dismissals, the wording of postings that went silent. These can inform the
wording of a lesson's evidence, never invent its numbers.

## 3. Propose lessons

1. `jt insights lessons --period <p>` lists the candidates the system found,
   each with its `key`, `dimension`, `group`, `cases`, `evidence`, and an
   `effect` when one is possible. Some are marked as already proposed,
   applied, ignored, or reverted: do not propose those again unless the
   output says there are five or more new cases.
2. Keep only candidates you can defend after section 2 and the guide. You may
   also write a lesson the system did not list, from the history, if it has at
   least five cases; give it a short, stable `candidate_key` of your own (for
   example `dismissed:location:onsite`).
3. Send them in one call: `jt rules propose -` with a list of
   `{"text", "evidence", "candidate_key", "cases", "area", "effect"}`:
   - `text`: what to do, one sentence the user understands ("Treat an
     application as no response after 29 days");
   - `evidence`: the counts behind it, one or two sentences ("No response
     arrived after day 27; the median is 10.5 days, from 50 responses");
   - `area`: what it affects: `score`, `resume`, `cover_letter`, `form`,
     `salary`, `statuses`, `providers`, `search`, or `general`;
   - `effect`: only when the system can apply it (from the candidate, or one
     of `min_score_shown`, `title_state`, `ghost_after_days`,
     `follow_up_after_days`, `salary_cap_pct`, `resume_emphasis`, `weights`);
     otherwise omit it and the lesson guides the agent through its text.
4. Corrections of your own readings (`correction` records, `corrections`
   candidates) become lessons with area `providers` and no effect: say what to
   read more carefully on that site.

## 4. Experiments (prescriptive level only)

When `level.name` is `prescriptive`, `jt experiments list` shows running ones
and the system's ideas. Only when a difference is real but uncertain (ranges
overlap), propose one: `jt experiments propose <dimension> --question "..."
--planned <n>`. The user accepts or declines it in the panel; an accepted one
concludes by itself after its planned applications.

## 5. Report

Tell the user, in a few short paragraphs:

- the level and what the next one needs;
- what the results show, with counts, for the period you looked at;
- what you could not conclude and why (too few cases, confounding);
- the lessons you proposed, each with its evidence, and that they take effect
  only when applied in the Learning tab of the panel (`jt panel` if it is not
  running);
- at the prescriptive level, any experiment you proposed.

Do not add numbers that are not in the CLI output or the history.
