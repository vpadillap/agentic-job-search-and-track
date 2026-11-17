## MODIFIED Requirements

### Requirement: Expandable detail
Each row SHALL expand to show the job description exactly as captured, the
score breakdown by component with a note for each, and the salary suggestion
with its range, confidence, comparison criteria, and linked evidence. The
complete description SHALL be readable in the page itself, without a box with
its own scroll bar: a long description shows its beginning with a control
that reveals the rest in place.

#### Scenario: Expanding a row
- **WHEN** the user expands a posting
- **THEN** the verbatim description, the per-component score, and each salary evidence source are visible

#### Scenario: Reading a long description
- **WHEN** a posting's description is longer than the visible beginning and the user activates "Read the full description"
- **THEN** the whole description is shown in place, with no inner scroll bar, and "Show less" returns to the beginning
