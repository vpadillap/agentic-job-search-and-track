## ADDED Requirements

### Requirement: Local providers only for their countries
A search SHALL skip an enabled local provider whose countries do not include
the profile's country, recording the reason `other_country`, and SHALL NOT
query it. When the profile has no country, local providers SHALL be searched
as usual.

#### Scenario: Local provider of another country
- **WHEN** the profile's country is CL and an enabled provider has `regions: [PE]`
- **THEN** the run reports that provider as skipped with reason `other_country` and performs no queries on it

#### Scenario: Local provider of the user's country
- **WHEN** the profile's country is PE and an enabled provider has `regions: [PE]`
- **THEN** the provider is searched

#### Scenario: No country in the profile
- **WHEN** the profile has no country and an enabled provider is local
- **THEN** the provider is searched
