## Why

The product's main promise is that it gets better with use: every application
and its outcome should sharpen the next score, document, and salary ask. That
requires moving from describing the past, to predicting which postings are
worth the effort, to prescribing what to do next, without pretending to know
more than the user's data supports.

Learning feeds on results, so it belongs where results are used: when a posting
is scored and when documents are tailored, not in the search for postings.

## What Changes

- **Learning refresh before scoring and before tailoring.** `/job-search`
  (between filtering and scoring) and `/prepare-documents` (before tailoring)
  run an automatic, cheap refresh: insights are recomputed, the prediction
  model is refitted when enough new outcomes have resolved, active lessons are
  loaded, and new lesson candidates are proposed.
- **The agent gets the whole history.** Every application the user applied to
  and what happened to it (so far), every dismissed posting with its reason,
  and every correction the user made to the agent's readings, from the first
  data point. It is ordered by similarity to the posting at hand but never
  truncated; the agent decides what is relevant and cites the cases it relies
  on in its score notes.
- **Outcome insights** computed by code: funnel, response and interview rates,
  time to response, ghosting, and breakdowns by score band, title, channel,
  resume kind, posting language, work mode, and asked-versus-suggested salary,
  each with its sample size and uncertainty.
- **Rules and lessons:** the refresh and the optional deeper review propose
  lessons with evidence, from outcomes, from repeated dismissal reasons, and
  from work-mode readings the user corrected; the user applies, ignores, or
  reverts them in the panel; applied lessons change scoring, documents, salary
  asks, timing, or the profile from the next run. User preferences and system
  rules live in the same list.
- **Retraining the scoring rubric:** when the validated model shows which
  score components actually predict interviews, the refresh proposes new
  component weights; applying them creates a new weights version.
- **Outcome prediction:** once enough outcomes exist and the model proves
  itself in back-testing, every posting shows an estimated chance of reaching
  an interview.
- **Fit to you:** the user's own track and dismiss decisions (dozens within
  weeks, long before outcomes) train a separate estimate of how well a new
  posting matches what the user usually tracks. It is shown once it proves
  itself in back-testing, always labeled as fit to the user's choices, never
  as a chance of success.
- **Recommendations:** a ranked "apply next" list, salary ask guidance,
  resume emphasis, follow-up timing, and suggested experiments.
- **`/analyze-results`** becomes an optional deeper review (confounding,
  wording of lessons, experiments); the **Learning board** (board 3 of the
  design) shows the active maturity level and the last refresh.
- **Demo history:** the demo seed can load a fictional history that reaches
  each maturity level, so the Learning board can be tried.

## Non-goals

- Learning does not steer searching: no reordering of titles or job sites, no
  extra search filters from lessons. Lessons about titles are suggestions to
  change the profile, applied only by the user.
- Using other people's data or any external training data.
- Changing rules, weights, or the profile without the user's approval.
- Predicting offers or the salary offered (too few cases for one person).
- Using the free-text work-mode detail as a statistical input (the agent may
  read it, but numbers never depend on it).

## Capabilities

### New Capabilities

- `outcome-insights`: descriptive statistics of the user's results and the
  full history the agent receives.
- `rules-and-lessons`: the list of rules the agent obeys, the learning
  refresh, how lessons are proposed, approved, and reverted, and how they take
  effect.
- `outcome-prediction`: the estimated interview chance per posting, the
  fit-to-you estimate, and the conditions under which each is shown.
- `recommendations`: prescriptive advice derived from insights and predictions.
- `learning-board`: the panel tab that shows all of the above.

### Modified Capabilities

None.

## Impact

- New: `src/jobtracker/core/{stats,insights,learning,predict,recommend}.py`,
  migration `0011_learning.sql`, `jobtracker learning refresh`,
  `jobtracker insights …`, `jobtracker rules propose|apply|ignore|revert`,
  `jobtracker predict …`, `.claude/skills/analyze-results/`, Spanish alias,
  Learning board frontend, `learning/` folder in the private home.
- Touches: scoring (history component and influence records), salary,
  documents, and answers (influence records), `jobtracker context` (effects
  and level), the job-search skill (refresh step before scoring; resume
  reference format in `scoring-guide.md`), the prepare-documents skill
  (refresh step), `demo.py` (fictional history; fix of a score note listing a
  skill as both matched and missing), `docs/workspace-layout.md`.
- Uses `work_mode_source` and work-mode events from `add-work-mode-detail`,
  and the dismissal reasons from `add-panel-search-tab`.
- No new runtime dependencies.
