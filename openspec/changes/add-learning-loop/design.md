## Context

Implements D11 and D12 of `define-foundation-architecture`. Visual reference:
board 3 of `design/panel-ux.html` (KPIs, lessons with Apply / Ignore / Revert,
four breakdown panels) and the "agent memory" card of board 4.

The hard constraint is statistical honesty. One person generates tens to a few
hundred applications, outcomes are noisy and delayed, and the data is
observational. The design therefore gates every capability on evidence and
shows its own uncertainty.

## Goals / Non-Goals

**Goals:** advice that measurably improves with data; every claim traceable to
cases; the user in control of every behavioral change.

**Non-Goals:** external data; black-box models; automatic changes.

## Decisions

### L1. Outcomes and resolution

Primary outcome: the application reached the interview stage. Secondary: any
response from the employer. An application is *resolved* when it reached
interview or beyond, was closed, or has been in the applied stage longer than
the ghost threshold. Unresolved applications are excluded from rates
(otherwise recent applications look like failures). Applications tracked as
"already applied" count; postings never applied to do not.

### L2. Maturity levels

| Level | Condition | Enabled |
|---|---|---|
| 0 Collecting | fewer than 15 resolved | funnel and counts |
| 1 Descriptive | 15+ resolved | segment rates with intervals, lesson proposals |
| 2 Predictive | 40+ resolved, 8+ interviews, back-test passes (L5) | interview chance per posting; history score component |
| 3 Prescriptive | level 2 passed on two consecutive analyses at least 14 days apart | apply-next ranking, salary ask guidance, experiments |

The level is recomputed on every analysis and can go down. The panel shows the
level, what is needed for the next one, and never shows a capability above the
current level. Thresholds are constants in one module, chosen conservatively;
they are tunable later with real data.
*Alternative:* always show predictions (misleading with little data).

### L3. Descriptive statistics

For each segment (score band, title, channel, provider, resume kind, cover
letter, salary delta band, work mode, posting age at application): cases,
interviews, rate, and a credible interval from a Beta-Binomial model whose
prior is the user's overall rate with the weight of 4 pseudo-cases. Shrinking
toward the overall rate stops 1-of-1 segments from showing 100%. Segments with
fewer than 5 cases are shown greyed and never produce lessons.

### L4. Lessons

`jobtracker insights lessons` emits *candidates* mechanically: segments whose
interval is clearly above or below the overall rate, score-band monotonicity,
salary-delta effect, response-time distribution (for the ghost threshold).
`/analyze-results` has the agent read candidates and raw cases, discard
spurious ones (confounded or explained by a third factor it can see), word
them, attach the evidence, and store them as `proposed` rules. A lesson has an
area, a statement, evidence text with counts, and optionally a structured
effect from a fixed list:

- `min_score_shown` (search default filter)
- `title_priority` (lower/raise a title; move a title to under review)
- `ghost_days`, `followup_days`
- `salary_cap_pct` (maximum ask over the median)
- `resume_emphasis` (terms to foreground when supported by the base resume)
- `provider_priority`
- `weights` (new weights version)

Lessons without a structured effect are text the agent must follow. Apply,
Ignore, and Revert are user actions; each is an event. A reverted or ignored
lesson is not proposed again unless the evidence has materially changed.
*Alternative:* agent applies lessons automatically (violates user control).

### L5. Prediction model

Features (from the application snapshot, all binned): score band, each score
component band, title, channel, resume kind, cover letter, work mode, contract
type, posting age band, salary delta band. Model: L2-regularized logistic
regression fitted by gradient descent in pure Python, with recency weighting
(half-life 180 days) and all seasons included unless the user resets learning.

Validation: walk-forward, training on the first k resolved applications and
predicting the next block, repeated. The model passes when its Brier score
beats the base-rate predictor by a margin and the top-third of predictions
contains more interviews than the bottom third. Otherwise level 2 is not
granted (or is withdrawn) and the reason is shown.

Output per posting: a probability, shown as a rounded percentage with a range
and a plain-language label (low, medium, high) plus the two factors that moved
it most. The history component of the score (10 points) becomes a function of
this probability relative to the base rate; before level 2 it stays neutral.

*Alternatives:* naive Bayes on smoothed rates (simpler, poorly calibrated with
correlated features); scikit-learn (dependency); gradient boosting (overfits
at this size); agent-estimated probability (not reproducible).

### L6. Recommendations (level 3)

- **Apply next:** rank untouched tracked postings by interview chance, with
  posting age as a tie-breaker (earlier applications do better if the data
  says so).
- **Salary ask:** within the evidence range of the suggestion, the highest
  band whose historical progression rate is not clearly worse; never outside
  the evidence range and never a number without evidence.
- **Resume emphasis:** terms over-represented in postings that led to
  interviews and present in the base resume.
- **Timing:** follow-up day and ghost threshold from the response-time
  distribution.
- **Experiments:** when two options have overlapping intervals and both have
  cases (for example cover letter or not), propose alternating them over the
  next N similar applications; the experiment is tracked and concluded
  automatically when it reaches N or a clear difference.

Every recommendation states that it is based on correlation in the user's own
data, with counts, and is a suggestion.

### L7. Where learning takes effect

`jobtracker context` returns active rules and, at level 2+, the model summary.
Search reads `min_score_shown`, `title_priority`, `provider_priority`; scoring
reads `weights` and the history component; documents read `resume_emphasis`;
salary answers read `salary_cap_pct`; tracking reads `ghost_days` and
`followup_days`. Each produced item records which rules influenced it, so a
later analysis can check whether a rule helped and propose reverting it.

### L8. Analysis cadence

`/analyze-results` runs on request. The panel suggests it when 10 or more
applications have resolved since the last analysis. Insights numbers on the
Learning board are computed live; lessons and model refits happen only in an
analysis, so behavior does not shift silently.

## Risks / Trade-offs

- [Small samples produce confident-looking nonsense] → levels, shrinkage,
  minimum cases, intervals shown everywhere, back-test gate.
- [Confounding (referrals convert better whatever the resume)] → agent review
  of candidates, wording as correlation, experiments for causal questions.
- [Feedback loop: hiding low scores removes the evidence that they fail] → the
  minimum score filter hides, never deletes; the user can still track hidden
  postings; lessons record the data they were based on.
- [Market shifts make old data misleading] → recency weighting, seasons, and
  automatic withdrawal of the model when it stops validating.
- [User does not record outcomes] → insights show the share of unresolved
  applications and the ghost prompts from `add-application-tracking`.
