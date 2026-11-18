## MODIFIED Requirements

### Requirement: Adding a provider
A contributor SHALL be able to add a provider by adding one file that follows
the template, without changing application code, either in the repository's
`providers/` folder or in the user's private providers folder.

#### Scenario: New provider file
- **WHEN** a valid new provider file is added
- **THEN** the provider appears in the list of available providers

#### Scenario: New private provider file
- **WHEN** a valid new provider file is added to the user's private providers folder
- **THEN** the provider appears in the list of available providers marked as private
