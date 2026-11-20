## ADDED Requirements

### Requirement: Postings shown while the search runs
While a search is running, the board SHALL show each new posting as soon as
it is imported, without waiting for the run to finish. A new posting not yet
scored SHALL be marked "Scoring…" (localized) instead of a score, and SHALL
take its score and place in the table on the board's next refresh after it
is scored. A posting removed by the first-pass filter SHALL leave the table
and appear in the filtered-out list. The user SHALL be able to open, track,
or dismiss any shown posting while the search goes on.

#### Scenario: Imported but not scored
- **WHEN** a running search has imported a posting that has no score yet
- **THEN** the board lists it with "Scoring…" in the score column

#### Scenario: Scored during the search
- **WHEN** that posting is scored 82 while the search is still running
- **THEN** the board shows it with 82 on its next refresh, without the user reloading the page

#### Scenario: Tracking during the search
- **WHEN** the user tracks a scored posting while the search is still running
- **THEN** it is tracked as usual and the search goes on

#### Scenario: Search finished with an unscored posting
- **WHEN** a run is finished and one of its new postings has no score
- **THEN** the board shows a dash for it instead of "Scoring…"

## MODIFIED Requirements

### Requirement: Run summary
The board SHALL summarize the displayed search run: when it ran, the posting
age window, the number of titles searched, counts of found, new, filtered-out,
and duplicate postings, per-provider counts, and any provider that was skipped
with the reason. While the run is running, the summary SHALL also show its
progress: how many sites are done out of those being searched, how many new
postings are scored out of the new ones, and each site that is cooling down
with the time it resumes.

#### Scenario: Skipped provider
- **WHEN** a provider was skipped because it needs the user present
- **THEN** the summary names the provider and the reason

#### Scenario: Filtered-out postings
- **WHEN** the user opens the filtered-out list
- **THEN** each filtered-out posting is listed with the reason it was excluded

#### Scenario: Progress of a running search
- **WHEN** a running search has finished 2 of 4 sites, scored 18 of 30 new postings, and one site is cooling down until 15:40
- **THEN** the summary shows 2 of 4 sites done, 18 of 30 scored, and that site resuming at 15:40

### Requirement: Search, filter, and sort
The board SHALL filter rows as the user types across title, company, and
description, SHALL filter by work mode, contract type, minimum score, provider,
and presence of a salary suggestion, SHALL sort by any column, and SHALL state
how many rows are hidden by filters. While the search is running, the
minimum-score filter SHALL NOT hide postings still marked "Scoring…"; it
applies to them once they are scored.

#### Scenario: Type-ahead
- **WHEN** the user types part of a company name
- **THEN** only matching rows remain visible after each keystroke

#### Scenario: Hidden rows are disclosed
- **WHEN** a minimum-score filter hides five postings
- **THEN** the board states that five are hidden by that filter

#### Scenario: Minimum score during a running search
- **WHEN** a minimum score of 70 is set and a running search has a posting still being scored
- **THEN** that posting stays visible as "Scoring…" and is hidden only if it is then scored below 70
