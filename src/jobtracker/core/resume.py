"""Base resume intake: keep the file exactly as given, plus its extracted text."""
from __future__ import annotations

import json
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


def current(conn: sqlite3.Connection, paths: Paths) -> dict | None:
    row = conn.execute("SELECT * FROM base_resumes WHERE is_current = 1").fetchone()
    if row is None:
        return None
    return {
        "version": row["version"],
        "path": str(paths.profile / row["file_name"]),
        "text_path": str(paths.profile / row["text_name"]),
        "original_name": row["original_name"],
        "characters": row["characters"],
        "text_source": row["text_source"],
        "imported_at": row["imported_at"],
    }


def import_resume(
    conn: sqlite3.Connection, paths: Paths, source: Path, text_file: Path | None = None
) -> dict:
    """Store `source` as the base resume. The previous one is kept under a versioned name.

    `text_file` supplies the text when it cannot be extracted (scanned resume
    read visually and confirmed by the user).
    """
    if not source.is_file():
        raise JobTrackerError("not_found", f"There is no file at '{source}'")
    extension = source.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise JobTrackerError(
            "unsupported_resume",
            f"'{extension or source.name}' is not supported. Use PDF, DOCX, Markdown, or text.",
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
    previous = conn.execute("SELECT * FROM base_resumes WHERE is_current = 1").fetchone()
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

    file_name = f"resume-base{extension}"
    text_name = "resume-base.md"
    (paths.profile / file_name).write_bytes(payload)
    if file_name != text_name:
        (paths.profile / text_name).write_text(text + "\n", encoding="utf-8")

    now = now_iso()
    conn.execute(
        "INSERT INTO base_resumes (version, file_name, text_name, original_name, characters,"
        " text_source, imported_at, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
        (version, file_name, text_name, source.name, characters, text_source, now),
    )
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
        " VALUES ('base_resume', ?, 'imported', ?, ?)",
        (str(version), json.dumps({"replaced": previous["version"] if previous else None}), now),
    )
    rescore = previous is not None
    if rescore:
        # Open postings were judged against the old resume; they need a new score.
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (RESCORE_SETTING, now),
        )
    bump_changes(conn)

    result = current(conn, paths)
    assert result is not None
    return {
        **result,
        "words": len(text.split()),
        "replaced_version": previous["version"] if previous else None,
        "rescore_needed": rescore,
    }


def rescore_since(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (RESCORE_SETTING,)).fetchone()
    return row["value"] if row else None
