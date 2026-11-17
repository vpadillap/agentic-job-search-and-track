## Purpose

Defines the proposed answers to a posting's application-form questions, so the
user can apply by copying reviewed answers instead of writing each from
scratch.

## ADDED Requirements

### Requirement: An answer for each captured question
For applications whose form questions were captured, the agent SHALL propose an
answer to each question, in the posting's language.

#### Scenario: Four questions
- **WHEN** answers are prepared for an application with four captured questions
- **THEN** each of the four questions has a proposed answer

#### Scenario: No captured questions
- **WHEN** answers are requested for an application without captured questions
- **THEN** the agent reports that there is no form to answer

### Requirement: Answers are grounded
An answer SHALL be based on the user's resume, profile, and stored data, and a
question that cannot be answered from them SHALL be left for the user with a
note of what is needed.

#### Scenario: Unknown fact
- **WHEN** a question asks for information absent from the user's data
- **THEN** the answer is marked as needing the user's input and no value is invented

#### Scenario: Salary expectation
- **WHEN** a question asks for salary expectation and a suggestion with evidence exists
- **THEN** the answer uses that suggestion and states that it is based on it

#### Scenario: Salary expectation without data
- **WHEN** a question asks for salary expectation and no reliable salary data exists
- **THEN** the answer is left for the user

### Requirement: User edits are kept
The user SHALL be able to edit any answer in the panel, and the agent SHALL NOT
overwrite an answer the user edited.

#### Scenario: Regenerating after an edit
- **WHEN** answers are regenerated for an application where the user edited one
- **THEN** the edited answer is unchanged and the new proposal is offered as an alternative

### Requirement: Answers are easy to use
Each answer SHALL be displayed with its question and its origin, and SHALL be
copyable individually.

#### Scenario: Edited answer
- **WHEN** the user has edited an answer
- **THEN** it is labeled as edited by the user

#### Scenario: Copying an answer
- **WHEN** the user activates copy on a form answer in the Applications board
- **THEN** the answer text is placed on the clipboard
