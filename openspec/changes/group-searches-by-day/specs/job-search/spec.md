## ADDED Requirements

### Requirement: Runs grouped by day
A run started on the same local day as the latest group's runs SHALL join that
group. A run on a later day SHALL start a new group unless the user chose to
add it to an earlier group; when a search in the same conversation was made on
an earlier day, the agent SHALL ask the user once which they prefer.

#### Scenario: Second search the same day
- **WHEN** a run starts on the same day as the latest group's runs
- **THEN** it joins that group

#### Scenario: Next day in the same chat
- **WHEN** the agent ran a search yesterday in this conversation and starts one today
- **THEN** it asks whether to add today's search to yesterday's, and groups it as the user answers

### Requirement: Past searches grouped only with consent
Existing runs SHALL keep their own pages after the update until the user
accepts the one-time offer to group past searches by day.

#### Scenario: Accepting the offer
- **WHEN** the user accepts grouping past searches
- **THEN** runs of the same day become one group and nothing else changes
