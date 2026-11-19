# setup-onboarding Specification

## Purpose
Defines the first-run experience that takes a freshly cloned repository to a
personalized, working installation and leaves the user knowing how to use it.

## Requirements

### Requirement: Environment check before anything else
The setup flow SHALL check the environment first, tell the user what is
missing, and install missing requirements only after telling the user what will
be installed.

#### Scenario: Missing packages
- **WHEN** setup starts on a machine without the project's packages installed
- **THEN** the user is shown the list of what will be installed and the installation runs before any other step

#### Scenario: Unsupported Python
- **WHEN** the Python version is older than the minimum supported
- **THEN** setup stops and explains which version is required

### Requirement: Language is the first question
The setup flow SHALL ask whether the panel should be in English or Spanish
before any other question, and SHALL conduct the rest of the setup in that
language.

#### Scenario: Spanish chosen
- **WHEN** the user chooses Spanish
- **THEN** the panel language is stored as Spanish and subsequent questions are asked in Spanish

### Requirement: Resume intake with confirmation
The setup flow SHALL store the user's resume unchanged in the private home,
extract its text, and ask the user to confirm a summary of what was read.

#### Scenario: Readable resume
- **WHEN** the user provides a text-based PDF or DOCX resume
- **THEN** the original file and its extracted text exist in the profile folder and the user is shown a summary to confirm

#### Scenario: Unreadable resume
- **WHEN** no text can be extracted from the provided file
- **THEN** the user is told and asked for another file or for confirmation of a visually read version

### Requirement: Job-needs questionnaire
The setup flow SHALL collect work mode, contract types, locations, minimum
salary, languages, seniority, and default posting age, and SHALL store them as
the first profile version.

#### Scenario: Combination answers
- **WHEN** the user wants both remote and hybrid roles as full-time or contractor
- **THEN** the stored profile contains both work modes and both contract types

#### Scenario: Optional answers skipped
- **WHEN** the user declines to give a minimum salary
- **THEN** the profile is stored without one and no default is invented

### Requirement: Target titles are researched and confirmed
The setup flow SHALL ask for the titles the user wants, propose alternates
based on the resume and a preliminary search of real postings, and include a
proposed title only when the user accepts it.

#### Scenario: Accepting and rejecting proposals
- **WHEN** the agent proposes three alternate titles and the user accepts one and rejects one
- **THEN** the accepted title is included, the rejected title is excluded, and the unanswered one remains suggested

### Requirement: Privacy registration
The setup flow SHALL register the user's identifying terms for the privacy
guard and SHALL create all personal files only inside the private home.

#### Scenario: After setup
- **WHEN** setup completes
- **THEN** version control reports no new or modified tracked files and the private terms file exists in the private home

### Requirement: Preferences without duplication
The setup flow SHALL record a standing preference as a rule only when it adds
to the rules already in force, and SHALL let the user reword or retire their
own rules when revising.

#### Scenario: User keeps the default
- **WHEN** the user is satisfied that the resume layout is never changed, which is already a system rule
- **THEN** no additional rule is stored

#### Scenario: Revising preferences
- **WHEN** the preferences step is repeated and the user changes an earlier preference
- **THEN** the existing rule is reworded or retired instead of a second rule being added

### Requirement: Resumable setup
The setup flow SHALL resume from the first incomplete step when run again and
SHALL allow completed steps to be revised without losing other data.

#### Scenario: Interrupted setup
- **WHEN** setup is interrupted after the resume step and run again
- **THEN** it continues with the questionnaire without asking for the resume again

### Requirement: Guided tour
The setup flow SHALL end by starting the panel and explaining each panel tab,
each available command with an example, where the user's data is stored, and
the recommended next step.

#### Scenario: Setup finished
- **WHEN** the last setup step completes
- **THEN** the user receives the panel address and the tour in their chosen language

### Requirement: Python installed by a fixed route on Windows
When Python is missing on Windows, setup SHALL install it by the route stated
in the setup skill (not the Microsoft Store), SHALL use the installed
interpreter by its full path for the rest of the session so no restart is
needed, and SHALL create the project's environment with it.

#### Scenario: Windows without Python
- **WHEN** setup runs on Windows and no working Python is found
- **THEN** the agent installs Python by the stated route, creates the project's environment with it in the same session, and the environment check passes
