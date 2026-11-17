# panel-shell Specification

## Purpose
Defines the local web panel's frame: how it is reached, its tabs, language
switching, data freshness, and how it hands work to the agent.

## Requirements

### Requirement: Local-only panel
The panel SHALL be served only on the local machine and SHALL refuse requests
that are not addressed to a loopback host name.

#### Scenario: Local access
- **WHEN** the user opens the panel address on the same machine
- **THEN** the panel loads

#### Scenario: Non-loopback host header
- **WHEN** a request arrives with a host name that is not a loopback name
- **THEN** the request is rejected

### Requirement: Tabbed desktop layout
The panel SHALL present four tabs: Search, Applications, Learning, and Profile
& agent, with counters on Search (new results) and Applications (active), and
SHALL keep the selected tab across reloads.

#### Scenario: Reload keeps the tab
- **WHEN** the user reloads the page while on the Applications tab
- **THEN** the Applications tab is shown

### Requirement: Language switching
The panel SHALL be fully usable in English and Spanish, SHALL switch language
without reloading, and SHALL remember the choice.

#### Scenario: Switching to English
- **WHEN** the user selects EN in a panel showing Spanish
- **THEN** all panel labels are shown in English and remain so after a restart

#### Scenario: Agent-written text
- **WHEN** the language is switched
- **THEN** text written by the agent or the user is displayed unchanged

### Requirement: Data freshness
The panel SHALL show when the data last changed, SHALL refresh the visible
board after the agent or another window changes data, and SHALL NOT discard
input the user is currently editing.

#### Scenario: Agent finishes a search
- **WHEN** the agent stores new results while the Search tab is open
- **THEN** the new results appear without the user reloading the page

#### Scenario: Change during editing
- **WHEN** data changes while the user is typing in a field
- **THEN** the field keeps its content and the panel offers to load the new data

### Requirement: The panel never runs the agent
The panel SHALL present agent actions as commands the user copies into their
agent session, and SHALL show a count of items pending for the agent.

#### Scenario: Copying a command
- **WHEN** the user activates the copy control next to a command
- **THEN** the command text is placed on the clipboard and the panel confirms it

### Requirement: Usable before any data exists
The panel SHALL show an explanatory empty state with the next command to run
when there is no data.

#### Scenario: Before setup
- **WHEN** the panel is opened on an uninitialized workspace
- **THEN** it explains that setup is needed and shows the setup command
