## Purpose

Defines the panel tab where the user sees what is working, what the agent has
learned, and how far the system's advice can currently be trusted.

## ADDED Requirements

### Requirement: Maturity level is always visible
The board SHALL show the current learning level (collecting, descriptive,
predictive, or prescriptive), what it enables, and what is needed to reach the
next level.

#### Scenario: Early use
- **WHEN** the user has eight resolved applications
- **THEN** the board shows the collecting level and how many more outcomes unlock descriptive insights

### Requirement: Indicators and breakdowns
The board SHALL show the headline indicators and the breakdowns by score,
resume kind, channel, and salary difference, with a period selector.

#### Scenario: Changing the period
- **WHEN** the user selects the last 90 days
- **THEN** all indicators and breakdowns reflect that period

### Requirement: Lessons with actions
The board SHALL list proposed lessons with their evidence and Apply and Ignore
actions, and applied lessons with the date applied and a Revert action.

#### Scenario: Applying from the board
- **WHEN** the user chooses Apply on a proposed lesson
- **THEN** it is shown as applied with today's date

### Requirement: Nothing above the current level is shown
The board SHALL NOT display predictions or recommendations that the current
level does not permit.

#### Scenario: Descriptive level
- **WHEN** the current level is descriptive
- **THEN** no interview-chance estimates or apply-next ranking are displayed

### Requirement: Prompt to analyze
The board SHALL show when the last analysis was made, SHALL suggest a new one
when enough new outcomes have accumulated, and SHALL show the command to run
it.

#### Scenario: New outcomes since the last analysis
- **WHEN** ten applications have resolved since the last analysis
- **THEN** the board suggests running the analysis and shows the command

### Requirement: Empty state
With no applications the board SHALL explain what will appear and what the user
needs to do.

#### Scenario: No data
- **WHEN** there are no tracked applications
- **THEN** the board explains that insights appear as outcomes are recorded
