## ADDED Requirements

### Requirement: The applications table fits the screen
The applications table SHALL show every column without horizontal scrolling
at widths of 1,280 pixels and more, and on narrower widths SHALL move
secondary columns into the row's detail, showing each row as a card at phone
width.

#### Scenario: Laptop screen
- **WHEN** the Applications tab is shown at 1,366 pixels wide
- **THEN** the page does not scroll sideways and the status, documents, and next step of every row are visible
