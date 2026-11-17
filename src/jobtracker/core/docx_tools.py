"""Tailoring a DOCX resume without touching its design.

`tailor` copies the base resume and edits text in place: each replacement keeps
the formatting of the run where the replaced text starts, and paragraphs can be
reordered (bullet order). Layout, styles, and everything else stay as they
were. Edits apply all or nothing.

`layout_check` compares the paragraph count and text length with the base.
The result is delivered as a DOCX: the user opens it in Word, adjusts it, and
saves it as PDF if an application asks for one.
"""
from __future__ import annotations

from pathlib import Path

from .errors import JobTrackerError


def _docx():
    try:
        import docx
        from docx.oxml.ns import qn
    except ImportError as error:
        raise JobTrackerError(
            "missing_dependency",
            "Editing Word files needs the 'python-docx' package. Install the project's "
            "dependencies (`uv sync`, or `pip install -e .` in a virtual environment).",
        ) from error
    return docx, qn


def _open(path: Path):
    docx, _ = _docx()
    try:
        return docx.Document(str(path))
    except Exception as error:  # python-docx raises several unrelated types
        raise JobTrackerError("unreadable_resume",
                              f"'{path.name}' could not be read as a Word document") from error


def _paragraphs(document):
    """Every paragraph in the body, tables included, in document order."""
    _, qn = _docx()
    return list(document.element.body.iter(qn("w:p")))


def _runs(paragraph) -> list:
    _, qn = _docx()
    return [r for r in paragraph.iter(qn("w:r"))]


def _run_text(run) -> str:
    _, qn = _docx()
    parts = []
    for node in run:
        if node.tag == qn("w:t"):
            parts.append(node.text or "")
        elif node.tag == qn("w:tab"):
            parts.append("\t")
        elif node.tag in (qn("w:br"), qn("w:cr")):
            parts.append("\n")
    return "".join(parts)


def _set_run_text(run, text: str) -> None:
    """Replace a run's text; its formatting (w:rPr) is kept."""
    _, qn = _docx()
    for node in list(run):
        if node.tag in (qn("w:t"), qn("w:tab"), qn("w:br"), qn("w:cr")):
            run.remove(node)
    if text:
        element = run.makeelement(qn("w:t"), {})
        element.text = text
        element.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        run.append(element)


def paragraph_text(paragraph) -> str:
    return "".join(_run_text(r) for r in _runs(paragraph))


def text_of(path: Path) -> str:
    document = _open(path)
    return "\n".join(t for t in (paragraph_text(p) for p in _paragraphs(document)) if t.strip())


def _replace_in_paragraph(paragraph, find: str, replace: str) -> None:
    runs = _runs(paragraph)
    texts = [_run_text(r) for r in runs]
    full = "".join(texts)
    start = full.index(find)
    end = start + len(find)
    offset = 0
    first = last = None
    for index, text in enumerate(texts):
        run_start, run_end = offset, offset + len(text)
        if first is None and run_end > start:
            first = (index, start - run_start)
        if run_end >= end:
            last = (index, end - run_start)
            break
        offset = run_end
    assert first is not None and last is not None
    first_index, first_cut = first
    last_index, last_cut = last
    if first_index == last_index:
        text = texts[first_index]
        _set_run_text(runs[first_index], text[:first_cut] + replace + text[last_cut:])
        return
    _set_run_text(runs[first_index], texts[first_index][:first_cut] + replace)
    for index in range(first_index + 1, last_index):
        _set_run_text(runs[index], "")
    _set_run_text(runs[last_index], texts[last_index][last_cut:])


def _matches(paragraphs, needle: str) -> list:
    return [p for p in paragraphs if needle in paragraph_text(p)]


def _single(paragraphs, needle: str, index: int, field: str):
    found = _matches(paragraphs, needle)
    if len(found) != 1:
        raise JobTrackerError(
            "edit_not_applied",
            f"edit {index}: '{needle[:60]}' must appear in exactly one paragraph "
            f"({len(found)} found); quote more of the text to make it unique",
            index=index, field=field, found=len(found),
        )
    return found[0]


def tailor(base: Path, target: Path, edits: object) -> dict:
    """Write `target` as a copy of `base` with text edits. All edits apply or none.

    Edits: {"find": "...", "replace": "..."} replaces text inside one paragraph;
    {"move": "...", "before": "..."} moves the paragraph containing `move` in
    front of the paragraph containing `before` (reordering bullets).
    """
    if not isinstance(edits, list) or not edits:
        raise JobTrackerError("invalid_edit", "expected a non-empty list of edits")
    if base.suffix.lower() != ".docx":
        raise JobTrackerError(
            "not_editable",
            "Only a DOCX resume can be tailored without changing its design. Ask the user for "
            "the editable version; rebuilding from text is a layout change that needs consent.",
        )
    if target.exists():
        raise JobTrackerError("exists", f"'{target.name}' already exists; versions are never "
                                        "overwritten")
    document = _open(base)
    paragraphs = _paragraphs(document)
    applied = []
    for index, edit in enumerate(edits):
        if not isinstance(edit, dict):
            raise JobTrackerError("invalid_edit", f"edit {index}: must be an object", index=index)
        if "find" in edit:
            find, replace = edit.get("find"), edit.get("replace")
            if not isinstance(find, str) or not find or not isinstance(replace, str):
                raise JobTrackerError("invalid_edit",
                                      f"edit {index}: 'find' and 'replace' must be text",
                                      index=index)
            paragraph = _single(paragraphs, find, index, "find")
            _replace_in_paragraph(paragraph, find, replace)
            applied.append({"edit": index, "kind": "replace"})
        elif "move" in edit:
            move, before = edit.get("move"), edit.get("before")
            if not isinstance(move, str) or not move or not isinstance(before, str) or not before:
                raise JobTrackerError("invalid_edit",
                                      f"edit {index}: 'move' and 'before' must be text",
                                      index=index)
            moving = _single(paragraphs, move, index, "move")
            anchor = _single(paragraphs, before, index, "before")
            if moving is not anchor:
                anchor.addprevious(moving)
                paragraphs = _paragraphs(document)
            applied.append({"edit": index, "kind": "move"})
        else:
            raise JobTrackerError("invalid_edit",
                                  f"edit {index}: use find/replace or move/before", index=index)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".partial")
    try:
        document.save(str(partial))
        partial.replace(target)
    finally:
        if partial.exists():
            partial.unlink()
    return {"file": str(target), "edits": applied}


def layout_check(base: Path, proposed: Path) -> dict:
    """Does the tailored resume keep the base's shape? Paragraphs and text length."""
    base_doc, proposed_doc = _open(base), _open(proposed)
    base_paragraphs = [paragraph_text(p) for p in _paragraphs(base_doc)]
    new_paragraphs = [paragraph_text(p) for p in _paragraphs(proposed_doc)]
    base_chars = sum(len(t) for t in base_paragraphs)
    new_chars = sum(len(t) for t in new_paragraphs)
    return {
        "paragraphs": {"base": len(base_paragraphs), "proposed": len(new_paragraphs)},
        "characters": {"base": base_chars, "proposed": new_chars,
                       "change_pct": round((new_chars - base_chars) * 100 / base_chars, 1)
                       if base_chars else None},
        "same_shape": len(base_paragraphs) == len(new_paragraphs),
    }
