# provider-recipes Specification

## Purpose
Defines the per-site instruction files that tell the agent exactly how to read
each job or salary site, and the per-user state of each provider.

## Requirements

### Requirement: One instruction file per provider
Each supported site SHALL have one file that states its kind, regions, access
method, whether a login or the user's presence is needed, required tools,
pacing limits, the date it was last verified, and step-by-step instructions for
searching and extracting fields.

#### Scenario: Valid provider file
- **WHEN** provider files are validated
- **THEN** a file missing a required field or section is reported with the missing item

### Requirement: Agents follow the provider file
The agent SHALL use the access method and pacing stated in the provider file
and SHALL NOT use a method the file marks as unreliable or forbidden.

#### Scenario: Stated access method
- **WHEN** a provider file states how the site must be accessed
- **THEN** the search uses that method and no other for that provider

### Requirement: Read-only behavior
Provider instructions and the agent SHALL NOT submit applications, send
messages, or modify anything in the user's account on a provider's site.

#### Scenario: Reading form questions
- **WHEN** the agent inspects an application form
- **THEN** it leaves the form without submitting or saving it

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

### Requirement: Dependencies are checked per provider
The system SHALL report, for each enabled provider, whether the tools it
requires are available.

#### Scenario: Missing tool
- **WHEN** an enabled provider requires a tool that is not installed
- **THEN** diagnostics name the provider, the missing tool, and how to install it

### Requirement: Adding a provider
A contributor SHALL be able to add a provider by adding one file that follows
the template, without changing application code.

#### Scenario: New provider file
- **WHEN** a valid new provider file is added
- **THEN** the provider appears in the list of available providers
