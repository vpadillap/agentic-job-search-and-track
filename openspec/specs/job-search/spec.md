# job-search Specification

## Purpose
Defines how a job search run is requested, which postings it considers, how
duplicates and unsuitable postings are handled, and what the user is told.

## Requirements

### Requirement: Search on request with a posting-age window
A search SHALL consider only postings published within the last 7 days by
default, and SHALL use a different window when the user gives one for that run.

#### Scenario: Default window
- **WHEN** the user requests a search without a window
- **THEN** only postings published in the last 7 days are stored as results

#### Scenario: Custom window
- **WHEN** the user requests a search for the last 3 days
- **THEN** only postings published in the last 3 days are stored and the run records a 3-day window

### Requirement: Search uses the active profile and enabled providers
A search SHALL query each enabled provider for each included target title and
SHALL NOT query excluded titles or disabled providers.

#### Scenario: Disabled provider
- **WHEN** a provider is disabled
- **THEN** the run performs no queries on it and reports zero results for it

### Requirement: A provider failure does not fail the run
The search SHALL continue when a provider fails or needs the user present, and
SHALL record which provider was skipped and why.

#### Scenario: Provider needs the user present
- **WHEN** a provider requires a live walk and the user is not present
- **THEN** the run completes with the other providers and reports that provider as skipped with the reason

### Requirement: De-duplication and memory of past decisions
The search SHALL treat postings as the same only when they share the provider's
own posting id or the URL, SHALL recognize such postings found again in earlier
runs, SHALL NOT present dismissed or already tracked postings as new, and SHALL
keep the same job found on different sites as separate postings marked as
possible duplicates.

#### Scenario: Same URL found twice
- **WHEN** a run returns a posting whose URL is already stored
- **THEN** no second posting is stored and the sighting is counted as a duplicate or as already seen

#### Scenario: Same job on two sites
- **WHEN** two providers return a posting with the same company and title published within 7 days of each other
- **THEN** both postings are stored separately and each is marked as a possible duplicate of the other

#### Scenario: Previously dismissed
- **WHEN** a search finds a posting the user dismissed earlier
- **THEN** it is counted as already seen and not listed as new

### Requirement: First-pass filter with reasons
The search SHALL exclude postings that clearly violate a hard constraint of the
profile or an active rule, SHALL record the reason for each exclusion, and
SHALL keep ambiguous postings with a visible flag instead of excluding them. A
posting whose work mode is not stated SHALL NOT be excluded for its work mode.

#### Scenario: Wrong work mode
- **WHEN** a posting is onsite-only and the profile accepts remote only
- **THEN** it is stored as filtered out with the reason "work mode"

#### Scenario: Ambiguous seniority
- **WHEN** a posting's seniority appears lower than the user's but is not stated clearly
- **THEN** it stays in the results with a flag describing the doubt

#### Scenario: Work mode not stated
- **WHEN** neither the title nor the description of a posting says where the work is done, and the profile accepts remote only
- **THEN** the posting stays in the results with a flag saying the work mode is not stated

### Requirement: Verbatim capture
The search SHALL store each posting's description exactly as published, its
link, and its publication date as an absolute date. It SHALL also store the
posting's work mode (remote, hybrid, or onsite) and, when the posting says
more about the arrangement, a work-mode detail in the posting's language, both
as read by the agent from the title and the complete description; neither is
guessed when the posting does not state it.

#### Scenario: Relative date
- **WHEN** a site shows "2 days ago" for a posting
- **THEN** the stored publication date is the corresponding calendar date

#### Scenario: Hybrid with days on site
- **WHEN** a Spanish posting says the role is hybrid with two days a week at the office
- **THEN** the posting is stored with work mode hybrid and a Spanish detail stating two days a week on site

#### Scenario: Arrangement beyond the mode
- **WHEN** a remote posting mentions shortened Fridays in summer
- **THEN** the posting is stored as remote with a detail that mentions the shortened summer Fridays

### Requirement: Form questions are captured when visible
The search SHALL store the application-form questions of a posting when they
can be seen without submitting anything, and SHALL NOT submit or start an
application.

#### Scenario: Visible questions
- **WHEN** a posting's application form shows four questions before submission
- **THEN** the four questions are stored with the posting and nothing is submitted

### Requirement: Run report
At the end of a run the agent SHALL report counts of found, new, filtered, and
duplicate postings, skipped providers, and the top results, and the panel SHALL
show the same run.

#### Scenario: Run finished
- **WHEN** a search completes
- **THEN** the counts reported by the agent match the run summary shown in the panel
