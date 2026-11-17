## MODIFIED Requirements

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
