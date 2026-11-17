"""Base resume intake: keep the file exactly as given, plus its extracted text."""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .db import bump_changes, now_iso
from .errors import JobTrackerError
from .paths import Paths

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".md", ".txt")
MIN_TEXT_CHARACTERS = 200
RESCORE_SETTING = "profile.rescore_since"
_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            document = archive.read("word/document.xml")
        if b"<!DOCTYPE" in document or b"<!ENTITY" in document:
            raise ElementTree.ParseError("entity declarations are not allowed")
        root = ElementTree.fromstring(document)
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise JobTrackerError(
            "unreadable_resume", f"'{path.name}' is not a valid Word document"
        ) from error
    paragraphs = []
    for paragraph in root.iter(f"{_WORD_NS}p"):
        parts = []
        for node in paragraph.iter():
            if node.tag == f"{_WORD_NS}t" and node.text:
                parts.append(node.text)
            elif node.tag in (f"{_WORD_NS}tab", f"{_WORD_NS}br"):
                parts.append("\t" if node.tag.endswith("tab") else "\n")
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
        from pypdf.errors import PyPdfError
    except ImportError as error:
        raise JobTrackerError(
            "missing_dependency",
            "Reading PDF files needs the 'pypdf' package. Install the project's dependencies "
            "(`uv sync`, or `pip install -e .` in a virtual environment).",
        ) from error
    try:
        reader = PdfReader(str(path))
        return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
    except (PyPdfError, OSError, ValueError) as error:
        raise JobTrackerError(
            "unreadable_resume", f"'{path.name}' could not be read as a PDF"
        ) from error


def extract_text(path: Path) -> str:
    extension = path.suffix.lower()
    if extension == ".pdf":
        return _pdf_text(path)
    if extension == ".docx":
        return _docx_text(path)
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _visible_characters(text: str) -> int:
    return sum(1 for character in text if not character.isspace())


LANGUAGE_PATTERN = re.compile(r"^[a-z]{2}$")


def _language(code: str | None) -> str | None:
    if code is None:
        return None
    clean = code.strip().lower()
    if not LANGUAGE_PATTERN.match(clean):
        raise JobTrackerError("invalid_language",
                              f"'{code}' is not a 2-letter language code such as en or es")
    return clean


def _dict(row: sqlite3.Row, paths: Paths) -> dict:
    return {
        "id": row["id"],
        "version": row["version"],
        "language": row["language"],
        "current": bool(row["is_current"]),
        "path": str(paths.profile / row["file_name"]),
        "text_path": str(paths.profile / row["text_name"]),
        "original_name": row["original_name"],
        "characters": row["characters"],
        "text_source": row["text_source"],
        "translated_from": row["translated_from"],
        "imported_at": row["imported_at"],
    }


def by_id(conn: sqlite3.Connection, paths: Paths, resume_id: int) -> dict:
    row = conn.execute("SELECT * FROM base_resumes WHERE id = ?", (resume_id,)).fetchone()
    if row is None:
        raise JobTrackerError("not_found", f"There is no base resume {resume_id}")
    return _dict(row, paths)


def list_current(conn: sqlite3.Connection, paths: Paths) -> list[dict]:
    """The current base resume of every language."""
    return [_dict(r, paths) for r in conn.execute(
        "SELECT * FROM base_resumes WHERE is_current = 1 ORDER BY COALESCE(language, ''), id")]


def list_all(conn: sqlite3.Connection, paths: Paths) -> list[dict]:
    return [_dict(r, paths) for r in conn.execute(
        "SELECT * FROM base_resumes ORDER BY is_current DESC, COALESCE(language, ''),"
        " version DESC")]


def _current_in(conn: sqlite3.Connection, language: str | None) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM base_resumes WHERE is_current = 1 AND COALESCE(language, '') = ?",
        (language or "",)).fetchone()


def choose_row(conn: sqlite3.Connection, posting_language: str | None,
               override: str | None = None) -> sqlite3.Row:
    """The base resume for a posting: the user's resume in the posting's language.

    Each resume is the source for its own language; there is no fallback to
    another language. A resume imported before languages were recorded is used
    while it is the user's only one.
    """
    if override is not None:
        row = _current_in(conn, _language(override))
        if row is None:
            raise JobTrackerError("no_resume_for_language",
                                  f"There is no base resume in '{override}'",
                                  language=override)
        return row
    rows = conn.execute("SELECT * FROM base_resumes WHERE is_current = 1").fetchall()
    if not rows:
        raise JobTrackerError("no_base_resume", "There is no base resume. Run /setup.")
    wanted = (posting_language or "").strip().lower() or None
    if wanted is not None:
        row = _current_in(conn, wanted)
        if row is not None:
            return row
        if len(rows) == 1 and rows[0]["language"] is None:
            return rows[0]
        raise JobTrackerError(
            "no_resume_for_language",
            f"The user has no resume in '{wanted}'. Ask them for one, or offer to translate "
            f"one of theirs into '{wanted}' as a draft they review "
            f"(`resume translate --from <code> --to {wanted}`). Nothing was stored.",
            language=wanted,
        )
    if len(rows) == 1:
        return rows[0]
    raise JobTrackerError(
        "posting_language_unknown",
        "The posting's language is not recorded and the user has resumes in several "
        "languages. Read the posting and pass --base <code> for its language.",
    )


def choose_base(conn: sqlite3.Connection, paths: Paths, posting_language: str | None,
                override: str | None = None) -> dict:
    row = choose_row(conn, posting_language, override)
    base = _dict(row, paths)
    wanted = (posting_language or "").strip().lower() or None
    translate = None if not wanted or not base["language"] else wanted != base["language"]
    return {**base, "translate": translate}


def set_language(conn: sqlite3.Connection, paths: Paths, language: str) -> dict:
    """State the language of the base resume imported before languages were recorded."""
    code = _language(language)
    row = _current_in(conn, None)
    if row is None:
        raise JobTrackerError("not_found",
                              "There is no base resume without a language to set")
    if _current_in(conn, code) is not None:
        raise JobTrackerError(
            "language_taken",
            f"There is already a base resume in '{code}'. Import the newer one with "
            f"`resume import <file> --language {code}` instead.",
        )
    conn.execute("UPDATE base_resumes SET language = ? WHERE id = ?", (code, row["id"]))
    bump_changes(conn)
    return _dict(conn.execute("SELECT * FROM base_resumes WHERE id = ?",
                              (row["id"],)).fetchone(), paths)


def import_resume(
    conn: sqlite3.Connection, paths: Paths, source: Path, text_file: Path | None = None,
    language: str | None = None, translated_from: str | None = None,
) -> dict:
    """Store `source` as the base resume in `language`. The previous base resume in
    that language is kept under a versioned name; other languages are untouched.

    `text_file` supplies the text when it cannot be extracted (scanned resume
    read visually and confirmed by the user).
    """
    language = _language(language)
    translated_from = _language(translated_from)
    if translated_from is not None and translated_from == language:
        raise JobTrackerError("invalid_language",
                              "a resume cannot be translated into its own language")
    if not source.is_file():
        raise JobTrackerError("not_found", f"There is no file at '{source}'")
    extension = source.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise JobTrackerError(
            "unsupported_resume",
            f"'{extension or source.name}' is not supported. Use PDF, DOCX, Markdown, or text.",
        )
    if language is not None and _current_in(conn, None) is not None \
            and _current_in(conn, language) is None:
        raise JobTrackerError(
            "language_unknown",
            "The current base resume has no language yet. Ask the user which language it is "
            "in and run `resume language <code>` first, so a new file does not end up "
            "beside it as a second copy of the same language. Nothing was stored.",
        )

    if text_file is not None:
        if not text_file.is_file():
            raise JobTrackerError("not_found", f"There is no file at '{text_file}'")
        text = text_file.read_text(encoding="utf-8", errors="replace").strip()
        text_source = "provided"
    else:
        text = extract_text(source)
        text_source = "extracted"
    characters = _visible_characters(text)
    if characters < MIN_TEXT_CHARACTERS:
        raise JobTrackerError(
            "no_text_extracted",
            f"Only {characters} characters of text could be read from '{source.name}'. It is "
            "probably a scanned image. Ask for a text-based PDF or DOCX, or read it visually, "
            "confirm the text with the user, and import again with --text <file>. "
            "Nothing was stored.",
            characters=characters,
        )

    paths.profile.mkdir(parents=True, exist_ok=True)
    previous = _current_in(conn, language)
    latest = conn.execute("SELECT COALESCE(MAX(version), 0) FROM base_resumes").fetchone()[0]
    version = latest + 1

    # Read everything before touching the profile folder: the source may be
    # the current base resume itself.
    payload = source.read_bytes()

    if previous is not None:
        old_version = previous["version"]
        renamed: dict[str, str] = {}
        for column in ("file_name", "text_name"):
            name = previous[column]
            if name in renamed:
                continue
            old_path = paths.profile / name
            stem, suffix = Path(name).stem, Path(name).suffix
            new_name = f"{stem}-v{old_version}{suffix}"
            if old_path.exists():
                shutil.move(str(old_path), str(paths.profile / new_name))
            renamed[name] = new_name
        conn.execute(
            "UPDATE base_resumes SET is_current = 0, file_name = ?, text_name = ? WHERE id = ?",
            (renamed[previous["file_name"]], renamed[previous["text_name"]], previous["id"]),
        )

    stem = f"resume-base-{language}" if language else "resume-base"
    file_name = f"{stem}{extension}"
    text_name = f"{stem}.md"
    (paths.profile / file_name).write_bytes(payload)
    if file_name != text_name:
        (paths.profile / text_name).write_text(text + "\n", encoding="utf-8")

    now = now_iso()
    cursor = conn.execute(
        "INSERT INTO base_resumes (version, file_name, text_name, original_name, characters,"
        " text_source, imported_at, is_current, language, translated_from)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
        (version, file_name, text_name, source.name, characters, text_source, now, language,
         translated_from),
    )
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
        " VALUES ('base_resume', ?, 'imported', ?, ?)",
        (str(version), json.dumps({"replaced": previous["version"] if previous else None,
                                   "language": language,
                                   "translated_from": translated_from}), now),
    )
    # Postings in this language were judged against the replaced version.
    rescore = previous is not None
    if rescore:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (RESCORE_SETTING, now),
        )
    bump_changes(conn)

    result = by_id(conn, paths, cursor.lastrowid)
    return {
        **result,
        "words": len(text.split()),
        "replaced_version": previous["version"] if previous else None,
        "rescore_needed": rescore,
    }


def rescore_since(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (RESCORE_SETTING,)).fetchone()
    return row["value"] if row else None


def translate_draft(conn: sqlite3.Connection, paths: Paths, source_language: str,
                    target_language: str, edits: object) -> dict:
    """Write a translated copy of the user's resume in `source_language`, same design,
    for the user to review in Word. It is not a base resume until imported."""
    from . import docx_tools
    from .paths import next_version_path

    source_language = _language(source_language)
    target_language = _language(target_language)
    if source_language == target_language:
        raise JobTrackerError("invalid_language", "translate into a different language")
    row = _current_in(conn, source_language)
    if row is None:
        raise JobTrackerError("no_resume_for_language",
                              f"There is no base resume in '{source_language}'",
                              language=source_language)
    source = paths.profile / row["file_name"]
    target = next_version_path(paths.profile, f"resume-draft-{target_language}", "docx")
    result = docx_tools.tailor(source, target, edits)
    return {
        "file": str(target), "file_name": target.name,
        "from": {"language": source_language, "version": row["version"]},
        "to": target_language, "edits": result["edits"],
        "layout": docx_tools.layout_check(source, target),
        "next": f"Ask the user to open {target.name} in Word, adjust it, and confirm; then "
                f"`resume import <file> --language {target_language} "
                f"--translated-from {source_language}`.",
    }
