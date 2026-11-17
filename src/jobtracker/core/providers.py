"""Provider instruction files (providers/<id>.md): front matter only, for now."""
from __future__ import annotations

import re
from pathlib import Path

from .paths import repo_root

SKIPPED_FILES = {"readme.md", "_template.md"}


def providers_dir() -> Path:
    return repo_root() / "providers"


def _parse_value(raw: str) -> object:
    value = raw.split(" #", 1)[0].strip()
    if value.startswith("[") and value.endswith("]"):
        return [item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip()]
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value.strip("'\"")


def parse_front_matter(text: str) -> dict[str, object]:
    """The flat `key: value` block between the leading '---' lines."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    data: dict[str, object] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if match:
            data[match.group(1)] = _parse_value(match.group(2))
    return data


def list_providers(directory: Path | None = None) -> list[dict[str, object]]:
    directory = directory or providers_dir()
    found = []
    if not directory.is_dir():
        return found
    for path in sorted(directory.glob("*.md")):
        if path.name.lower() in SKIPPED_FILES:
            continue
        meta = parse_front_matter(path.read_text(encoding="utf-8"))
        meta.setdefault("id", path.stem)
        meta["file"] = path.name
        found.append(meta)
    return found
