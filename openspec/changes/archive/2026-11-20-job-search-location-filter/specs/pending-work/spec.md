## ADDED Requirements

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
