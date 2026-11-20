## ADDED Requirements

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
