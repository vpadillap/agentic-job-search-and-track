## ADDED Requirements

### Requirement: <Site> is read only by its stated route
The <Site> provider SHALL read <Site> only by the route stated in
`providers/<id>.md` and SHALL NOT sign in for the user, pass credentials
through automation, or change anything on the site.

#### Scenario: Searching <Site>
- **WHEN** a search runs with <Site> enabled
- **THEN** every <Site> result comes from the stated route

### Requirement: Verbatim postings
For each posting the provider SHALL record the site's own id, the link, the
title, company, location, the publication date when the site states it, and
the complete description verbatim.

#### Scenario: Complete posting
- **WHEN** a posting is read
- **THEN** its record carries the site's id, link, title, company, location, and complete description

### Requirement: Terms-of-use risk is stated
The provider file SHALL state what <Site>'s terms say about automated access
and the realistic consequence for the user.

#### Scenario: Reading the provider file
- **WHEN** the user or the agent reads `providers/<id>.md`
- **THEN** the terms-of-use risk is stated in it
