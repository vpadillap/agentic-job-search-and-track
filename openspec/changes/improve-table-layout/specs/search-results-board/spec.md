## ADDED Requirements

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
