## Purpose

Defines the per-site instruction files that tell the agent exactly how to read
each job or salary site, and the per-user state of each provider.

## ADDED Requirements

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

### Requirement: Anonymous access only
The agent SHALL read job and salary sites as a logged-out visitor and SHALL NOT
use the user's logged-in account or browser session on those sites.

#### Scenario: Sign-in required
- **WHEN** a site shows the needed content only after signing in
- **THEN** the agent does not sign in, and the run reports what could not be read

#### Scenario: Sign-in prompt over public content
- **WHEN** a site shows a sign-in prompt over content that is public
- **THEN** the agent follows the provider file's instructions for that case without signing in, or skips the provider and reports it

### Requirement: Read-only behavior
Provider instructions and the agent SHALL NOT submit applications, send
messages, or modify anything in the user's account on a provider's site.

#### Scenario: Reading form questions
- **WHEN** the agent inspects an application form
- **THEN** it leaves the form without submitting or saving it

### Requirement: Per-user provider state
The system SHALL store, per user, whether each provider is enabled and the
result of its last use, and the user SHALL be able to enable or disable a
provider from the panel.

#### Scenario: Disabling from the panel
- **WHEN** the user turns a provider off in the panel
- **THEN** the next search skips it

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
