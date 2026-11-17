# outcome-prediction Specification

## Purpose
Defines the estimate of how likely a posting is to lead to an interview for
this user, learned from the user's own past outcomes, and the conditions under
which that estimate may be shown.

## Requirements

### Requirement: Prediction only with sufficient, validated evidence
The system SHALL show an interview-chance estimate only when the user has at
least 40 resolved applications including at least 8 that reached interview,
and the estimate has been shown to outperform the user's overall rate on
applications it was not trained on.

#### Scenario: Not enough data
- **WHEN** the user has 20 resolved applications
- **THEN** no interview chance is shown anywhere and the panel states how many more outcomes are needed

#### Scenario: Validation fails
- **WHEN** there is enough data but the estimate does not outperform the overall rate in back-testing
- **THEN** no interview chance is shown and the panel explains that the predictions are not yet reliable

#### Scenario: Requirements met
- **WHEN** the data and validation requirements are met
- **THEN** each new and tracked posting shows an interview-chance estimate

### Requirement: Honest presentation
An estimate SHALL be presented with a range, a plain-language level, and the
factors that most influenced it, and SHALL be described as an estimate based on
the user's own history.

#### Scenario: Viewing an estimate
- **WHEN** the user opens a posting's detail while predictions are active
- **THEN** the estimate, its range, and its main factors are shown

### Requirement: Prediction quality is visible
The system SHALL show how well past estimates matched actual outcomes.

#### Scenario: Track record
- **WHEN** the user views the prediction section of the Learning tab
- **THEN** it shows, for groups of past estimates, the predicted and the actual interview rates

### Requirement: Fit to the user's choices
The system SHALL estimate how well a posting matches the postings the user
usually tracks, learned only from the user's track and dismiss decisions, and
SHALL show it only after at least 30 decisions with at least 8 tracked and 8
dismissed and a passing back-test. It SHALL be presented as fit to the user's
choices, separately from the interview estimate, and SHALL NOT change the
alignment score or the search.

#### Scenario: Enough decisions
- **WHEN** the user has tracked 12 and dismissed 25 postings and the fit estimate passes back-testing
- **THEN** new postings in the Search board show a fit label that can be sorted

#### Scenario: Too few decisions
- **WHEN** the user has made 20 decisions
- **THEN** no fit label is shown and the Learning tab states how many more decisions are needed

#### Scenario: Never a success claim
- **WHEN** a posting has a high fit and a low interview estimate
- **THEN** both are shown with their own labels and the score is unchanged by the fit

### Requirement: Refitting with new outcomes
The model SHALL be refitted and revalidated during a learning refresh once ten
or more applications have resolved since the last fit, and SHALL NOT use the
free-text work-mode detail as an input.

#### Scenario: Enough new outcomes
- **WHEN** a refresh finds twelve applications resolved since the last fit
- **THEN** the model is refitted and validated before new estimates are shown

### Requirement: Withdrawal when unreliable
The system SHALL stop showing estimates when a later analysis finds they no
longer outperform the overall rate.

#### Scenario: Model degrades
- **WHEN** an analysis finds the estimates no longer pass validation
- **THEN** estimates are removed from the panel and the reason is stated

### Requirement: History feeds the score
While predictions are active the history component of the alignment score SHALL
reflect the estimate, and SHALL be neutral otherwise.

#### Scenario: Before predictions are active
- **WHEN** predictions are not active
- **THEN** every posting receives the same neutral history points

### Requirement: Only the user's own data
Estimates SHALL be derived solely from the user's recorded applications and
outcomes.

#### Scenario: Reset of learning
- **WHEN** the user asks to reset learning
- **THEN** estimates are withdrawn until the requirements are met again with new outcomes
