## Why

The product's main promise is that it gets better with use: every application
and its outcome should sharpen the next search, score, document, and salary
ask. That requires moving from describing the past, to predicting which
postings are worth the effort, to prescribing what to do next, without
pretending to know more than the user's data supports.

## What Changes

- Add outcome insights computed by code: funnel, response and interview rates,
  time to response, ghosting, and breakdowns by score band, title, channel,
  resume kind, and asked-versus-suggested salary, each with its sample size and
  uncertainty.
- Add rules and lessons: the agent proposes lessons with evidence; the user
  applies, ignores, or reverts them in the panel; applied lessons change the
  agent's behavior from its next run. User preferences and system rules live
  in the same list.
- Add outcome prediction: once enough outcomes exist and the model proves
  itself in back-testing, every posting shows an estimated chance of reaching
  an interview.
- Add recommendations: a ranked "apply next" list, salary ask guidance,
  resume emphasis, follow-up timing, and suggested experiments.
- Add the `/analyze-results` skill and the Learning board (board 3 of the
  design), with the active maturity level always visible.

## Non-goals

- Using other people's data or any external training data; the model learns
  from this user's outcomes only.
- Changing rules, weights, or the profile without the user's approval.
- Predicting offers or salaries offered (too few cases for one person).

## Capabilities

### New Capabilities

- `outcome-insights`: descriptive statistics of the user's results.
- `rules-and-lessons`: the list of rules the agent obeys, how lessons are
  proposed, approved, and reverted, and how they take effect.
- `outcome-prediction`: the estimated interview chance per posting and the
  conditions under which it is shown.
- `recommendations`: prescriptive advice derived from insights and predictions.
- `learning-board`: the panel tab that shows all of the above.

### Modified Capabilities

None.

## Impact

- New: `src/jobtracker/core/insights/` (pure Python statistics and model),
  rules tables and effects, `jobtracker insights …`, `jobtracker rules …`,
  `jobtracker predict …`, `.claude/skills/analyze-results/`, Spanish alias,
  Learning board frontend.
- Touches: scoring (history component now supplied by the learning loop),
  search (default minimum score, title priority, and ghost threshold read from
  rules), Search board (interview chance column when level 2 is active).
- No new runtime dependencies.
- Depends on `add-application-tracking`; benefits from
  `add-document-preparation` (resume kind).
