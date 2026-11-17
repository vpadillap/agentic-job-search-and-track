# applications-board Specification

## Purpose
Defines the panel tab where the user sees every tracked application, finds any
of them instantly, and updates what happened.

## Requirements

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

### Requirement: Real-time search, filtering, and sorting
The board SHALL filter as the user types across title, company, notes, and
tags, SHALL filter by status, tag, document state, and applied date, and SHALL
sort by any column; sorting by status SHALL follow the order of the status
list.

#### Scenario: Type-ahead
- **WHEN** the user types "data"
- **THEN** after each keystroke only applications matching the text remain

#### Scenario: Funnel as filter
- **WHEN** the user selects the "Technical test sent" count card
- **THEN** only applications with that status are listed

#### Scenario: Sorting by status
- **WHEN** the user sorts by status
- **THEN** applications are ordered as their statuses appear in the status list

### Requirement: Inline editing
The user SHALL be able to change status, tags, application details, and the
posting's work mode and its detail directly in the board without leaving it,
and each change SHALL be saved immediately. The status SHALL be changed from
the status shown in the row, and tags from their own control.

#### Scenario: Inline status change
- **WHEN** the user picks a new status in a row
- **THEN** the row shows the new status and it persists after reload

#### Scenario: Status opens from the status itself
- **WHEN** the user activates the status shown in a row
- **THEN** the list of statuses opens with the current one selected, including the option to create a new status

#### Scenario: Tags have their own control
- **WHEN** the user activates the add-tag control in a row
- **THEN** only the tag form opens, without the status list

#### Scenario: Inline work-mode correction
- **WHEN** the user changes a tracked posting's work mode from onsite to hybrid with the detail "Fridays from home"
- **THEN** the row shows hybrid with that detail, the same value appears in the Search tab, and the change is in the application's history

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

### Requirement: Attention summary
The board SHALL summarize applications that need something: missing tailored
resume, unanswered form questions, no response past the threshold, and
follow-ups due, each as a filter, together with the command that hands the
pending work to the agent.

#### Scenario: Missing documents
- **WHEN** four tracked applications have no tailored resume
- **THEN** the summary shows four and selecting it lists those applications

### Requirement: Document access
The board SHALL let the user open each document of an application and copy the
text of a cover letter. Copying form answers is defined with the answers
themselves (`form-answers`).

#### Scenario: Copying a cover letter
- **WHEN** the user activates copy on a cover letter
- **THEN** the letter text is placed on the clipboard

### Requirement: Ended applications hidden by default
The board SHALL hide applications whose status ended them by default, SHALL
state how many are hidden and with which statuses, and SHALL show them when
the user asks.

#### Scenario: Default view
- **WHEN** the board opens with nine rejected or ghosted applications
- **THEN** those nine are not listed and the board states that nine ended applications are hidden, naming Rejected and Ghosted

#### Scenario: Custom ending status
- **WHEN** an application has a user-created status that ends an application
- **THEN** it is hidden by default like the built-in ending statuses

#### Scenario: Selecting an ending status
- **WHEN** the user selects the count card of an ending status
- **THEN** the applications with that status are listed even though ended applications are hidden by default

### Requirement: One count per status
The board SHALL show one count card for each status that at least one
application has, with the status's full name and its number of applications,
in the order of the status list, and selecting a card SHALL filter the table
by that status.

#### Scenario: Counts by status
- **WHEN** three applications are Applied, one is Interview, and one has the custom status "Technical test sent"
- **THEN** the board shows the cards "Applied 3", "Interview 1", and "Technical test sent 1", and no card for statuses nobody has
