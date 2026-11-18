## ADDED Requirements

### Requirement: Open-web search with reputable sources
The agentic-search provider SHALL find postings for each included title by
searching the web, SHALL prefer the company's own careers page or
applicant-tracking board over copies of the same posting, and SHALL NOT use
aggregators that republish postings, pages without a company name, or pages
that require payment or personal data to show a posting.

#### Scenario: Posting found on an aggregator
- **WHEN** a posting is found on a site that republishes it and the company's own page has the same posting
- **THEN** the posting is read and recorded from the company's own page

#### Scenario: Untrusted page
- **WHEN** a page asks for personal data before showing the posting
- **THEN** the posting is not used

### Requirement: Company channels are explored
For each company found hiring for an included title, the provider SHALL look
at that company's own careers channel for other openings that match the
user's included titles, within the provider's limits.

#### Scenario: Company with more openings
- **WHEN** the first results show a company hiring for one title and its careers page lists another opening matching an included title
- **THEN** that opening is also read and imported

### Requirement: Sites with their own provider are not read
The provider SHALL NOT read a site that has its own provider file, whether
that provider is enabled or disabled.

#### Scenario: Posting only on a disabled provider's site
- **WHEN** a posting is found only on the site of a provider the user turned off
- **THEN** it is not read or imported

### Requirement: Verbatim records with their source
Each posting SHALL be imported with its canonical URL as external id, the
site it came from, the complete description copied verbatim, and the
publication date only when the page states it.

#### Scenario: Page without a date
- **WHEN** a posting's page does not show a publication date
- **THEN** the posting is imported without a date and flagged, and no date is guessed

### Requirement: Bounded effort
The provider SHALL stop at the limits stated in its file (postings per title,
companies explored per title, time between requests) and SHALL say in the run
report when a limit was reached.

#### Scenario: Company limit reached
- **WHEN** the agent has explored the maximum number of companies for a title
- **THEN** it stops exploring more for that title and the run report says the limit was reached
