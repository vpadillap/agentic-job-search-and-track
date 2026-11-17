## ADDED Requirements

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
