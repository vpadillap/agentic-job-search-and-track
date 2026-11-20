# search-results-board Specification

## Purpose
Defines how the user reviews the postings found by the latest search, sees why
each was scored and priced as it was, and decides what to track or dismiss.

## Requirements

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

### Requirement: Results table
The board SHALL list each new posting with its alignment score, title, company,
conditions (contract type, work mode with its detail, and location), suggested
monthly salary, publication date, and a link to the original posting on its
source site. The user SHALL be able to set or correct a posting's work mode and
its detail from its row; the change SHALL be saved immediately, kept when later
searches find the posting again, and shown as set by the user.

#### Scenario: Posting without reliable salary data
- **WHEN** a posting has no stored salary suggestion
- **THEN** the salary cell states that there is no reliable data and shows no amount

#### Scenario: Opening the original posting
- **WHEN** the user activates the source link
- **THEN** the original posting opens in a new browser tab

#### Scenario: Work-mode detail shown
- **WHEN** a posting is hybrid with the detail "2 días presencial por semana"
- **THEN** its conditions cell shows the hybrid work mode together with that detail

#### Scenario: User fills in a missing work mode
- **WHEN** a posting has no work mode and the user sets it to remote with the detail "Early Friday" from its row
- **THEN** the row shows remote with that detail, marked as set by the user, and it persists after reload

#### Scenario: User edit survives a later search
- **WHEN** the user corrected a posting's work mode and a later search finds the same posting
- **THEN** the posting keeps the user's work mode and detail

### Requirement: Possible duplicates are visible
Each posting SHALL remain its own row, and a posting that may be the same job
as another posting of the displayed run or a tracked posting SHALL show a
possible-duplicate mark naming the other postings and their sites.

#### Scenario: Same job on two sites
- **WHEN** the run contains the same company and title from two sites, published within 7 days of each other
- **THEN** both rows are shown, each with a possible-duplicate mark naming the other site

#### Scenario: Already tracked elsewhere
- **WHEN** a new posting matches the company and title of a tracked posting from another site
- **THEN** its row shows a possible-duplicate mark that names the tracked job

### Requirement: Expandable detail
Each row SHALL expand to show the job description exactly as captured, the
score breakdown by component with a note for each, and the salary suggestion
with its range, confidence, comparison criteria, and linked evidence. The
complete description SHALL be readable in the page itself, without a box with
its own scroll bar: a long description shows its beginning with a control
that reveals the rest in place.

#### Scenario: Expanding a row
- **WHEN** the user expands a posting
- **THEN** the verbatim description, the per-component score, and each salary evidence source are visible

#### Scenario: Reading a long description
- **WHEN** a posting's description is longer than the visible beginning and the user activates "Read the full description"
- **THEN** the whole description is shown in place, with no inner scroll bar, and "Show less" returns to the beginning

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
The board SHALL show the latest group of runs by default, with every posting
of the group's runs once and a summary that adds up its runs, and SHALL let
the user open an earlier group.

#### Scenario: Viewing a previous run
- **WHEN** the user selects an earlier group of runs
- **THEN** the summary and table show that group's runs and postings

#### Scenario: Two searches on the same day
- **WHEN** two runs were made on the same day
- **THEN** the board shows them on one page, with their postings once and their counts added up

### Requirement: The results table fits the screen
The results table SHALL show every column without horizontal scrolling at
widths of 1,280 pixels and more, SHALL keep each row's actions reachable in
one click, and on narrower widths SHALL move secondary columns into the row's
detail, showing each row as a card at phone width.

#### Scenario: Laptop screen
- **WHEN** the Search tab is shown at 1,366 pixels wide
- **THEN** the page does not scroll sideways and the salary, date, and actions of every row are visible

#### Scenario: Phone width
- **WHEN** the Search tab is shown at phone width
- **THEN** each posting is a card with its title, company, score, salary, and actions, and the other fields are in its detail

### Requirement: Salary column with the agent's suggestion
The salary cell SHALL show the offered salary when the posting has one and the
suggested range with the count of sources by kind; the agent's note SHALL be
shown in the salary detail and as the cell's tooltip. The detail SHALL list
every input used with its link or reference, the reports set aside and why,
and the dates. When there is no suggestion, it SHALL say that there is no
salary data and what was checked.

#### Scenario: Offered and suggested
- **WHEN** a posting offers a range and the agent suggested a range from one company reference and two offers from the user's history
- **THEN** the cell shows both ranges with "1 company, 2 your history", and the detail shows the note and each input

#### Scenario: No suggestion
- **WHEN** a posting offers no salary and the agent found no source
- **THEN** the cell says there is no salary data and the detail lists what was checked

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

### Requirement: Restore a filtered-out posting
Each posting in the filtered-out list SHALL have a "Restore" action. A
restored posting SHALL leave the filtered-out list and return to the results
as a new posting without a score, SHALL never be filtered out again, and the
board SHALL say that it will be scored by the command that completes the
pending work. Filtered-out postings SHALL NOT be scored, priced, or prepared
while they stay filtered out.

#### Scenario: Restoring a posting
- **WHEN** the user restores a posting filtered out for "location"
- **THEN** it leaves the filtered-out list, appears in the results without a score, and a message says it will be scored with the pending work

#### Scenario: Restoring during a running search
- **WHEN** the user restores a posting while its search is still running
- **THEN** it appears in the results as "Scoring…" and the search scores it before it finishes

#### Scenario: Filtered-out postings cost nothing
- **WHEN** a search filters out ten postings
- **THEN** none of the ten receives a score or a salary suggestion

### Requirement: Each site's latest result on a page
On a page that holds several searches, each site SHALL be shown with the
result of the latest search on that page that tried it (searched, failed, or
skipped for a reason other than not being searched), and with the time it was
last searched successfully on that page. Its found count SHALL be the sum over
the page's searches.

#### Scenario: Failure then success the same day
- **WHEN** Bumeran failed for a missing tool in the morning search and was read fine in the afternoon search of the same page
- **THEN** the page shows Bumeran as searched with the afternoon's time and no failure

#### Scenario: Success then failure the same day
- **WHEN** Bumeran was read fine in the morning and failed in the afternoon search of the same page
- **THEN** the page shows the afternoon failure with its reason and the morning as the last successful search

#### Scenario: Site not searched later
- **WHEN** the afternoon search covered only LinkedIn, and Bumeran was read fine in the morning
- **THEN** the page still shows Bumeran as searched in the morning
