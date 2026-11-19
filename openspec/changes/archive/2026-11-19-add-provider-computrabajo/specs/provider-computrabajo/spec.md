## ADDED Requirements

### Requirement: Route chosen by a study
The Computrabajo provider SHALL read Computrabajo's job postings only by the
route the owner chose from this change's study, as stated in
`providers/computrabajo.md`, and SHALL NOT use a route the file marks as not
working or forbidden.

#### Scenario: Searching Computrabajo
- **WHEN** a search runs with Computrabajo enabled in one of its countries
- **THEN** every Computrabajo result comes from the route stated in the provider file

### Requirement: Logged out and read-only
The provider SHALL read Computrabajo without the user's account and SHALL NOT
apply, save, follow, or change anything on the site.

#### Scenario: Posting with an application form
- **WHEN** a posting offers an application form
- **THEN** the form is not started, filled, or submitted

### Requirement: Verbatim postings
For each posting the provider SHALL record the site's own id, its link, the
title, company, location, the publication date when the site states it, and
the complete description verbatim; a salary the posting states SHALL be kept
as a hint for the agent's reading.

#### Scenario: Posting with a stated salary
- **WHEN** a posting states a salary
- **THEN** its record carries the salary as the site states it, for the agent to read as the published salary
