## ADDED Requirements

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

## MODIFIED Requirements

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
