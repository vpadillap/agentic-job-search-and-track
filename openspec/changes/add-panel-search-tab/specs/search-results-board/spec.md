## Purpose

Defines how the user reviews the postings found by the latest search, sees why
each was scored and priced as it was, and decides what to track or dismiss.

## ADDED Requirements

### Requirement: Run summary
The board SHALL summarize the displayed search run: when it ran, the posting
age window, the number of titles searched, counts of found, new, filtered-out,
and duplicate postings, per-provider counts, and any provider that was skipped
with the reason.

#### Scenario: Skipped provider
- **WHEN** a provider was skipped because it needs the user present
- **THEN** the summary names the provider and the reason

#### Scenario: Filtered-out postings
- **WHEN** the user opens the filtered-out list
- **THEN** each filtered-out posting is listed with the reason it was excluded

### Requirement: Results table
The board SHALL list each new posting with its alignment score, title, company,
conditions (contract type, work mode, and location), suggested monthly salary,
publication date, and a link to the original posting on its source site.

#### Scenario: Posting without reliable salary data
- **WHEN** a posting has no stored salary suggestion
- **THEN** the salary cell states that there is no reliable data and shows no amount

#### Scenario: Opening the original posting
- **WHEN** the user activates the source link
- **THEN** the original posting opens in a new browser tab

### Requirement: Expandable detail
Each row SHALL expand to show the job description exactly as captured, the
score breakdown by component with a note for each, and the salary suggestion
with its range, confidence, comparison criteria, and linked evidence.

#### Scenario: Expanding a row
- **WHEN** the user expands a posting
- **THEN** the verbatim description, the per-component score, and each salary evidence source are visible

### Requirement: Search, filter, and sort
The board SHALL filter rows as the user types across title, company, and
description, SHALL filter by work mode, contract type, minimum score, provider,
and presence of a salary suggestion, SHALL sort by any column, and SHALL state
how many rows are hidden by filters.

#### Scenario: Type-ahead
- **WHEN** the user types part of a company name
- **THEN** only matching rows remain visible after each keystroke

#### Scenario: Hidden rows are disclosed
- **WHEN** a minimum-score filter hides five postings
- **THEN** the board states that five are hidden by that filter

### Requirement: Track actions
Each row SHALL offer "Track" and "Track and mark applied", individually and for
a selection of rows. Tracked postings SHALL be marked as tracked and link to
the Applications tab.

#### Scenario: Track
- **WHEN** the user tracks a posting
- **THEN** it appears in tracked applications with the initial status and the row shows it is tracked

#### Scenario: Track and mark applied
- **WHEN** the user chooses "Track and mark applied"
- **THEN** the application is created with status Applied and today's date as the applied date

#### Scenario: Bulk track
- **WHEN** the user selects two rows and chooses Track
- **THEN** both postings become tracked

### Requirement: Dismiss with reason
Each row SHALL offer dismissal that records a reason, and dismissed postings
SHALL leave the default view and not be proposed again.

#### Scenario: Dismissing for location
- **WHEN** the user dismisses a posting with the reason "location"
- **THEN** the posting is hidden, the reason is stored, and a later search does not list it as new

### Requirement: Earlier runs
The board SHALL show the latest run by default and SHALL let the user open an
earlier run.

#### Scenario: Viewing a previous run
- **WHEN** the user selects an earlier run
- **THEN** the summary and table show that run's postings
