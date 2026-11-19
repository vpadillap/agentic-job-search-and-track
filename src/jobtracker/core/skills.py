"""User-facing commands and their Spanish aliases.

Canonical skills live in `.claude/skills/<id>/` (committed). Aliases are thin
wrappers whose templates live in `i18n/skill-aliases/<language>/`; they are
copied next to the canonical skills only for users of that language and are
gitignored there.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from .paths import repo_root

SKILLS_DIR_ENV = "JOBTRACKER_SKILLS_DIR"
ALIAS_LANGUAGES = ("es",)

# id, example arguments, alias per language, alias example, one-line descriptions
COMMANDS: tuple[dict, ...] = (
    {
        "id": "setup", "example": "",
        "aliases": {"es": "configurar"}, "alias_examples": {"es": ""},
        "description": {
            "en": "First run: checks requirements, language, and builds your profile",
            "es": "Primera vez: revisa dependencias, idioma y arma tu perfil",
        },
    },
    {
        "id": "job-search", "example": "days=7",
        "aliases": {"es": "buscar-empleos"}, "alias_examples": {"es": "dias=7"},
        "description": {
            "en": "Searches the enabled job sites and updates the panel",
            "es": "Busca en los proveedores activos y actualiza el panel",
        },
    },
    {
        "id": "prepare-documents", "example": "pending",
        "aliases": {"es": "preparar-documentos"}, "alias_examples": {"es": "pendientes"},
        "description": {
            "en": "Resumes, cover letters, and form answers missing on tracked jobs (or ids=…)",
            "es": "CV, cartas y formularios que falten en vacantes seguidas (o ids=…)",
        },
    },
    {
        "id": "form-answers", "example": "ids=J0007",
        "aliases": {"es": "formulario"}, "alias_examples": {"es": "ids=J0007"},
        "description": {
            "en": "Answers to the application form of one or more jobs",
            "es": "Respuestas del formulario de una o varias vacantes",
        },
    },
    {
        "id": "analyze-results", "example": "",
        "aliases": {"es": "analizar-resultados"}, "alias_examples": {"es": ""},
        "description": {
            "en": "Reviews your results and proposes adjustments",
            "es": "Revisa resultados y propone ajustes",
        },
    },
    {
        "id": "new-season", "example": "",
        "aliases": {"es": "nueva-temporada"}, "alias_examples": {"es": ""},
        "description": {
            "en": "New profile; archives the previous campaign",
            "es": "Perfil nuevo; archiva lo anterior",
        },
    },
    {
        "id": "add-provider", "example": "",
        "aliases": {"es": "agregar-proveedor"}, "alias_examples": {"es": ""},
        "description": {
            "en": "Adds a job site for you; once proved, offers it to the project",
            "es": "Agrega un portal para ti; ya probado, ofrece aportarlo al proyecto",
        },
    },
    {
        "id": "update", "example": "",
        "aliases": {"es": "actualizar"}, "alias_examples": {"es": ""},
        "description": {
            "en": "Updates the project to the latest version; your data stays as it is",
            "es": "Actualiza el proyecto a la última versión; tus datos no se tocan",
        },
    },
    {
        "id": "panel", "example": "",
        "aliases": {}, "alias_examples": {},
        "description": {
            "en": "Starts or stops the local panel",
            "es": "Inicia o detiene el panel local",
        },
    },
)


def canonical_dir() -> Path:
    return repo_root() / ".claude" / "skills"


def install_dir() -> Path:
    override = os.environ.get(SKILLS_DIR_ENV)
    return Path(override) if override else canonical_dir()


def templates_dir(language: str) -> Path:
    return repo_root() / "i18n" / "skill-aliases" / language


def _is_built(command: dict) -> bool:
    return (canonical_dir() / command["id"] / "SKILL.md").is_file()


def _alias_installed(alias: str) -> bool:
    return (install_dir() / alias / "SKILL.md").is_file()


def sync(language: str) -> dict:
    """Install the aliases of `language` and remove those of every other language.

    Only folders named after a known alias are ever created or removed.
    """
    target = install_dir()
    installed, removed, not_built = [], [], []
    for command in COMMANDS:
        for alias_language, alias in command["aliases"].items():
            destination = target / alias
            if alias_language != language:
                if destination.is_dir():
                    shutil.rmtree(destination)
                    removed.append(alias)
                continue
            template = templates_dir(language) / alias / "SKILL.md"
            if not _is_built(command) or not template.is_file():
                if destination.is_dir():
                    shutil.rmtree(destination)
                    removed.append(alias)
                not_built.append(alias)
                continue
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(template, destination / "SKILL.md")
            installed.append(alias)
    return {"language": language, "installed": installed, "removed": removed,
            "not_available_yet": not_built}


def command_list(language: str) -> list[dict]:
    """Commands as they should be shown: by alias only where the alias really works."""
    result = []
    for command in COMMANDS:
        alias = command["aliases"].get(language)
        built = _is_built(command)
        # A built command is shown by its alias only where the alias is installed
        # and therefore works; a planned one by the name it will have.
        use_alias = bool(alias) and (_alias_installed(alias) or not built)
        name = alias if use_alias else command["id"]
        example = command["alias_examples"].get(language, "") if use_alias else command["example"]
        result.append({
            "id": command["id"],
            "command": f"/{name}",
            "example": f"/{name} {example}".strip(),
            "description": command["description"].get(language, command["description"]["en"]),
            "available": built,
        })
    return result
