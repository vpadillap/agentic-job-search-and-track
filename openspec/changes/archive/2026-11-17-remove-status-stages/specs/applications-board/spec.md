## REMOVED Requirements

### Requirement: Negative closed applications hidden by default
**Reason**: There is no closed negative stage any more.
**Migration**: Replaced by "Ended applications hidden by default", which hides
applications whose status ended them.

## ADDED Requirements

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

## MODIFIED Requirements

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
