## Purpose

Defines the record kept for every posting the user decides to follow: its
status, tags, the facts of the application, the resume actually sent, and the
full history of what happened.

## ADDED Requirements

### Requirement: Tracked applications persist across searches
A tracked posting SHALL remain available with all its data regardless of later
searches, until the user removes it.

#### Scenario: New search after tracking
- **WHEN** a new search is run after a posting was tracked
- **THEN** the tracked application and its data are unchanged

### Requirement: One status with a stage
Every application SHALL have exactly one status, and every status SHALL belong
to one stage among: to apply, applied, interview, offer, closed positive, and
closed negative.

#### Scenario: Changing status
- **WHEN** the user changes an application from Applied to Interview
- **THEN** the application's stage is interview and the change is recorded in its history with the date

### Requirement: User-defined statuses
The user SHALL be able to create a new status inline by giving it a name and a
stage, and SHALL be able to rename or retire custom statuses. Built-in
statuses SHALL always exist.

#### Scenario: Creating a status inline
- **WHEN** the user types a new status name and assigns it to the closed negative stage
- **THEN** the status is applied to that application and is available for all others

#### Scenario: Retiring a status in use
- **WHEN** the user retires a custom status that some applications have
- **THEN** those applications keep it and it is no longer offered for new assignments

### Requirement: Free-form tags
The user SHALL be able to add and remove any number of free-form tags on an
application.

#### Scenario: Adding a tag
- **WHEN** the user adds the tag "Referral"
- **THEN** the tag is shown on the application and can be used to filter

### Requirement: Application details
The user SHALL be able to record the date they applied, the monthly salary they
asked for, the channel, a contact, notes, and the date of the next step.

#### Scenario: Recording the asked salary
- **WHEN** the user enters the salary they asked for
- **THEN** it is stored with its currency and shown next to the suggested salary

### Requirement: Resume actually sent
The user SHALL be able to upload or replace the resume they actually used, in
place of or in addition to the one proposed by the agent, and the system SHALL
queue the application for rescoring against it.

#### Scenario: Uploading the sent resume
- **WHEN** the user uploads a resume file for an application
- **THEN** the file is stored in that application's private folder, is shown as the sent resume, and the application appears in the pending work as needing a rescore

#### Scenario: Replacing an upload
- **WHEN** the user uploads a second file
- **THEN** the new file becomes the sent resume and the earlier file is kept

#### Scenario: Unsupported file
- **WHEN** the user uploads a file that is not a PDF or DOCX
- **THEN** the upload is rejected with an explanation

### Requirement: History
The system SHALL record every change to an application with its date, and SHALL
capture the facts known at the moment the user applied.

#### Scenario: Timeline
- **WHEN** the user opens an application's history
- **THEN** it lists when it was found, when documents were produced or uploaded, and each status change

#### Scenario: Snapshot at application time
- **WHEN** an application first reaches the applied stage
- **THEN** the score, resume kind, channel, and suggested salary current at that moment are preserved even if they change later

### Requirement: Ghosting is proposed, not assumed
The system SHALL flag applications without a response after the configured
number of days and SHALL change their status only on the user's confirmation.

#### Scenario: No response after the threshold
- **WHEN** an applied application has had no update for longer than the threshold
- **THEN** it is flagged with a proposal to mark it as ghosted and its status is unchanged
