## ADDED Requirements

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
