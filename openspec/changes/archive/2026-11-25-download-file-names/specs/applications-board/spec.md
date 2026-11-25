## ADDED Requirements

### Requirement: Download names of agent-made documents
A tailored resume and a cover letter SHALL download as Word documents named
after the user's full name and the job id: `<Full Name> - <Job id>.docx` for a
resume, and `<Full Name> - <Job id> - Cover letter.docx` (`Carta de
presentación` when the letter is in Spanish) for a cover letter. Every version
downloads under the same name. Without a recorded full name the name starts
with the job id. Characters file systems do not allow are left out; accents
are kept.

#### Scenario: Downloading a tailored resume
- **WHEN** the recorded full name is "Marisol Quispe Tanaka" and the user downloads the tailored resume of J0007
- **THEN** the file arrives as `Marisol Quispe Tanaka - J0007.docx` and the stored file keeps its versioned name

#### Scenario: Downloading a cover letter
- **WHEN** the user downloads the cover letter of J0007, which is in Spanish
- **THEN** the file arrives as `Marisol Quispe Tanaka - J0007 - Carta de presentación.docx`

#### Scenario: No recorded full name
- **WHEN** no full name is recorded and the user downloads the tailored resume of J0007
- **THEN** the file arrives as `J0007.docx`

### Requirement: Markdown documents download as Word
A tailored resume or cover letter stored as Markdown SHALL be converted to a
Word document for the download, keeping its headings, paragraphs, list items,
and bold text. The stored file, the uploaded sent resume, and the posting text
SHALL NOT be renamed or converted.

#### Scenario: Cover letter in Word
- **WHEN** the user downloads a cover letter stored as Markdown
- **THEN** it arrives as a Word document with the letter's headings, paragraphs, and list items, and the stored Markdown file is unchanged

#### Scenario: Resume stored as Markdown
- **WHEN** the tailored resume of J0012 is stored as Markdown and the user downloads it
- **THEN** it arrives as `Marisol Quispe Tanaka - J0012.docx` with the same headings, paragraphs, and list items

#### Scenario: Sent resume keeps its name
- **WHEN** the user downloads the resume they uploaded as sent for J0007
- **THEN** it arrives under its stored name and format, as before

### Requirement: Remove an application from tracking
Each application SHALL offer "Remove from tracking" at any time, whatever its
status. The action SHALL ask for confirmation inside the panel (not a browser
dialog), naming the job id and saying that its data and documents are deleted.
Once confirmed, the application SHALL leave the board immediately and its
posting SHALL return to the search results as untracked.

#### Scenario: Removing an application tracked by mistake
- **WHEN** the user removes J0007 from tracking and confirms
- **THEN** J0007 no longer appears in Applications, and its posting appears in the search results of its run as untracked with "Track" available

#### Scenario: Cancelling the removal
- **WHEN** the user opens "Remove from tracking" on J0007 and cancels
- **THEN** J0007 stays in Applications unchanged

#### Scenario: Removing an application already marked applied
- **WHEN** the user removes J0009, whose status is Applied, and confirms
- **THEN** J0009 is removed in the same way
