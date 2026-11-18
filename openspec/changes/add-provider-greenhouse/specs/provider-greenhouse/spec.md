## ADDED Requirements

### Requirement: Route chosen by a study
The Greenhouse provider SHALL use only the access route the owner chose from
this change's study, as stated in `providers/greenhouse.md`, and SHALL NOT use
a route the file marks as not working or forbidden.

#### Scenario: Searching Greenhouse
- **WHEN** a search runs with Greenhouse enabled
- **THEN** the agent reads Greenhouse only by the route stated in the provider file

### Requirement: No credentials through automation
The Greenhouse provider SHALL NOT receive, type, or store the user's
credentials or cookies. If a route needs the user signed in, the user signs
in themselves in their own browser, the provider is marked as needing a login
and the user's presence, and a run without the user's confirmation skips it.

#### Scenario: Unattended run with a sign-in route
- **WHEN** the chosen route needs the user signed in and the user has not confirmed they are present
- **THEN** the run records Greenhouse as skipped with the reason and searches the other providers

### Requirement: Verbatim postings and form questions
For each posting the provider SHALL record the posting's own id as the
external id, a link to the posting, title, company, location, publication or
update date, the complete description, and the application-form questions
when they are visible without applying.

#### Scenario: Posting with visible questions
- **WHEN** a Greenhouse posting shows its application form questions without submitting anything
- **THEN** the questions are captured with the posting and nothing is submitted or saved

### Requirement: Read-only
The provider SHALL NOT apply, save, follow, or change anything on Greenhouse or
in the user's Greenhouse account.

#### Scenario: Reading a posting with an application form
- **WHEN** the agent reads a posting with an application form
- **THEN** it leaves the form without filling or submitting it
