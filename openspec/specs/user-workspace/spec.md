# user-workspace Specification

## Purpose
Defines the private home directory where all of a user's personal job-search
data is stored, how it is laid out and named, and the safeguards that keep that
data out of the shared repository.

## Requirements

### Requirement: Single private home directory
The system SHALL store all personal data under one private home directory,
which is `user-data/` at the repository root by default and the path given by
the `JOBTRACKER_HOME` environment variable when it is set. The system SHALL
NOT write personal data to any location outside the private home.

#### Scenario: Default location
- **WHEN** `JOBTRACKER_HOME` is not set and the workspace is initialized
- **THEN** the private home is created at `user-data/` in the repository root

#### Scenario: Overridden location
- **WHEN** `JOBTRACKER_HOME` points to another directory and the workspace is initialized
- **THEN** all data is created under that directory and nothing is created under `user-data/`

### Requirement: Fixed layout and naming
The system SHALL create and use the directory layout and file naming rules
documented in `docs/workspace-layout.md`, and SHALL report the resolved
location of every well-known path on request so that agents never construct
paths themselves.

#### Scenario: Initialization creates the documented structure
- **WHEN** the workspace is initialized in an empty private home
- **THEN** the configuration file, the database, and the `profile`, `applications`, `searches`, `exports`, `backups`, and `archive` directories exist

#### Scenario: Initialization is repeatable
- **WHEN** the workspace is initialized again on an existing private home
- **THEN** no existing file is modified or removed and the command reports that the workspace already exists

#### Scenario: Application folder naming
- **WHEN** a folder is requested for job `J0007` at a company named "Altamar Retail S.A."
- **THEN** the folder path returned is `applications/J0007-altamar-retail-s-a` under the private home

### Requirement: Versioned documents are never overwritten
The system SHALL store each new version of an agent-proposed document under a
new version number and SHALL NOT overwrite or renumber earlier versions.

#### Scenario: Second proposed resume
- **WHEN** a proposed resume is registered for a job that already has `resume-proposed-v1`
- **THEN** the new file is stored as `resume-proposed-v2` and version 1 remains unchanged

### Requirement: Private data is excluded from version control
The repository SHALL ignore the private home directory, and a privacy guard
SHALL reject any commit that contains a file inside a private home directory,
a resume-type or database-type file outside the test fixtures folder, or
content matching the user's registered private terms.

#### Scenario: Staged file inside the private home
- **WHEN** a file under `user-data/` is force-added and a commit is attempted with the guard enabled
- **THEN** the commit is rejected with a message naming the file

#### Scenario: Resume document outside fixtures
- **WHEN** a `.pdf` or `.docx` file outside `tests/fixtures/` is staged
- **THEN** the guard rejects the commit

#### Scenario: Private term in a source file
- **WHEN** a staged text file contains a term listed in the private terms file
- **THEN** the guard rejects the commit and its message does not reveal the term

#### Scenario: Clean commit
- **WHEN** only source files without private terms are staged
- **THEN** the guard allows the commit

### Requirement: Nothing is deleted on reset
The system SHALL move an existing private home aside into its archive location
when a full reset is requested, and SHALL NOT delete user data.

#### Scenario: Full reset
- **WHEN** a full reset is requested on a private home that contains data
- **THEN** the previous contents are available under a dated archive folder and a fresh empty workspace is initialized

### Requirement: The privacy guard finds a working Python
The privacy guard SHALL run with the project's own Python when the project's
environment exists, and otherwise with any Python that really runs; a stub
that does not run Python SHALL NOT be used. When no working Python is found,
the guard SHALL block the commit with a message that says how to fix it.

#### Scenario: Windows without Python on the PATH
- **WHEN** a commit is made on Windows, the project's environment exists, and `python` on the PATH is the Store alias
- **THEN** the guard runs with the project's environment and checks the commit

#### Scenario: No Python at all
- **WHEN** a commit is made and no working Python is found
- **THEN** the commit is blocked with a message saying how to get Python or run setup
