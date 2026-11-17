## ADDED Requirements

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

## MODIFIED Requirements

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
