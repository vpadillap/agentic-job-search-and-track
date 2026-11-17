## MODIFIED Requirements

### Requirement: Table of all tracked applications
The board SHALL list every tracked application with its score, title, company
and conditions (including the work mode with its detail), status and tags,
document state, applied date and channel, salary asked next to salary
suggested, and next step.

#### Scenario: Score changed by a resume
- **WHEN** an application's score changed after the sent resume was uploaded
- **THEN** the row shows the current score and the change

#### Scenario: Work-mode detail shown
- **WHEN** a tracked posting is hybrid with the detail "Hybrid: 3 days on site"
- **THEN** its row shows the hybrid work mode together with that detail

### Requirement: Inline editing
The user SHALL be able to change status, tags, application details, and the
posting's work mode and its detail directly in the board without leaving it,
and each change SHALL be saved immediately.

#### Scenario: Inline status change
- **WHEN** the user picks a new status in a row
- **THEN** the row shows the new status and it persists after reload

#### Scenario: Inline work-mode correction
- **WHEN** the user changes a tracked posting's work mode from onsite to hybrid with the detail "Fridays from home"
- **THEN** the row shows hybrid with that detail, the same value appears in the Search tab, and the change is in the application's history
