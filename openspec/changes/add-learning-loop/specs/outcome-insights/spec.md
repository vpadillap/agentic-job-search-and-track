## Purpose

Defines the descriptive statistics of the user's own results, which show what
is working and form the evidence for every lesson and prediction.

## ADDED Requirements

### Requirement: Headline indicators
The system SHALL report, for a chosen period, the response rate, the rate of
applications reaching interview, the number of offers, the ghosting rate, and
the median days to first response, each with the counts behind it.

#### Scenario: Indicators with counts
- **WHEN** insights are requested for a period with 41 resolved applications of which 7 reached interview
- **THEN** the interview indicator shows 17% and states 7 of 41

### Requirement: Only resolved applications count
Rates SHALL be computed over applications whose outcome is known or that have
waited longer than the no-response threshold, and the number of unresolved
applications SHALL be reported separately.

#### Scenario: Recent application
- **WHEN** an application was submitted two days ago and has no response
- **THEN** it is not counted in any rate and is included in the unresolved count

### Requirement: Breakdowns
The system SHALL report the interview rate by score range at the time of
applying, by target title, by channel, by kind of resume used, and by the
difference between salary asked and salary suggested, with the number of cases
in each group.

#### Scenario: Score ranges
- **WHEN** breakdown by score is requested
- **THEN** each score range shows its rate and its number of cases, using the score recorded when the user applied

### Requirement: Uncertainty is shown
Every rate SHALL be accompanied by its number of cases and a range expressing
its uncertainty, and groups with fewer than five cases SHALL be marked as
insufficient.

#### Scenario: Small group
- **WHEN** a channel has three applications
- **THEN** its rate is marked as based on too few cases

### Requirement: Period selection
The user SHALL be able to view insights for the last 30 days, the last 90 days,
the current season, or all history.

#### Scenario: Current season
- **WHEN** the current season is selected
- **THEN** only applications from that season are counted

### Requirement: Reproducible numbers
Insight figures SHALL be computed by the system from stored data and SHALL be
identical for the agent and the panel.

#### Scenario: Agent and panel agree
- **WHEN** the agent reports the interview rate for a period
- **THEN** the panel shows the same value for that period
