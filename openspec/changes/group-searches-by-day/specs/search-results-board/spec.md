## MODIFIED Requirements

### Requirement: Earlier runs
The board SHALL show the latest group of runs by default, with every posting
of the group's runs once and a summary that adds up its runs, and SHALL let
the user open an earlier group.

#### Scenario: Viewing a previous run
- **WHEN** the user selects an earlier group of runs
- **THEN** the summary and table show that group's runs and postings

#### Scenario: Two searches on the same day
- **WHEN** two runs were made on the same day
- **THEN** the board shows them on one page, with their postings once and their counts added up
