# provider-getonbrd Specification

## Purpose
TBD - created by archiving change add-provider-getonbrd. Update Purpose after archive.

## Requirements

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

### Requirement: Remote postings valid for the user's country
A Get on Board search for a title SHALL include the postings in the user's
country, the remote postings open to that country, and the postings remote
from anywhere, and SHALL leave out remote postings limited to other countries.

#### Scenario: Remote from anywhere
- **WHEN** a posting is remote with no country limit and the user's country is PE
- **THEN** it is read for the user, although the site's country filter leaves it out

#### Scenario: Remote limited to another country
- **WHEN** a posting is remote only for Chile and the user's country is PE
- **THEN** it is not read

### Requirement: Not read by the agentic web search
Once Get on Board has its own provider, the agentic web search SHALL NOT read
it, whether the Get on Board provider is enabled or not.

#### Scenario: Web search finds a Get on Board posting
- **WHEN** the agentic web search finds a posting on getonbrd.com
- **THEN** it does not read or import it

### Requirement: The agent installs what an enabled provider needs
Before a search, the agent SHALL install any missing dependency of an enabled
provider into the project's environment, tell the user what it installed, and
search the provider; it SHALL skip the provider only when the installation
fails, saying why. The user SHALL NOT have to install anything by hand.

#### Scenario: Update that needs a new tool
- **WHEN** an update makes an enabled provider need a tool that is not installed
- **THEN** the next search installs it, says so in one line, and searches the provider as usual

#### Scenario: Installation fails
- **WHEN** installing a provider's tool fails
- **THEN** that provider is skipped with the reason and the other providers are searched
