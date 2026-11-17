## Purpose

Defines the panel tab that shows who the agent thinks the user is, what it
remembers, what it has pending, how to command it, and which job sites it uses.

## ADDED Requirements

### Requirement: Season summary
The board SHALL show the active season with its start date, the command to
start a new season, and access to earlier seasons.

#### Scenario: Earlier season exists
- **WHEN** an earlier season exists
- **THEN** the board offers a way to view it

### Requirement: Profile summary
The board SHALL show the active profile version, the base resume with a way to
open it, the target titles grouped by state, and the user's job needs.

#### Scenario: Title under review
- **WHEN** a title has been placed under review by an applied lesson
- **THEN** it is shown as under review

### Requirement: Acting on suggested titles
The user SHALL be able to include or exclude a title the agent suggested,
directly on the board.

#### Scenario: Including a suggestion
- **WHEN** the user includes a suggested title
- **THEN** it is shown as included and the next search uses it

### Requirement: Profile changes go through the agent
Apart from suggested titles, the board SHALL present the profile as read-only
and explain that it is changed by talking to the agent.

#### Scenario: Wanting to change work mode
- **WHEN** the user views job needs
- **THEN** the board indicates that changes are made in conversation with the agent

### Requirement: Pending work
The board SHALL list each item pending for the agent and the command that
processes them.

#### Scenario: Nothing pending
- **WHEN** no items are pending
- **THEN** the board states that nothing is pending

### Requirement: Command reference
The board SHALL list every available command with a one-line description in the
panel language, each copyable.

#### Scenario: Spanish panel with aliases
- **WHEN** the panel is in Spanish and Spanish commands are installed
- **THEN** the commands are listed by their Spanish names

### Requirement: Agent memory
The board SHALL list the rules the agent always respects with the origin of
each, read-only, and explain how to add or change one.

#### Scenario: Mixed origins
- **WHEN** there are system rules, a user preference, and an applied lesson
- **THEN** each is listed with its origin and date

### Requirement: Provider control
The board SHALL list each provider with its access method, last status, and
instruction file, and SHALL let the user enable or disable it.

#### Scenario: Provider needing presence
- **WHEN** a provider requires the user to be present
- **THEN** its status says so

#### Scenario: Disabling a provider
- **WHEN** the user switches a provider off
- **THEN** it is shown as disabled with the date and the next search skips it
