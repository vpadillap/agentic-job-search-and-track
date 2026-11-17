"""Builders for throwaway resume files (fictional content only)."""
from __future__ import annotations

import zipfile
from pathlib import Path

RESUME_TEXT = """Marisol Quispe Tanaka
Senior Data Engineer

Summary
Data engineer with seven years of experience building batch and near real-time
pipelines on Google Cloud for retail and logistics companies.

Experience
Altamar Retail S.A. - Senior Data Engineer (2022 - present)
Designed and maintained Airflow and dbt pipelines on BigQuery.
Finlima S.A. - Data Engineer (2019 - 2022)
Modeled commercial and inventory data; mentored two junior engineers.

Skills
Python, SQL, Airflow, dbt, BigQuery, GCP, Pub/Sub

Languages
Spanish (native), English (B2)
"""


def make_docx(path: Path, text: str = RESUME_TEXT) -> Path:
    paragraphs = "".join(
        f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>" for line in text.splitlines()
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{paragraphs}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document)
    return path


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_text_pdf(path: Path, text: str = RESUME_TEXT) -> Path:
    """A minimal one-page PDF with real, extractable text."""
    lines = [line for line in text.splitlines()]
    content = ["BT", "/F1 10 Tf", "12 TL", "40 800 Td"]
    for line in lines:
        content.append(f"({_escape(line)}) Tj T*")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    return _write_pdf(path, objects)


def make_image_only_pdf(path: Path) -> Path:
    """A PDF page with no text at all, like a scan."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] >>",
    ]
    return _write_pdf(path, objects)


def _write_pdf(path: Path, objects: list[bytes]) -> Path:
    output = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(output)
    output += f"xref\n0 {len(objects) + 1}\n".encode()
    output += b"0000000000 65535 f \n"
    for offset in offsets:
        output += f"{offset:010d} 00000 n \n".encode()
    output += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode()
    path.write_bytes(bytes(output))
    return path
