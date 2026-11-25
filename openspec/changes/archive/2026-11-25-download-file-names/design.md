## Context

See proposal.md, "Why". Today `GET /api/applications/{job_id}/documents/{id}`
returns `FileResponse(path, filename=path.name)`, so the download name is the
stored name (`resume-proposed-v2.docx`, `cover-letter-v1.md`). Cover letters
are always stored as Markdown; tailored resumes as `.docx` or `.md`. The
user's name is only in `user-data/.private-terms`, as one unlabeled term
among email and phone, so it cannot be read back reliably. `core` must stay
standard-library only at import time; python-docx is a package dependency and
`core/docx_tools.py` already imports it lazily.

## Goals / Non-Goals

**Goals:**
- One place that decides a document's download name and format.
- A labeled, private record of the full name that also feeds the privacy guard.

**Non-Goals:**
- Faithful Markdown rendering beyond what cover letters and Markdown resumes
  use (headings, paragraphs, `-`/`•` list items, `**bold**`).
- Styling the converted document beyond python-docx's default template.

## Decisions

### 1. Rename at download, not on disk

The download endpoint sets the name; stored files keep the names in
`docs/workspace-layout.md`.
*Alternative:* store files as `<Full Name> - J0007 - v2.docx`. Rejected (and by
the owner): it changes the storage contract, needs a migration of existing
folders, and puts the name into every path the agent handles.

### 2. Full name in `config.toml` (`full_name`), set by `jt privacy name set`

`jt privacy name set "<full name>"` validates the name (1–100 characters
after collapsing spaces, no control characters), writes `full_name` to
`config.toml` (TOML-escaped), and calls `privacy.add_terms` with it in the
same command, so the name is never stored without being guarded. The result
reports `{"full_name_recorded": true, "private_term_added": …}` and never
echoes the name. `jt privacy name show` returns it for the agent when asked.
A changed name replaces `full_name`; the earlier term stays registered.
*Alternatives:* a field in the versioned profile (rejected: the profile is
per season and describes job needs, so a new season would have to copy it);
marking one line of `.private-terms` as the name (rejected: changes a file
format the guard script parses); a new DB table (rejected: heavier than one
setting, and `config.toml` already holds per-user settings read before the
database opens). After a full reset the name is asked again by `/setup`, like
the panel language; the private terms survive as today.

### 3. Download naming in `core/documents.py`

A function `download(conn, paths, job_id, document_id) -> {path, name, convert}`:
- kinds `resume_proposed` and `cover_letter` only; any other kind returns the
  stored name unchanged and no conversion;
- stem: `"<full_name> - <job_id>"`, or `"<job_id>"` without a name;
- cover letter suffix: `" - Carta de presentación"` when the document's
  `language` (falling back to the posting's `language`) is `es`, otherwise
  `" - Cover letter"`;
- characters `\/:*?"<>|` and control characters removed, spaces collapsed;
  accents kept (Starlette sends `filename*=UTF-8''…`);
- always `.docx`; `convert` is true when the stored file is `.md`.
*Alternative:* label in the panel language. Rejected: the file is uploaded to
the job site with the letter, so it follows the letter's language like the
letter itself.

### 4. Markdown to Word in `core/docx_tools.py`

`markdown_to_docx(text) -> bytes` with a lazy `import docx`: `#`–`###` →
headings, `-`/`*`/`•` lines → "List Bullet" paragraphs, `**x**` → bold runs,
blank lines separate paragraphs. The endpoint returns the bytes in a
`Response` with the Word media type and `Content-Disposition: attachment`
built with the same encoding Starlette uses for `FileResponse`.
*Alternatives:* pandoc (rejected: an extra system tool the user would have to
install); writing a `.docx` next to each letter when it is registered
(rejected: a second stored file per version to keep in sync, and existing
letters would not have one).

### 5. "Work mode not stated" flag recognized in `core`, hidden and no longer stored

Provider files ask the agent for the flag "work mode not stated" in the panel
language; the stored texts vary ("Modalidad no indicada", "Modalidad de trabajo
no indicada"). A function `is_work_mode_not_stated(flag)` in `core/search.py`
matches the whole flag, after casefolding, removing accents, and trimming
final punctuation, against: `(work mode|work-mode|modality|modalidad( de
trabajo)?) (not stated|not specified|no indicada|no especificada)`. Only a
whole-text match counts, so "Ciudad no indicada en detalle: dice Lima;
modalidad no indicada" stays.
- `import_postings` drops matching flags before storing.
- The read models that return `flags` to the panel (search results and
  posting detail) leave matching flags out, so stored ones disappear without a
  data migration.
- The panel adds a `warn` modifier to `.wm-chip` when `work_mode` is empty and
  stops using the class `empty` there: that class name collides with the
  page-level `.empty` rule in `app.css` (padding, column flex).
*Alternatives:* make the orange flag clickable and drop it when the user sets
a mode (rejected by the owner: two marks for one fact); change the provider
files to stop asking for the flag (rejected: providers change only in their
own change); a migration rewriting stored flags (rejected: hiding in the read
model covers old rows with no write, and the matching is the same).

### 6. Removing an application: the existing `untrack`, without its time window

`tracking.untrack` already deletes the application row (documents, tags, and
answers go with it through `ON DELETE CASCADE`), records an `untracked` event
on the posting, and never reuses job ids. A new `tracking.remove(conn, paths,
job_ids)` does the same by job id with no `UNDO_WINDOW` check and returns the
applications' folders (`applications.folder`); the toast's "Undo" keeps using
`untrack`. Once that transaction is committed, the caller (CLI or API) calls
`tracking.delete_folders(paths, folders)`, which deletes each folder only
after checking that the resolved path is a direct child of
`paths.applications` inside the private home and is not a symlink; a missing
folder is not an error. Applications of an earlier season stay read-only, so
they cannot be removed (the panel does not offer the action there). The database delete and the folder
delete happen in that order, so a failure while deleting files leaves no
application pointing at missing files. Panel:
`POST /api/applications/remove {job_ids}`; CLI: `jt applications remove
<job_id>…`. The confirmation is a small in-panel confirm menu (the same `Menu`
component the row actions use), never `window.confirm`.
*Alternatives:* a soft delete (`removed_at`) so a re-track brings everything
back (rejected: every application query, about 25 across `core`, would need
the filter, for a case the owner described as a mistaken click); keeping the
folder (rejected by the owner: a re-track gets a new job id and folder, so
nothing in the panel could reach the old files).

## Risks / Trade-offs

- [Every version downloads under the same name] → the browser adds "(1)";
  the current version is the one the panel offers first, which is the one the
  user needs.
- [Converted letter uses Word's default style] → acceptable for a letter; the
  user can restyle it. Resumes the agent writes are `.docx` already.
- [Name typed with odd characters] → sanitized for the file name only; the
  stored value is what the user confirmed.
- [An agent writes the not-stated flag in a wording the pattern misses] → it
  stays visible as today (no harm); the pattern covers both texts found in
  real use and their English forms, and tests pin them.
- [Deleting files cannot be undone] → the in-panel confirmation names the
  job id and says its documents are deleted; the path check keeps the delete
  inside that one application's folder.
- [Removal drops status history used by the learning loop] → it was a mistaken
  track; the posting's `untracked` event keeps the record.

## Migration Plan

No data migration. Users who already ran `/setup` get downloads named by the
job id until they record their name; the CHANGELOG entry's `Action` line asks
them to do it (`/setup`, privacy step). Rollback: revert the commit; the
download changes touch no stored file (only removing an application deletes
files, and only those of that application).
