## ADDED Requirements

### Requirement: What is new, from the changelog
Before updating, the agent SHALL tell the user what the update brings from the
changelog entries the clone does not have yet, in the user's language and in
plain words.

#### Scenario: Is it worth updating
- **WHEN** the user asks whether there is a new version worth installing
- **THEN** the agent summarizes the new changelog entries (added, changed, fixed) without updating

### Requirement: New job sites offered after an update
After an update that brings new job sites, the agent SHALL offer to turn each
one on, stating its terms note, and with the user's yes SHALL offer to search
only that site now or to run the day's full search including it. Nothing is
turned on or searched without the user's yes.

#### Scenario: A new job site arrives
- **WHEN** an update adds a job site that works in the user's country
- **THEN** the agent asks whether to turn it on and, if yes, whether to search it alone now or run the full search including it
