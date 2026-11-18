## ADDED Requirements

### Requirement: Public documentation covers use and contribution
The repository SHALL document, in English with a Spanish section in the
README, how to install and use the project, every user command and the
plain-language way of asking, every job site with its coverage and access
method, how to add a private job site and contribute it, and how to
contribute code under the project's workflow and privacy rules.

#### Scenario: A newcomer contributes a job site
- **WHEN** a newcomer reads the README and CONTRIBUTING.md
- **THEN** they find how to add a job site for themselves and how to contribute it as a pull request

### Requirement: Documentation matches the code
Every command named in the README SHALL exist as a skill, and every provider
file in `providers/` SHALL appear in the README's job-site list.

#### Scenario: Command without a skill
- **WHEN** the README names a command that has no skill
- **THEN** the documentation tests fail and name the command

#### Scenario: Provider without documentation
- **WHEN** a provider file exists that the README does not list
- **THEN** the documentation tests fail and name the provider
