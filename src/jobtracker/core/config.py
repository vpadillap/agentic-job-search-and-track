"""config.toml: the few settings needed before the database is opened."""
from __future__ import annotations

import tomllib
from pathlib import Path

from .errors import JobTrackerError

DEFAULTS: dict[str, object] = {"language": "en", "host": "127.0.0.1", "port": 8000}
LANGUAGES = ("en", "es")
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


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


def load(path: Path) -> dict[str, object]:
    config = dict(DEFAULTS)
    if path.is_file():
        with path.open("rb") as handle:
            stored = tomllib.load(handle)
        for key in DEFAULTS:
            if key in stored:
                config[key] = stored[key]
    return config


def save(path: Path, config: dict[str, object]) -> None:
    lines = ["# Job Tracker settings. Change them with: jobtracker config set <key> <value>"]
    for key in DEFAULTS:
        value = validate(key, config.get(key, DEFAULTS[key]))
        rendered = str(value) if isinstance(value, int) else f'"{value}"'
        lines.append(f"{key} = {rendered}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_value(path: Path, key: str, value: object) -> dict[str, object]:
    config = load(path)
    config[key] = validate(key, value)
    save(path, config)
    return config
