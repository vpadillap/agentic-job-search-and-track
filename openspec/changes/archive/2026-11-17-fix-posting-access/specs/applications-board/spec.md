## MODIFIED Requirements

### Requirement: Table of all tracked applications
The board SHALL list every tracked application with its score, title, company
and conditions (including the work mode with its detail), status and tags,
document state, applied date and channel, salary asked next to salary
suggested, next step, and a link to the original posting on its source site.

#### Scenario: Score changed by a resume
- **WHEN** an application's score changed after the sent resume was uploaded
- **THEN** the row shows the current score and the change

#### Scenario: Work-mode detail shown
- **WHEN** a tracked posting is hybrid with the detail "Hybrid: 3 days on site"
- **THEN** its row shows the hybrid work mode together with that detail

#### Scenario: Opening the posting to apply
- **WHEN** the user activates the posting link of an application
- **THEN** the original posting opens in a new browser tab

### Requirement: Expandable detail
Each row SHALL expand to show the job description exactly as captured, with a
link to the original posting, the documents for the application, the form
questions with proposed answers when available, the user's application
details, and the history. The complete description SHALL be readable in the
page itself, without a box with its own scroll bar.

#### Scenario: Application without a form
- **WHEN** the posting had no visible form questions
- **THEN** the detail states that there is no form

#### Scenario: Reading the description of a tracked job
- **WHEN** the user expands an application and activates "Read the full description"
- **THEN** the complete verbatim description of its posting is shown in place
