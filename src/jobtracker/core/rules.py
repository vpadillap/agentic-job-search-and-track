"""Rules: system rules, user preferences, and learned lessons in one list."""
from __future__ import annotations

import json
import sqlite3

from .db import bump_changes, now_iso
from .errors import JobTrackerError

ORIGINS = ("system", "user", "learned")
STATUSES = ("proposed", "active", "ignored", "reverted")
AREAS = (
    "general", "search", "score", "resume", "cover_letter", "form",
    "salary", "statuses", "providers", "privacy",
)

# Shipped with the project and always active. Their text is owned by the code:
# it is refreshed on every initialization and shown in the panel language.
SYSTEM_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "salary_evidence",
        "salary",
        "Suggest a salary only with 2 or more comparable, linked sources (same country and "
        "level, matching work mode, similar industry and company size). Never extrapolate; "
        "otherwise record that there is no reliable data.",
    ),
    (
        "truthful_documents",
        "resume",
        "Resumes, cover letters, and form answers never claim experience, skills, employers, "
        "dates, or results that are not in the user's base resume or profile (the profile's "
        "additional facts are things the user confirmed and may be used).",
    ),
    (
        "resume_layout_consent",
        "resume",
        "Do not change a resume's layout or structure without the user's explicit consent; "
        "content edits only by default.",
    ),
    (
        "document_language",
        "general",
        "Resumes, cover letters, and form answers are written in the language of each job "
        "posting. The panel language does not affect them.",
    ),
    (
        "cover_letter_default",
        "cover_letter",
        "Write a cover letter only when the posting or its form asks for one, unless a rule "
        "from the user says otherwise.",
    ),
    (
        "no_auto_apply",
        "general",
        "The agent never submits applications, sends messages, or changes anything in the "
        "user's accounts on job sites. It prepares; the user applies.",
    ),
    (
        "privacy_boundary",
        "privacy",
        "Personal data is written only inside the private home directory, using the paths "
        "reported by `jobtracker paths`.",
    ),
)


SYSTEM_RULES_ES: dict[str, str] = {
    "salary_evidence":
        "Sugerir un salario solo con 2 o más fuentes comparables y con enlace (mismo país y "
        "nivel, misma modalidad, industria y tamaño de empresa similares). Nunca extrapolar; "
        "si no, registrar que no hay datos confiables.",
    "truthful_documents":
        "Los CV, cartas y respuestas de formulario nunca afirman experiencia, habilidades, "
        "empleadores, fechas o resultados que no estén en el CV base o en el perfil (los datos "
        "adicionales del perfil fueron confirmados por el usuario y pueden usarse).",
    "resume_layout_consent":
        "No cambiar el diseño ni la estructura del CV sin consentimiento explícito; por "
        "defecto, solo contenido.",
    "document_language":
        "Los CV, cartas y respuestas de formulario se escriben en el idioma de cada aviso. El "
        "idioma del panel no influye.",
    "cover_letter_default":
        "Escribir carta de presentación solo cuando el aviso o su formulario la pida, salvo "
        "que una regla del usuario diga otra cosa.",
    "no_auto_apply":
        "El agente nunca envía postulaciones ni mensajes, ni cambia nada en las cuentas del "
        "usuario en los portales. Él prepara; el usuario postula.",
    "privacy_boundary":
        "Los datos personales se escriben solo dentro de la carpeta privada, usando las rutas "
        "que informa `jobtracker paths`.",
}


def seed_system_rules(conn: sqlite3.Connection) -> int:
    """Insert missing system rules and refresh changed texts; returns rows touched."""
    touched = 0
    now = now_iso()
    for key, area, text in SYSTEM_RULES:
        row = conn.execute("SELECT text, area FROM rules WHERE key = ?", (key,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO rules (key, origin, status, area, text, created_at, updated_at)"
                " VALUES (?, 'system', 'active', ?, ?, ?, ?)",
                (key, area, text, now, now),
            )
            touched += 1
        elif row["text"] != text or row["area"] != area:
            conn.execute(
                "UPDATE rules SET text = ?, area = ?, updated_at = ? WHERE key = ?",
                (text, area, now, key),
            )
            touched += 1
    return touched


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "key": row["key"],
        "origin": row["origin"],
        "status": row["status"],
        "area": row["area"],
        "text": row["text"],
        "evidence": row["evidence"],
        "effect": json.loads(row["effect"]) if row["effect"] else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "applied_at": row["applied_at"],
    }


def list_rules(
    conn: sqlite3.Connection, status: str | None = "active", language: str = "en"
) -> list[dict]:
    if status is not None and status not in STATUSES:
        raise JobTrackerError("invalid_rule", f"unknown status '{status}'")
    query = "SELECT * FROM rules"
    params: tuple = ()
    if status is not None:
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY CASE origin WHEN 'system' THEN 0 WHEN 'user' THEN 1 ELSE 2 END, id"
    result = [_row_to_dict(row) for row in conn.execute(query, params)]
    from .seasons import earlier_season_rules

    earlier = earlier_season_rules(conn)
    for rule in result:
        rule["earlier_season"] = rule["id"] in earlier
    if language == "es":
        for rule in result:
            if rule["origin"] == "system" and rule["key"] in SYSTEM_RULES_ES:
                rule["text"] = SYSTEM_RULES_ES[rule["key"]]
    return result


def _editable(conn: sqlite3.Connection, rule_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
    if row is None:
        raise JobTrackerError("not_found", f"There is no rule {rule_id}")
    if row["origin"] == "system":
        raise JobTrackerError(
            "protected_rule", "System rules protect the user and cannot be changed or retired."
        )
    return row


def edit_rule(conn: sqlite3.Connection, rule_id: int, text: str) -> dict:
    """Reword a user or learned rule."""
    _editable(conn, rule_id)
    if not text.strip():
        raise JobTrackerError("invalid_rule", "'text' is required")
    now = now_iso()
    conn.execute("UPDATE rules SET text = ?, updated_at = ? WHERE id = ?",
                 (text.strip(), now, rule_id))
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, created_at)"
        " VALUES ('rule', ?, 'edited', ?)", (str(rule_id), now),
    )
    bump_changes(conn)
    return _row_to_dict(conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone())


def retire_rule(conn: sqlite3.Connection, rule_id: int) -> dict:
    """Stop applying a user or learned rule. It stays in history as reverted."""
    _editable(conn, rule_id)
    now = now_iso()
    conn.execute("UPDATE rules SET status = 'reverted', updated_at = ? WHERE id = ?",
                 (now, rule_id))
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, kind, created_at)"
        " VALUES ('rule', ?, 'retired', ?)", (str(rule_id), now),
    )
    bump_changes(conn)
    return _row_to_dict(conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone())


def _validate(record: object, index: int) -> dict:
    where = f"record {index}"
    if not isinstance(record, dict):
        raise JobTrackerError("invalid_rule", f"{where}: must be an object", index=index)
    text = record.get("text")
    if not isinstance(text, str) or not text.strip():
        raise JobTrackerError("invalid_rule", f"{where}: 'text' is required", index=index)
    origin = record.get("origin", "user")
    if origin not in ("user", "learned"):
        raise JobTrackerError(
            "invalid_rule", f"{where}: origin must be 'user' or 'learned'", index=index
        )
    area = record.get("area", "general")
    if area not in AREAS:
        raise JobTrackerError(
            "invalid_rule", f"{where}: area must be one of {', '.join(AREAS)}", index=index
        )
    default_status = "active" if origin == "user" else "proposed"
    status = record.get("status", default_status)
    if status not in STATUSES:
        raise JobTrackerError("invalid_rule", f"{where}: unknown status '{status}'", index=index)
    if origin == "learned" and status == "active":
        raise JobTrackerError(
            "invalid_rule",
            f"{where}: a learned rule starts as 'proposed'; the user applies it",
            index=index,
        )
    effect = record.get("effect")
    if effect is not None and not isinstance(effect, dict):
        raise JobTrackerError("invalid_rule", f"{where}: 'effect' must be an object", index=index)
    evidence = record.get("evidence")
    if evidence is not None and not isinstance(evidence, str):
        raise JobTrackerError("invalid_rule", f"{where}: 'evidence' must be text", index=index)
    return {
        "origin": origin, "status": status, "area": area, "text": text.strip(),
        "evidence": evidence, "effect": json.dumps(effect) if effect is not None else None,
    }


def add_rules(conn: sqlite3.Connection, records: list) -> list[dict]:
    """Validate every record first, then store them all; nothing is stored on error."""
    if not isinstance(records, list) or not records:
        raise JobTrackerError("invalid_rule", "expected a non-empty list of rules")
    validated = [_validate(record, index) for index, record in enumerate(records)]
    now = now_iso()
    ids = []
    for rule in validated:
        cursor = conn.execute(
            "INSERT INTO rules (origin, status, area, text, evidence, effect, created_at,"
            " updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (rule["origin"], rule["status"], rule["area"], rule["text"], rule["evidence"],
             rule["effect"], now, now),
        )
        ids.append(cursor.lastrowid)
        conn.execute(
            "INSERT INTO events (entity_type, entity_id, kind, data, created_at)"
            " VALUES ('rule', ?, 'created', ?, ?)",
            (str(cursor.lastrowid), json.dumps({"origin": rule["origin"]}), now),
        )
    bump_changes(conn)
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(f"SELECT * FROM rules WHERE id IN ({placeholders}) ORDER BY id", ids)
    return [_row_to_dict(row) for row in rows]
