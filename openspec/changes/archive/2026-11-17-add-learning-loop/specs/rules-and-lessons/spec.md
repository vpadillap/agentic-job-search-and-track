## Purpose

Defines the single list of rules the agent obeys (system rules, the user's
stated preferences, and lessons learned from results) and the user's control
over how lessons change the agent's behavior.

## ADDED Requirements

### Requirement: One visible list of rules
The system SHALL keep system rules, user preferences, and learned lessons in
one list, each showing its origin and date, and the panel SHALL display the
active ones.

#### Scenario: Viewing agent memory
- **WHEN** the user opens the agent memory section
- **THEN** each active rule is listed with whether it came from the system, from the user, or from learning

### Requirement: User preferences are remembered
When the user states a lasting preference to the agent, it SHALL be stored as a
user rule and obeyed in later sessions.

#### Scenario: Stated preference
- **WHEN** the user tells the agent not to change the resume layout
- **THEN** a user rule exists and later document preparation in a new session keeps the layout

### Requirement: Rules are loaded before acting
The agent SHALL obtain the active rules before searching, scoring, preparing
documents, or suggesting salaries, and SHALL act in accordance with them.

#### Scenario: Active salary rule
- **WHEN** an active rule limits the salary ask to 8% over the median
- **THEN** salary answers proposed afterwards do not exceed that limit

### Requirement: Learning refresh before scoring and tailoring
Before scoring postings and before tailoring documents, the agent SHALL refresh
learning: current insights and level, the active lessons and their effects, the
full history, and new lesson candidates. The prediction model SHALL be refitted
only when enough new outcomes have resolved since the last fit.

#### Scenario: Search run
- **WHEN** a search run reaches the scoring step
- **THEN** learning is refreshed before the first posting is scored

#### Scenario: Few new outcomes
- **WHEN** learning is refreshed and fewer than ten applications have resolved since the last fit
- **THEN** the model is not refitted and the previous validated model stays in use

### Requirement: Learning does not change searching
Lessons and learning results SHALL NOT change which titles or job sites are
searched or in which order; lessons about titles SHALL take effect only as
changes to the profile the user applies.

#### Scenario: Title that does not progress
- **WHEN** a lesson suggests putting a title under review and the user applies it
- **THEN** the profile marks the title as under review, and no search behavior changes otherwise

### Requirement: Lessons are proposed with evidence
A refresh or review SHALL propose lessons only when supported by at least
five cases, and each proposed lesson SHALL state what it would change, which
area it affects, and the evidence with counts. Lessons SHALL be drawn from
outcomes, from repeated dismissal reasons, and from agent readings the user
corrected.

#### Scenario: Insufficient cases
- **WHEN** a pattern is supported by three applications
- **THEN** no lesson is proposed for it

#### Scenario: Proposed lesson
- **WHEN** a title has seven applications and no interviews while a similar title progresses
- **THEN** a lesson to put that title under review in the profile is proposed with those counts

#### Scenario: Repeated dismissals
- **WHEN** the user dismissed six onsite postings outside the accepted areas for "location"
- **THEN** a lesson about those postings is proposed with the six dismissals as evidence

#### Scenario: Corrected readings
- **WHEN** the user corrected the agent's work-mode reading on five postings from one site
- **THEN** a lesson for reading that site is proposed with those corrections as evidence

### Requirement: Retraining the scoring rubric
When predictions are validated and the score components predict interviews
differently from their current weights, a lesson SHALL propose new component
weights with the evidence; applying it SHALL create a new weights version, keep
earlier scores with their version, and mark open postings for rescoring.

#### Scenario: Skills matter more than seniority
- **WHEN** the validated model shows skills predict interviews much more strongly than seniority
- **THEN** a lesson proposes more points for skills and fewer for seniority, with counts

#### Scenario: Applying new weights
- **WHEN** the user applies a weights lesson
- **THEN** new scores use the new weights version and open postings appear as needing a rescore

### Requirement: The user decides
A proposed lesson SHALL have no effect until the user applies it; the user
SHALL be able to apply or ignore a proposal and to revert an applied lesson.

#### Scenario: Applying
- **WHEN** the user applies a proposed lesson
- **THEN** it becomes active and affects the agent from its next run

#### Scenario: Ignoring
- **WHEN** the user ignores a proposed lesson
- **THEN** it has no effect and is not proposed again on the same evidence

#### Scenario: Reverting
- **WHEN** the user reverts an applied lesson
- **THEN** its effect stops from the agent's next run and past records are unchanged

### Requirement: System rules cannot be disabled
Rules that protect the user (salary evidence, truthful documents, no automatic
applications) SHALL be listed and SHALL NOT be overridable by lessons.

#### Scenario: Conflicting lesson
- **WHEN** a lesson would allow suggesting a salary without evidence
- **THEN** it is not proposed

### Requirement: Traceable influence
Each search result, score, document, and suggestion SHALL record which rules
influenced it.

#### Scenario: Checking a lesson's effect
- **WHEN** a later analysis evaluates an applied lesson
- **THEN** it can compare outcomes of items produced with and without that lesson
