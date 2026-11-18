## ADDED Requirements

### Requirement: Global and local providers
Each provider file SHALL declare its coverage in `regions`: `[global]` for a
site that serves many countries, or a list of two-letter uppercase country
codes for a site that serves only those countries (local). Validation SHALL
reject any other value, and the provider list SHALL report each provider's
coverage (`global` or `local`) and its countries.

#### Scenario: Global provider
- **WHEN** a provider file has `regions: [global]`
- **THEN** the provider list reports it with coverage `global` and no countries

#### Scenario: Local provider
- **WHEN** a provider file has `regions: [PE]`
- **THEN** the provider list reports it with coverage `local` and countries `PE`

#### Scenario: Invalid regions
- **WHEN** a provider file has `regions: [global, PE]`, `regions: [pe]`, or `regions: []`
- **THEN** validation reports the file as invalid and names the `regions` field

#### Scenario: Coverage is visible to the user
- **WHEN** the user looks at the job sites in setup or in the panel
- **THEN** each site is shown as global or local with its countries

### Requirement: Each country of a local provider is verified
A local provider with more than one country SHALL record, for each country in
`regions`, the site address used there and the date its recipe was last
verified in that country, and validation SHALL report every country without
that record and every record for a country not in `regions`.

#### Scenario: Country without a verification
- **WHEN** a provider file has `regions: [PE, CL]` and its countries table has a row only for PE
- **THEN** validation reports the file as invalid and names CL

#### Scenario: Every country verified
- **WHEN** a provider file has `regions: [PE, CL]` and a row with a valid date for each
- **THEN** the file passes validation

### Requirement: Job sites offered and filtered by country
Setup SHALL offer the global providers plus the local providers of the user's
country, and the panel's job-site lists SHALL let the user filter by country,
showing by default the global providers plus those of the profile's country.
Filtering SHALL NOT enable or disable any provider.

#### Scenario: Setup for a user in Peru
- **WHEN** the user's country is PE during setup
- **THEN** the agent offers the global sites and the sites local to PE, and not sites local to other countries

#### Scenario: Filtering the panel list
- **WHEN** the user picks another country in the job-site list's filter
- **THEN** the list shows the global sites and the sites of that country, and every site keeps its on/off state
