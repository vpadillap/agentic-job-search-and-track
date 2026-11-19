# self-update Specification

## Purpose
TBD - created by archiving change add-self-update. Update Purpose after archive.

## Requirements

### Requirement: Update on request without touching user data
On the user's request the agent SHALL update the clone from the repository
and leave the project working: packages, database schema, command names, and
the tools of enabled job sites. It SHALL NOT change, move, or delete anything
in the user's private home except through database migrations and offers the
user accepts.

#### Scenario: A new version is available
- **WHEN** the user asks to update and the repository has newer commits
- **THEN** the agent says what is new, and with the user's yes pulls them, reinstalls, migrates, refreshes command names, installs missing tools, and confirms that diagnostics pass

#### Scenario: Already up to date
- **WHEN** the user asks to update and there are no newer commits
- **THEN** the agent says so and changes nothing

### Requirement: No forced update
The agent SHALL NOT discard the user's changes to tracked files or rewrite
history to update. A clone with changed tracked files or a branch that cannot
be fast-forwarded SHALL be explained to the user, who decides.

#### Scenario: A source file was edited
- **WHEN** the user asks to update and a tracked file has local changes
- **THEN** the agent names the file and asks before keeping it aside or stopping; nothing is discarded

### Requirement: A failed update can be undone
When an update step fails, the agent SHALL stop, say what failed, and name the
previous version and the database backup that restore the earlier state.

#### Scenario: A step fails
- **WHEN** reinstalling or migrating fails after the pull
- **THEN** the agent reports the failure, the previous commit, and the backup, and asks before restoring

### Requirement: One-time offers
A change MAY declare a one-time offer for existing users. The system SHALL list
pending offers that apply to the user's data, SHALL apply an offer only when
the user accepts it, and SHALL never present an answered offer again.

#### Scenario: Offer after an update
- **WHEN** an update brings an offer that applies to the user's data
- **THEN** the agent presents it once, applies it only with the user's yes, and records the answer

### Requirement: What is new, from the changelog
Before updating, the agent SHALL tell the user what the update brings from the
changelog entries the clone does not have yet, in the user's language and in
plain words.

#### Scenario: Is it worth updating
- **WHEN** the user asks whether there is a new version worth installing
- **THEN** the agent summarizes the new changelog entries (added, changed, fixed) without updating

### Requirement: New job sites offered after an update
After an update that brings new job sites, the agent SHALL offer to turn each
one on, stating its terms note, and with the user's yes SHALL offer to search
only that site now or to run the day's full search including it. Nothing is
turned on or searched without the user's yes.

#### Scenario: A new job site arrives
- **WHEN** an update adds a job site that works in the user's country
- **THEN** the agent asks whether to turn it on and, if yes, whether to search it alone now or run the full search including it
