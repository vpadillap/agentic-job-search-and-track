## ADDED Requirements

### Requirement: Route chosen by a study
The Get on Board provider SHALL read Get on Board only by the route the owner
chose from this change's study, as stated in `providers/getonbrd.md`, and
SHALL NOT use a route the file marks as not working or forbidden.

#### Scenario: Searching Get on Board
- **WHEN** a search runs with Get on Board enabled
- **THEN** every Get on Board result comes from the route stated in the provider file

### Requirement: Logged out and read-only
The provider SHALL read Get on Board without the user's account and SHALL
NOT apply, save, follow, or change anything on the site.

#### Scenario: Posting with an application form
- **WHEN** a posting offers an application form
- **THEN** the form is not started, filled, or submitted

### Requirement: Verbatim postings with their stated salary
For each posting the provider SHALL record the site's own id, its link, the
title, company, location or remote scope, the publication date when the site
states it, and the complete description verbatim; a salary the posting
states SHALL be kept as a hint for the agent's reading.

#### Scenario: Posting with a salary range
- **WHEN** a posting states a salary range
- **THEN** its record carries the range as the site states it, for the agent to read as the published salary

### Requirement: Not read by the agentic web search
Once Get on Board has its own provider, the agentic web search SHALL NOT read
it, whether the Get on Board provider is enabled or not.

#### Scenario: Web search finds a Get on Board posting
- **WHEN** the agentic web search finds a posting on getonbrd.com
- **THEN** it does not read or import it
