## ADDED Requirements

### Requirement: Salary sources are always available
Salary sources SHALL NOT be switched on or off: a salary-only source SHALL be
refused by the switch, and the salary pages of a job site that is also a
salary source SHALL be usable whether or not its job search is on. For each
posting the system SHALL tell the agent which salary sources serve the
posting's country, whether their tools are ready, and what each already
answered for the posting's keys; the agent SHALL ask the ones that fit.

#### Scenario: A user who never turned anything on
- **WHEN** the agent researches the salary of a posting in a country two salary sources serve
- **THEN** both are listed for that posting and the agent may ask them, without any switch

#### Scenario: Trying to switch a salary source
- **WHEN** the user or the agent tries to turn a salary-only source off
- **THEN** it is refused with a message saying salary sources are always used

#### Scenario: A job site whose search is off
- **WHEN** a job site that is also a salary source has its job search turned off
- **THEN** its salary pages are still listed and usable for salary research
