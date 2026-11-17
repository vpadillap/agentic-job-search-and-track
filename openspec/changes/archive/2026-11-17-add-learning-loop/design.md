## Context

Implements D11 and D12 of `define-foundation-architecture`. Visual reference:
board 3 of `design/panel-ux.html` (KPIs, lessons with Apply / Ignore / Revert,
four breakdown panels) and the "agent memory" card of board 4.

Two kinds of learning work together:

- **The agent's judgment** improves only through what it is given before it
  acts: the active rules, the numbers, and the cases. It gets every data point
  from the first one (L9). It is never retrained; it is better informed.
- **Statistical claims** (rates, an interview percentage, recommendations) are
  computed by code and shown only when the data supports them (L2). This gate
  limits what the system asserts as a number, never what the agent may read.

The hard constraint for the second kind is statistical honesty. One person
generates tens to a few hundred applications, outcomes are noisy and delayed,
and the data is observational.

Owner decisions (2026-11-17): learning is not part of searching; it runs
before scoring and before tailoring; the agent receives all the history, not a
selection.

## Goals / Non-Goals

**Goals:** advice that measurably improves with data; every claim traceable to
cases; the user in control of every behavioral change; no data point wasted.

**Non-Goals:** external data; black-box models; automatic changes; steering
the search.

## Decisions

### L1. Outcomes and resolution

Primary outcome: the application reached the interview stage. Secondary: any
response from the employer. An application is *resolved* when it reached
interview or beyond, was closed, or has been in the applied stage longer than
the ghost threshold. Unresolved applications are excluded from rates
(otherwise recent applications look like failures) but are still part of the
history the agent reads, marked as pending. Applications tracked as "already
applied" count; postings never applied to are not outcomes, but their
dismissals are learning input (L4).

### L2. Maturity levels (for statistical claims)

| Level | Condition | Enabled |
|---|---|---|
| 0 Collecting | fewer than 15 resolved | funnel and counts |
| 1 Descriptive | 15+ resolved | segment rates with intervals, lesson proposals from rates |
| 2 Predictive | 40+ resolved, 8+ interviews, back-test passes (L5) | interview chance per posting; history score component; rubric retraining |
| 3 Prescriptive | level 2 passed on two consecutive refreshes at least 14 days apart | apply-next ranking, salary ask guidance, experiments |

The level is recomputed on every refresh and can go down. The panel shows the
level, what is needed for the next one, and never shows a capability above the
current level. Thresholds are constants in one module, chosen conservatively;
they are tunable later with real data. At every level, including 0, the agent
reads the full history (L9).
*Alternative:* always show predictions (misleading with little data).

### L3. Descriptive statistics

For each segment (score band, title, channel, provider, resume kind, cover
letter, salary delta band, work mode, posting language, posting age at
application): cases, interviews, rate, and a credible interval from a
Beta-Binomial model whose prior is the user's overall rate with the weight of
4 pseudo-cases. Shrinking toward the overall rate stops 1-of-1 segments from
showing 100%. Segments with fewer than 5 cases are shown greyed and never
produce lessons.

Work mode is the posting's **current** value: a user's correction
(`work_mode_source = 'user'`) replaces the agent's reading for every
statistic. A posting that does not state its work mode is its own group,
"not stated".

### L4. Lessons

Candidates are emitted mechanically by the refresh (L8) from:

- **outcomes:** segments whose interval is clearly above or below the overall
  rate, score-band monotonicity, salary-delta effect, response-time
  distribution (for the ghost and follow-up thresholds);
- **dismissals:** the same reason given repeatedly for postings that share a
  trait (for example "location" for onsite postings outside the accepted
  areas, "industry" for one industry): a candidate to adjust the profile or a
  user rule for the first-pass filter;
- **corrections:** work-mode readings the user corrected, per provider: a text
  lesson for the search skill ("on this site the work mode is in the
  description, not the location line");
- **the validated model:** new score weights (L10).

The agent reads candidates and the full history, discards spurious ones
(confounded or explained by a third factor it can see), words them, attaches
the evidence, and stores them as `proposed` rules. A lesson has an area, a
statement, evidence text with counts, and optionally a structured effect from
a fixed list:

- `min_score_shown` (the panel's default score filter; search is unchanged)
- `title_state` (move a target title to under review or excluded in the
  profile, done when the user applies the lesson)
- `ghost_after_days`, `follow_up_after_days`
- `salary_cap_pct` (maximum ask over the median)
- `resume_emphasis` (terms to foreground when supported by the base resume)
- `weights` (new weights version)

Lessons without a structured effect are text the agent must follow. Apply,
Ignore, and Revert are user actions; each is an event. A reverted or ignored
lesson is not proposed again unless the evidence has materially changed (5 or
more new cases).
*Alternatives:* agent applies lessons automatically (violates user control);
lessons that reorder titles or job sites in the search (rejected by the owner:
learning is not part of searching).

### L5. Prediction model

Features (all binned): score band, each score component band, title, channel,
resume kind, cover letter, current work mode, contract type, posting language,
posting age band. The work-mode detail (free text) is never a feature. Model:
L2-regularized logistic regression fitted by gradient descent in pure Python,
with recency weighting (half-life 180 days) and all seasons included unless
the user resets learning.

Validation: walk-forward, training on the first k resolved applications and
predicting the next block, repeated. The model passes when its Brier score
beats the base-rate predictor by a margin and the top third of predictions
contains more interviews than the bottom third. Otherwise level 2 is not
granted (or is withdrawn) and the reason is shown.

Output per posting: a probability, shown as a rounded percentage with a range
and a plain-language label (low, medium, high) plus the two factors that moved
it most. The history component of the score (10 points) becomes a function of
this probability relative to the base rate; before level 2 it stays neutral.

*Alternatives:* naive Bayes on smoothed rates (simpler, poorly calibrated with
correlated features); scikit-learn (dependency); gradient boosting (overfits
at this size); agent-estimated probability (not reproducible).

### L5b. Fit to you

A second, independent estimate learned from the user's decisions on postings
shown in the Search board: tracked (positive) or dismissed (negative, with its
reason). Postings the user has not decided on are not used. Features are what
is known before the decision: title group, provider, current work mode,
contract type, language, score band and component bands, salary suggestion
relative to the profile's minimum, posting age band, flags. Same model and
walk-forward validation as L5 (recency-weighted logistic regression; must beat
the base rate of tracking and rank tracked postings higher).

Gate: 30 or more decisions with at least 8 tracked and 8 dismissed, and a
passing back-test. It does not depend on the maturity levels (L2): decisions
accumulate within weeks, outcomes within months.

Use: the Search board shows a fit label (low, medium, high) and lets the user
sort by it; the refresh gives the agent the fit estimate of each posting it
scores, which the agent may mention in the score note. It never changes the
interview estimate, the score total, or the search itself, and it is always
worded as "matches what you usually track", never as a chance of success
(a posting the user likes is not more likely to lead to an interview).

*Alternative:* fold the user's preference into the alignment score (mixes
"what the user likes" with "what works", which the learning loop must keep
apart to evaluate either).

### L6. Recommendations (level 3)

- **Apply next:** rank untouched tracked postings by interview chance, with
  posting age as a tie-breaker.
- **Salary ask:** within the evidence range of the suggestion, the highest
  band whose historical progression rate is not clearly worse; never outside
  the evidence range and never a number without evidence.
- **Resume emphasis:** terms over-represented in postings that led to
  interviews and present in the user's resumes; the others are gaps.
- **Timing:** follow-up day and ghost threshold from the response-time
  distribution.
- **Experiments:** when two options have overlapping intervals and both have
  cases (for example cover letter or not), propose alternating them over the
  next N similar applications; the experiment is tracked and concluded
  automatically when it reaches N or a clear difference.

Every recommendation states that it is based on correlation in the user's own
data, with counts, and is a suggestion.

### L7. Where learning takes effect

Never in searching. `jobtracker context` returns active rules, their effects,
and the level. Scoring reads `weights` and the history component and receives
the full history (L9); documents read `resume_emphasis`; salary answers read
`salary_cap_pct`; tracking reads `ghost_after_days` and
`follow_up_after_days`; the panel's Search board reads `min_score_shown` as
its default filter; `title_state` changes the profile when applied. Each
produced item records which rules influenced it, so a later refresh can check
whether a rule helped and propose reverting it.

### L8. Learning refresh

`jobtracker learning refresh [--posting <id>]` runs at two points, by the
skills:

1. `/job-search`, after the first-pass filter and before scoring;
2. `/prepare-documents`, before tailoring.

It is cheap and automatic:

- recomputes insights and the level;
- refits and revalidates the interview model only when 10 or more
  applications have resolved since the last fit (or none was fitted yet and
  level 2 counts are met), and the fit-to-you model only when 10 or more new
  decisions were made since its last fit, so refreshes are fast and behavior
  does not shift on every run;
- writes the full history (L9);
- returns the active rules and effects, the level, the history file, and new
  lesson candidates (L4), which the agent stores as `proposed`; they change
  nothing until the user applies them.

`/analyze-results` stays as an optional deeper review on request: the agent
studies the history and candidates for confounding, words lessons carefully,
reads work-mode details qualitatively, and proposes experiments. The panel
suggests it when 10 or more applications have resolved since the last one.

*Alternative:* analysis only on request (owner rejected: learning must be in
place whenever a posting is scored or a document is tailored).

### L9. Full history for the agent

Every refresh writes `learning/history.jsonl` in the private home (gitignored
like the rest of it) and returns its path. One line per record, nothing left
out:

- every application the user applied to: posting title, company, language,
  current work mode, contract type, score and components at application time,
  resume kind, cover letter, channel, asked and suggested salary, current
  status, dates, outcome so far (pending, response, interview, offer, closed),
  and its job id;
- every dismissed posting with its reason and note;
- every user correction of an agent reading (work mode, with before and
  after) per provider.

With `--posting <id>`, records are ordered by similarity to that posting
(same target title, shared skills, language, work mode) so the most relevant
come first; the order is a convenience, never a cut. The agent decides what is
relevant and cites the cases it relies on in its score note ("Similar: J0003
reached interview, J0007 rejected"). Statistical claims (rates, percentages)
still come only from the code (L3, L5).

*Alternative:* pass only the top few similar cases (owner rejected: every
data point is valuable; the agent decides).

### L10. Retraining the scoring rubric

When the validated model (L5) shows that score components predict interviews
differently from their current weights, the refresh emits a `weights`
candidate: new maximum points per judged component, proportional to each
component's predictive strength, bounded (each component between 5 and 45;
judged components sum to 90, history keeps 10), and only when some component
would change by 5 points or more. The evidence states each component's effect
with counts. Applying it creates a new weights version; past scores keep their
version, and open postings scored with an older version appear as pending
rescores.

### L11. Demo history

`jobtracker demo seed --learning collecting|descriptive|predictive|prescriptive`
adds a fictional history (applications, outcomes, dismissals, corrections,
analyses) that reaches the chosen level, so the Learning board can be tried
and tested. The fictional persona only; never mixed with real data. The demo
score note that lists a skill as both matched and missing is fixed.

## Risks / Trade-offs

- [Small samples produce confident-looking nonsense] → levels, shrinkage,
  minimum cases, intervals shown everywhere, back-test gate.
- [Confounding (referrals convert better whatever the resume)] → agent review
  of candidates, wording as correlation, experiments for causal questions.
- [The agent over-reads a few similar cases] → score notes cite the cases by
  id so the user can check them; numbers come only from the code.
- [Feedback loop: hiding low scores removes the evidence that they fail] → the
  minimum score filter hides, never deletes; the user can still track hidden
  postings; lessons record the data they were based on.
- [A refresh slows every scoring run] → insights are cheap; the models are
  refitted only after 10 new resolved outcomes or decisions.
- [The user reads fit as a promise] → it is labeled as fit to the user's own
  choices, shown apart from the interview estimate, and never changes the
  score.
- [History grows large] → one compact line per record; hundreds of lines are
  well within what the agent can read; it is a file, not context it must hold.
- [Market shifts make old data misleading] → recency weighting, seasons, and
  automatic withdrawal of the model when it stops validating.
- [User does not record outcomes] → insights show the share of unresolved
  applications and the ghost prompts from `add-application-tracking`.
