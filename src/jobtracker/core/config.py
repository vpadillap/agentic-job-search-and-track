"""config.toml: the few settings needed before the database is opened.

It also keeps the user's full name (`full_name`), which names downloaded
documents. The name is set only through `privacy.set_full_name`, which also
registers it for the privacy guard, so it is not one of the `config set` keys.
"""
from __future__ import annotations

import json
import tomllib
from pathlib import Path

from .errors import JobTrackerError

DEFAULTS: dict[str, object] = {"language": "en", "host": "127.0.0.1", "port": 8000}
LANGUAGES = ("en", "es")
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
FULL_NAME_KEY = "full_name"
FULL_NAME_MAX = 100


def validate(key: str, value: object) -> object:
    if key == "language":
        if value not in LANGUAGES:
            raise JobTrackerError("invalid_config", "language must be 'en' or 'es'")
        return value
    if key == "host":
        if value not in LOOPBACK_HOSTS:
            raise JobTrackerError("invalid_config", "host must be a loopback address")
        return value
    if key == "port":
        try:
            port = int(value)  # type: ignore[call-overload]
        except (TypeError, ValueError):
            port = -1
        if not 1024 <= port <= 65535:
            raise JobTrackerError("invalid_config", "port must be between 1024 and 65535")
        return port
    raise JobTrackerError("invalid_config", f"unknown setting '{key}'")


def _stored(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load(path: Path) -> dict[str, object]:
    config = dict(DEFAULTS)
    stored = _stored(path)
    for key in DEFAULTS:
        if key in stored:
            config[key] = stored[key]
    return config


def clean_full_name(value: object) -> str:
    """A full name as stored: spaces collapsed, 1-100 characters, no control characters."""
    if not isinstance(value, str):
        raise JobTrackerError("invalid_config", "the full name must be text")
    if any(ord(char) < 32 or 127 <= ord(char) < 160 for char in value.strip()):
        raise JobTrackerError("invalid_config", "the full name cannot contain control characters")
    name = " ".join(value.split())
    if not 1 <= len(name) <= FULL_NAME_MAX:
        raise JobTrackerError("invalid_config",
                              f"the full name must have 1 to {FULL_NAME_MAX} characters")
    return name


def load_full_name(path: Path) -> str | None:
    value = _stored(path).get(FULL_NAME_KEY)
    return value if isinstance(value, str) and value.strip() else None


def _write(path: Path, config: dict[str, object], full_name: str | None) -> None:
    lines = ["# Job Tracker settings. Change them with: jobtracker config set <key> <value>"]
    for key in DEFAULTS:
        value = validate(key, config.get(key, DEFAULTS[key]))
        rendered = str(value) if isinstance(value, int) else f'"{value}"'
        lines.append(f"{key} = {rendered}")
    if full_name:
        lines.append("# Your full name, for downloaded documents: jobtracker privacy name set")
        # A JSON string without control characters is a valid TOML basic string.
        lines.append(f"{FULL_NAME_KEY} = {json.dumps(full_name, ensure_ascii=False)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save(path: Path, config: dict[str, object]) -> None:
    _write(path, config, load_full_name(path))


def save_full_name(path: Path, name: object) -> str:
    clean = clean_full_name(name)
    _write(path, load(path), clean)
    return clean


def set_value(path: Path, key: str, value: object) -> dict[str, object]:
    config = load(path)
    config[key] = validate(key, value)
    save(path, config)
    return config
