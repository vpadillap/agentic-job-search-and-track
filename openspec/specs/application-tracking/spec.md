# application-tracking Specification

## Purpose
Defines the record kept for every posting the user decides to follow: its
status, tags, the facts of the application, the resume actually sent, and the
full history of what happened.

## Requirements

### Requirement: Tracked applications persist across searches
A tracked posting SHALL remain available with all its data regardless of later
searches, until the user removes it.

#### Scenario: New search after tracking
- **WHEN** a new search is run after a posting was tracked
- **THEN** the tracked application and its data are unchanged

### Requirement: User-defined statuses
The user SHALL be able to create a new status inline by giving it a name and
answering whether the application ended with it, and SHALL be able to rename
or retire custom statuses. Nothing else SHALL be asked. Built-in statuses
SHALL always exist and SHALL NOT be renamed or retired.

#### Scenario: Creating a status inline
- **WHEN** the user types the new status name "Position frozen" and says the application ended with it
- **THEN** the status is applied to that application, the application has ended, and the status is available for all others

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
capture the facts known at the moment the application first gets an applied
date.

#### Scenario: Timeline
- **WHEN** the user opens an application's history
- **THEN** it lists when it was found, when documents were produced or uploaded, and each status change by the full names of the statuses

#### Scenario: Snapshot at application time
- **WHEN** an application first gets an applied date, by a status change or entered by hand
- **THEN** the score, resume kind, channel, and suggested salary current at that moment are preserved even if they change later

### Requirement: Ghosting is proposed, not assumed
The system SHALL flag applications that have an applied date, have not ended,
and have had no status change for longer than the configured number of days,
and SHALL change their status only on the user's confirmation.

#### Scenario: No response after the threshold
- **WHEN** an applied application that has not ended has had no update for longer than the threshold
- **THEN** it is flagged with a proposal to mark it as ghosted and its status is unchanged

#### Scenario: Ended application
- **WHEN** an application with the custom ending status "Position frozen" has had no update for longer than the threshold
- **THEN** it is not flagged

### Requirement: One status that says whether the application ended
Every application SHALL have exactly one status. Statuses SHALL form a single
list with no grouping, and every status SHALL say whether an application with
that status has ended. The built-in statuses Accepted, Rejected, Ghosted,
Offer declined, No economic alignment, and Withdrawn SHALL end an application;
New, Applied, Interview, and Offer SHALL NOT.

#### Scenario: Changing status
- **WHEN** the user changes an application from Applied to Interview
- **THEN** the application's status is Interview, it has not ended, and the change is recorded in its history with the date and both status names

#### Scenario: Ending status
- **WHEN** the user changes an application to Rejected
- **THEN** the application has ended

#### Scenario: No stage anywhere
- **WHEN** the agent or the panel reads an application or the list of statuses
- **THEN** no stage or other grouping of statuses is given

### Requirement: Applied date
An application SHALL count as applied exactly when it has an applied date. The
system SHALL fill in today's date when an application without one gets one of
the built-in statuses Applied, Interview, Offer, Accepted, Rejected, Ghosted,
Offer declined, or No economic alignment. New, Withdrawn, and custom statuses
SHALL NOT fill it in. The user SHALL be able to set, change, or clear the
applied date at any time.

#### Scenario: Marking as applied
- **WHEN** the user changes a new application to Applied and it has no applied date
- **THEN** its applied date is today

#### Scenario: Custom status before applying
- **WHEN** the user gives a new application the custom status "Waiting for a referral"
- **THEN** it has no applied date and still counts as not applied

#### Scenario: Date entered by hand
- **WHEN** the user enters an applied date for an application with a custom status
- **THEN** the application counts as applied from then on

### Requirement: Statuses for the agent
The agent SHALL receive, for every application, the full name of its status
(with the stable key of built-in statuses), whether the application ended, and
every status change with the full names of both statuses and its date.

#### Scenario: Custom status in the agent's data
- **WHEN** an application went from Applied to the custom status "Technical test sent" and then to Interview
- **THEN** the agent's data names the current status "Interview", says the application has not ended, and lists both changes with "Applied", "Technical test sent", "Interview", and their dates
