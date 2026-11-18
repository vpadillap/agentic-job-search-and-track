## ADDED Requirements

### Requirement: Private providers
A user SHALL be able to add a provider file in their private home without
changing the repository. A private provider SHALL be validated, listed,
enabled, and searched like a repository provider, SHALL be able to use any
access method, dependencies, and its own reader, SHALL be shown as private,
and SHALL be invalid when its id is already used by a repository provider.

#### Scenario: Adding a private provider
- **WHEN** a valid provider file is placed in the private providers folder
- **THEN** it is listed as a private provider, switched off, and can be enabled and searched

#### Scenario: Private provider with its own reader
- **WHEN** a private provider has a reader file next to it
- **THEN** `jt providers read` runs that reader with the same rules and outputs as a built-in reader

#### Scenario: Id already used
- **WHEN** a private provider file has the id of a repository provider
- **THEN** the private file is reported invalid and the repository provider is used

### Requirement: Rules a new provider must meet
A new provider SHALL be studied with real requests before its access method is
chosen, SHALL read logged out unless the user signs in themselves in their own
browser, SHALL never receive credentials through automation, SHALL be
read-only, SHALL declare its coverage, and SHALL state the site's
terms-of-use risk. It is proved when validation passes and a real search
returns complete postings for each country it claims.

#### Scenario: Provider claimed for two countries
- **WHEN** a new local provider claims two countries
- **THEN** it is proved only after a real search succeeds in each of them and each has a dated row

### Requirement: Guided workflow
The system SHALL offer a guided command that studies a site with the user,
writes the private provider file, validates it, runs the proving search, and
records the study privately.

#### Scenario: Finishing the workflow
- **WHEN** the proving search succeeds for every claimed country
- **THEN** the provider is enabled for the user and the study is saved in the private home

### Requirement: Pull request offer
After a provider is proved, the agent SHALL offer to contribute it as a pull
request and SHALL open one only with the user's consent, after the project's
checks pass, with an OpenSpec change describing the study, and without any
personal data.

#### Scenario: User accepts
- **WHEN** the user accepts the offer and the checks pass
- **THEN** a pull request adds the provider file and its change folder, with a study table that contains no personal data

#### Scenario: User declines
- **WHEN** the user declines the offer
- **THEN** nothing is pushed and the provider stays private
