## ADDED Requirements

### Requirement: Provider files name their domains
A provider file MAY list in its front matter the hosts the provider reads
(`domains`, a list of host names, each covering its subdomains, or
`name.*` for every country domain of a site). Every built-in
provider file SHALL list its domains. Validation SHALL report a `domains`
value that is not a list of host names, and SHALL warn, without failing, when
a provider other than the agentic web search has no `domains`. The provider
listing SHALL return each provider's domains.

#### Scenario: Built-in provider with domains
- **WHEN** provider files are validated
- **THEN** every built-in provider file names its domains and passes

#### Scenario: Invalid domains
- **WHEN** a provider file has `domains: "indeed.com"` instead of a list
- **THEN** validation reports the field as having the wrong type

#### Scenario: Private provider without domains
- **WHEN** a private provider file has no `domains`
- **THEN** it is still valid and validation warns that other providers cannot avoid its site
