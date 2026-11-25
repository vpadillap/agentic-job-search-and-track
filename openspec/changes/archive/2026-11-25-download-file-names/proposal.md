## Why

Three small frictions in the panel:

- Every tailored resume the agent writes is stored as `resume-proposed-v<N>.docx`
  and every cover letter as `cover-letter-v<N>.md`, and the panel downloads them
  under those same names. After downloading the documents of a few applications
  the user cannot tell which file belongs to which job, and the cover letter
  arrives as Markdown, which job sites do not take.
- A posting without a stated work mode shows two marks: an orange "work mode
  not stated" tag under the title, which cannot be clicked, and a dashed
  chip in the conditions that opens the work-mode editor. Users click the
  orange one, nothing happens, and it stays even after they set the mode.
- A posting tracked by mistake can only be untracked from the "Undo" of the
  toast, within 10 minutes of tracking it. After that it stays in
  Applications for good.

## What Changes

- The panel downloads a tailored resume as `<Full Name> - <Job id>.docx`
  (for example `Marisol Quispe Tanaka - J0007.docx`).
- The panel downloads a cover letter as a Word document named
  `<Full Name> - <Job id> - Cover letter.docx`, or
  `... - Carta de presentación.docx` when the letter is in Spanish.
- A tailored resume stored as Markdown also downloads as `.docx`.
- `/setup` records the user's full name once, in its privacy step, through one
  new command that stores it in the private home and registers it as a
  private term for the privacy guard in the same step. It can be changed later
  with the same command.
- Without a recorded name, downloads are named by the job id alone
  (`J0007.docx`, `J0007 - Cover letter.docx`).
- Files on disk keep their current names and versions; only the download name
  and format change.
- A posting without a work mode shows one mark only: the work-mode chip,
  styled as a warning and editable by click. A flag that only says the work
  mode is not stated is no longer shown (nor stored by later imports); flags
  that say more stay. Once the user sets a mode, the chip looks like any other.
- Applications gets a "Remove from tracking" action, available at any time
  and confirmed in the panel: the application leaves Applications, the
  posting goes back to the search results as untracked, its job id is never
  given to another posting, and its folder (tailored resumes, cover letters,
  uploaded sent resume, posting text) is deleted, since nothing in the panel
  could reach it any more.

## Non-goals

- Renaming or migrating stored files; `docs/workspace-layout.md` names stay.
- Changing the uploaded `resume-sent` file or the posting text (they download
  as before).
- Changing how the agent writes or registers documents, or the cover letter's
  storage format (it stays Markdown on disk; "copy text" keeps working).
- Converting to PDF.
- Reading LinkedIn's work-mode chip: it is only shown to signed-in members
  (checked logged out on 2026-11-25), so the LinkedIn reader and provider file
  do not change.
- Changing provider files or their instructions about flags.
- Bringing a removed
  application's status, tags, and answers back if the posting is tracked
  again (it starts as a new application with a new job id).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `applications-board`: new requirements for download names built from the
  user's full name and the job id, Word downloads of Markdown documents, and
  removing an application from tracking.
- `application-tracking`: a new requirement states what removing an
  application deletes and that its job id is never reused.
- `search-results-board`: a new requirement shows a missing work mode as one
  editable warning chip and stops showing the redundant flag.
- `setup-onboarding`: "Privacy registration" also records the user's full
  name, kept in the private home and registered as a private term.

## Impact

- `src/jobtracker/web/app.py`: the document download endpoint; a remove
  endpoint for applications.
- `src/jobtracker/core/`: download naming and Markdown-to-Word conversion
  (python-docx is already a dependency, imported lazily as in `docx_tools`);
  storing the full name (`config.toml` key and `privacy` module); recognizing
  the "work mode not stated" flag (import and read models); removing a tracked
  application (`tracking`).
- `src/jobtracker/cli/main.py`: `jt privacy name set|show`, `jt applications
  remove`.
- `src/jobtracker/web/static/`: work-mode chip style, flags list, remove
  action with in-panel confirmation, en/es texts.
- `.claude/skills/setup/SKILL.md`, its Spanish alias template,
  `docs/workspace-layout.md`, README (en/es), `CHANGELOG.md`.
- Tests under `tests/` with the fictional persona.
