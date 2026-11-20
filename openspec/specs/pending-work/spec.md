# pending-work Specification

## Purpose
Defines the list of items waiting for the agent and the single instruction that
completes all of them, so the user never has to track what is missing.

## Requirements

### Requirement: Pending work is derived from the data
The system SHALL determine pending items from the current data: tracked
applications not yet applied to that lack a tailored resume, a required cover
letter, or form answers, and applications needing a rescore.

#### Scenario: Newly tracked posting
- **WHEN** the user tracks a posting that has form questions
- **THEN** the pending work lists a missing resume and missing form answers for it

#### Scenario: Already applied
- **WHEN** an application was tracked as already applied
- **THEN** it is not listed as needing documents

### Requirement: Pending work is visible in the panel
The panel SHALL show the number of pending items, what each one is, and the
command that processes them.

#### Scenario: Three pending items
- **WHEN** three items are pending
- **THEN** the header shows three and the list names each item with its application

### Requirement: One instruction completes everything pending
A single batch instruction SHALL produce all missing resumes, cover letters,
and form answers and perform pending rescoring.

#### Scenario: Batch after tracking
- **WHEN** the user runs the batch instruction after tracking five postings
- **THEN** all five have their documents and answers and the pending count is zero

### Requirement: Batch is resilient and reported
The batch SHALL continue when one item fails and SHALL report, per application,
what was produced, what was skipped, and what needs the user.

#### Scenario: One failure
- **WHEN** one application's resume cannot be produced
- **THEN** the other applications are completed and the report names the failed one with the reason

### Requirement: Selective preparation
The user SHALL be able to request preparation for specific applications by
their identifiers.

#### Scenario: Two identifiers
- **WHEN** the user requests documents for two given applications
- **THEN** only those two are processed

### Requirement: Restored postings wait for a score
A posting the user restored from the filtered-out list that has no score yet,
on the latest search page and not in a search still running, SHALL be a
pending item of kind "score". The command that completes everything pending
SHALL score it, without filtering it again.

#### Scenario: Restored after the search
- **WHEN** the user restores a posting from a finished search
- **THEN** the pending work lists it as a score to calculate, and running the pending command gives it a score and removes the item

#### Scenario: Restored during a running search
- **WHEN** the user restores a posting while its search is still running
- **THEN** it is not a pending item, because the running search scores it
