## MODIFIED Requirements

### Requirement: Per-user provider state
The system SHALL store, per user, whether each provider is enabled and the
result of its last use, and the user SHALL be able to enable or disable a
provider from the panel. A provider the user has not enabled SHALL be
disabled, including a provider whose file arrives with an update of the
repository.

#### Scenario: Disabling from the panel
- **WHEN** the user turns a provider off in the panel
- **THEN** the next search skips it

#### Scenario: New provider after an update
- **WHEN** an update adds a provider file the user has never turned on
- **THEN** the provider is listed as disabled and the next search does not query it

#### Scenario: Enabling a provider
- **WHEN** the user turns a provider on in setup, the panel, or the CLI
- **THEN** the next search queries it
