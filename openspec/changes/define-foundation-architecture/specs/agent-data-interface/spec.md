## Purpose

Defines the command-line contract through which AI agents inspect the
environment and read or write structured job-search data, so that every change
is validated in one place and agents never edit stored data directly.

## ADDED Requirements

### Requirement: Machine-readable command output
Every command of the agent interface SHALL be able to emit its result as JSON
on standard output, SHALL write diagnostics to standard error, and SHALL exit
with a non-zero status when it fails.

#### Scenario: Successful command
- **WHEN** an agent runs a command with JSON output requested
- **THEN** standard output is a single valid JSON document and the exit status is zero

#### Scenario: Failed command
- **WHEN** a command fails validation
- **THEN** the exit status is non-zero and the JSON output contains an error code and a human-readable message

### Requirement: Environment diagnostics
The interface SHALL provide a diagnostics command that reports, without
changing anything, the Python version, whether required packages are
installed, whether the workspace is initialized, the database schema version,
and the availability of optional tools required by enabled providers.

#### Scenario: Fresh clone
- **WHEN** diagnostics are run before any setup
- **THEN** the report lists the workspace as not initialized and names each missing requirement with the action needed to fix it

#### Scenario: Healthy installation
- **WHEN** diagnostics are run on an initialized, up-to-date workspace
- **THEN** every check is reported as passing

### Requirement: Schema migrations with backup
The interface SHALL bring the database to the current schema version
automatically before any command that uses it, and SHALL create a backup copy
of an existing database before applying a migration.

#### Scenario: Older database
- **WHEN** a command runs against a database with an older schema version
- **THEN** a backup copy exists in the backups folder and the database is at the current version before the command executes

#### Scenario: Newer database
- **WHEN** a command runs against a database whose schema version is newer than the installed code supports
- **THEN** the command fails without modifying the database and asks the user to update the code

### Requirement: Agent context bundle
The interface SHALL provide a single command that returns everything an agent
must know before acting: panel language, active season and profile, active
rules, pending work items, and provider state.

#### Scenario: Context before setup
- **WHEN** the context command runs on an uninitialized workspace
- **THEN** it reports that setup is required and returns no profile

#### Scenario: Context on an initialized workspace
- **WHEN** the context command runs after setup
- **THEN** the output includes the panel language and the list of active rules, including the system rules shipped with the project

### Requirement: Validated writes only
The interface SHALL validate every write against the domain rules and reject
invalid input without partially applying it.

#### Scenario: Invalid input is rejected atomically
- **WHEN** a batch write contains one invalid record
- **THEN** no record from the batch is stored and the error identifies the invalid record

### Requirement: Safe concurrent use with the panel
The interface SHALL operate correctly while the local panel is running and
reading or writing the same data.

#### Scenario: Write while the panel is open
- **WHEN** a command writes data while the panel server is running
- **THEN** the write succeeds and the panel shows the new data on its next refresh
