## MODIFIED Requirements

### Requirement: Table of all tracked applications
The board SHALL list every tracked application with its score, title, company
and conditions (including the work mode with its detail), status and tags,
document state, applied date and channel, salary asked next to salary
suggested and, when recorded, salary offered, next step, and a link to the
original posting on its source site.

#### Scenario: Score changed by a resume
- **WHEN** an application's score changed after the sent resume was uploaded
- **THEN** the row shows the current score and the change

#### Scenario: Work-mode detail shown
- **WHEN** a tracked posting is hybrid with the detail "Hybrid: 3 days on site"
- **THEN** its row shows the hybrid work mode together with that detail

#### Scenario: Opening the posting to apply
- **WHEN** the user activates the posting link of an application
- **THEN** the original posting opens in a new browser tab

#### Scenario: Offered salary shown
- **WHEN** an application has an offered salary of 14,000 PEN and an asked salary of 15,000 PEN
- **THEN** its row shows the offered salary under the asked and suggested salaries
