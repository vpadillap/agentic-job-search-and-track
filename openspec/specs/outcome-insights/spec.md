# outcome-insights Specification

## Purpose
Defines the descriptive statistics of the user's own results, which show what
is working and form the evidence for every lesson and prediction.

## Requirements

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
applying, by target title, by channel, by kind of resume used, by posting
language, by work mode, and by the difference between salary asked and salary
suggested, with the number of cases in each group.

#### Scenario: Score ranges
- **WHEN** breakdown by score is requested
- **THEN** each score range shows its rate and its number of cases, using the score recorded when the user applied

#### Scenario: Corrected work mode
- **WHEN** the user corrected a posting's work mode after applying
- **THEN** the breakdown by work mode counts the application under the corrected value

#### Scenario: Work mode not stated
- **WHEN** a posting does not state its work mode
- **THEN** it is counted in a "not stated" group

### Requirement: Full history for the agent
Whenever learning is refreshed, the system SHALL give the agent every
application the user applied to with its outcome so far, every dismissed
posting with its reason, and every correction the user made to an agent
reading, without leaving any out, stored only inside the private home. Each
application SHALL carry its current status by full name in the panel
language, whether it ended, its whole path of statuses by full name with
their dates, and its asked, suggested, and offered salaries.

#### Scenario: First outcomes
- **WHEN** the user has applied to three postings and one reached interview
- **THEN** the history given to the agent contains all three with their outcomes

#### Scenario: Ordered for a posting
- **WHEN** learning is refreshed for a specific posting
- **THEN** the history lists the most similar past applications first and still contains every record

#### Scenario: Pending outcomes
- **WHEN** an application has no outcome yet
- **THEN** it is in the history marked as pending and is not counted in any rate

#### Scenario: Status path by name
- **WHEN** an application went from Applied to the custom status "Technical test sent" and then to Rejected, with a Spanish panel
- **THEN** its history record names the current status "Rechazado", says it ended, and lists the path "Postulado", "Technical test sent", "Rechazado" with each date

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

### Requirement: Offered salaries
An application with a recorded offered salary SHALL count as having reached
an offer. Insights SHALL report, for the chosen period, how many offers have
a recorded amount and the median difference between the offered and the asked
salary and between the offered and the suggested salary, each with its number
of cases, comparing only amounts in the same currency.

#### Scenario: Offer recorded with a custom status
- **WHEN** an application with the custom status "Proposal received" has an offered salary
- **THEN** it counts as an offer in the indicators and in the agent's history

#### Scenario: Offered against asked
- **WHEN** three offers in the period have offered and asked salaries in the same currency, 5% below, 10% below, and equal to what was asked
- **THEN** insights report the median offered-versus-asked difference as -5% over 3 cases

### Requirement: Restored postings in the history
The history given to the agent SHALL include every posting the user restored
from the filtered-out list, as a correction of the filter, with the reason and
detail it had been filtered out for, the site, and the date of the restore.

#### Scenario: Restore recorded
- **WHEN** the user restores a posting filtered out for "location" with the detail "Onsite in Arequipa"
- **THEN** the next history given to the agent lists it as a filter correction with that reason and detail
