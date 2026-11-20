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
The agent SHALL finish a run only after every imported batch has been
filtered and scored and the salary research for the run is done (or a site
the user chose not to wait for is left cooling down). At the end of a run the
agent SHALL report counts of found, new, filtered, and duplicate postings,
skipped providers, and the top results, and the panel SHALL show the same
run.

#### Scenario: Run finished
- **WHEN** a search completes
- **THEN** the counts reported by the agent match the run summary shown in the panel

#### Scenario: Batches still being scored
- **WHEN** every site has been searched but two batches are still being scored
- **THEN** the run stays open until both are scored, and only then the agent finishes it and reports

### Requirement: Readings merged into drafts at import
When a provider's reader has written drafts, the import SHALL accept the
drafts together with the agent's readings, matched by the posting's id on the
site. A reading SHALL contain only the work mode, the work-mode detail, the
language, flags, and the published salary. Every draft SHALL have exactly one
reading, and nothing else in a draft SHALL change, so captured descriptions
are stored exactly as the reader wrote them.

#### Scenario: Drafts with readings
- **WHEN** the agent imports a drafts file with a reading for each draft
- **THEN** every posting is stored with the reader's fields and the agent's reading, and the run report counts them as usual

#### Scenario: Missing reading
- **WHEN** a draft has no reading
- **THEN** the import is refused, names the job ids without a reading, and stores nothing

#### Scenario: A reading cannot change captured text
- **WHEN** a reading contains a field other than work mode, work-mode detail, language, flags, or published salary
- **THEN** the import is refused and names the field

### Requirement: Local providers only for their countries
A search SHALL skip an enabled local provider whose countries do not include
the profile's country, recording the reason `other_country`, and SHALL NOT
query it. When the profile has no country, local providers SHALL be searched
as usual.

#### Scenario: Local provider of another country
- **WHEN** the profile's country is CL and an enabled provider has `regions: [PE]`
- **THEN** the run reports that provider as skipped with reason `other_country` and performs no queries on it

#### Scenario: Local provider of the user's country
- **WHEN** the profile's country is PE and an enabled provider has `regions: [PE]`
- **THEN** the provider is searched

#### Scenario: No country in the profile
- **WHEN** the profile has no country and an enabled provider is local
- **THEN** the provider is searched

### Requirement: Runs grouped by day
A run started on the same local day as the latest group's runs SHALL join that
group. A run on a later day SHALL start a new group unless the user chose to
add it to an earlier group; when a search in the same conversation was made on
an earlier day, the agent SHALL ask the user once which they prefer.

#### Scenario: Second search the same day
- **WHEN** a run starts on the same day as the latest group's runs
- **THEN** it joins that group

#### Scenario: Next day in the same chat
- **WHEN** the agent ran a search yesterday in this conversation and starts one today
- **THEN** it asks whether to add today's search to yesterday's, and groups it as the user answers

### Requirement: Past searches grouped only with consent
Existing runs SHALL keep their own pages after the update until the user
accepts the one-time offer to group past searches by day.

#### Scenario: Accepting the offer
- **WHEN** the user accepts grouping past searches
- **THEN** runs of the same day become one group and nothing else changes

### Requirement: Results are filtered and scored during the search
The agent SHALL filter and score each batch of postings (the postings
imported for one title on one site) while the search goes on, without waiting
for the other titles or sites. Searching SHALL continue while earlier batches
are filtered and scored. Learning SHALL be refreshed once at the start of the
run, before any batch is scored, and every batch of the run SHALL be judged
with that same refresh.

#### Scenario: First batch ready while searching
- **WHEN** the first site has finished one title and three more sites remain to be searched
- **THEN** that title's new postings are filtered and scored before the remaining sites are searched to the end

#### Scenario: Same rules for every batch
- **WHEN** the run has ten batches
- **THEN** learning is refreshed once at the start and all ten batches are scored with the rules and lessons active at that moment

### Requirement: Limited number of helper agents
When the agent filters, scores, or researches salary through background
helper agents, it SHALL never run more than 3 of them at the same time in a
run, whatever the number of titles and sites. Batches waiting for a helper
SHALL be queued and taken in import order. At most one helper SHALL research
salary at a time, and it SHALL take only postings that are already scored.
When background helpers are not available, the agent SHALL do the same work
itself, filtering and scoring each batch right after its import, before
importing the next one.

#### Scenario: Many titles and sites
- **WHEN** a search covers 10 titles on 6 sites and 40 batches have been imported
- **THEN** no more than 3 helpers run at any moment and the other batches wait in the queue

#### Scenario: No background helpers
- **WHEN** the agent cannot start background helpers
- **THEN** it filters and scores each batch itself right after importing it, before importing the next batch

### Requirement: A cool-down does not hold up the rest of the search
When a site is cooling down after a throttle, the agent SHALL go on searching
the other sites and titles, and filtering and scoring the batches already
imported, and SHALL return to that site in the same run once its cool-down
has ended. If the user chose not to wait for the cool-down, the agent SHALL
finish the run once everything else is done.

#### Scenario: One site cooling down
- **WHEN** one site is cooling down for 30 minutes and two other sites are still to be searched
- **THEN** the agent searches the other two sites and scores their batches during those 30 minutes, then resumes the cooled-down site in the same run
