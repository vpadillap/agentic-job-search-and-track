## Purpose

Lets Spanish-speaking users invoke the agent's commands by Spanish names while
keeping one canonical English definition of each command.

## ADDED Requirements

### Requirement: Spanish aliases delegate to canonical skills
For every user-facing skill the project SHALL provide a Spanish alias that
performs exactly the canonical skill's procedure and accepts Spanish argument
names.

#### Scenario: Running an alias
- **WHEN** a user runs `/buscar-empleos dias=3`
- **THEN** the job search procedure runs with a posting age of 3 days

### Requirement: Aliases are installed only for the chosen language
The system SHALL install aliases when the panel language is Spanish, SHALL
remove them when it is English, and SHALL NOT leave installed aliases as
changes in version control.

#### Scenario: Spanish user
- **WHEN** alias synchronization runs with Spanish as the panel language
- **THEN** the six Spanish commands are available and version control reports no changes

#### Scenario: Switching to English
- **WHEN** alias synchronization runs after the language is changed to English
- **THEN** the Spanish commands are no longer installed

### Requirement: Commands are displayed in the panel language
The panel SHALL display command names that work in the user's installation:
Spanish aliases when they are installed and the panel is in Spanish, canonical
names otherwise.

#### Scenario: Spanish panel without aliases
- **WHEN** the panel is in Spanish but aliases are not installed
- **THEN** the panel shows the canonical English command names
