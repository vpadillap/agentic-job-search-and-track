## ADDED Requirements

### Requirement: A changelog entry for every merge
Every change merged into `main` SHALL add an entry to `CHANGELOG.md` in plain
language for the user, with its date, the change's name, what was added,
changed, or fixed, the providers and one-time offers it brings, and any action
the user must take; and SHALL update the documentation it affects.

#### Scenario: A provider is added
- **WHEN** a change that adds a job site is merged
- **THEN** the changelog has an entry saying so in plain language and naming the provider's id

### Requirement: The changelog is checked
A pull request that changes code, provider files, or skills without changing
`CHANGELOG.md` SHALL fail the continuous-integration check.

#### Scenario: Code changed without an entry
- **WHEN** a pull request changes a source file and not the changelog
- **THEN** the check fails and says that a changelog entry is missing
