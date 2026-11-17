"""`jobtracker demo seed`: fictional searches so the panel can be developed and tried.

Everything here is invented (companies, postings, salary reports) and every link
points to example.com. Data is written through the same services the agent
uses, so the demo also exercises validation. Demo rows are marked and can be
removed with `jobtracker demo clear`.
"""
from __future__ import annotations

import shutil
import sqlite3
from datetime import UTC, date, datetime, timedelta

from . import config, salary, scoring, search, tracking, workspace
from .db import bump_changes, session
from .errors import JobTrackerError
from .paths import Paths

PROVIDERS = (
    {"id": "linkedin", "name": "LinkedIn"},
    {"id": "bumeran", "name": "Bumeran"},
    {"id": "indeed", "name": "Indeed"},
    {"id": "computrabajo", "name": "Computrabajo"},
    {"id": "glassdoor", "name": "Glassdoor", "live_walk": True},
)
TITLES = ["Senior Data Engineer", "Data Platform Engineer", "Analytics Engineer",
          "BI Engineer", "Data Engineer"]

DESCRIPTION = """{company} busca un/a {title} para su equipo de datos.

Responsabilidades
• Diseñar y mantener pipelines en Airflow y dbt sobre GCP (BigQuery).
• Modelar datos para analítica comercial e inventario.
• Acompañar a perfiles junior en buenas prácticas.

Requisitos
• {years}+ años en ingeniería de datos.
• Python y SQL avanzados.
• Deseable: {extra}.
• Inglés intermedio.

Modalidad: {mode}. {contract}."""

# key, provider, title, company, location, work mode, contract, seniority, age (days),
# form questions, flags, extra skill, score points (title, skills, seniority, conditions)
LATEST = (
    ("altamar-li", "linkedin", "Senior Data Engineer", "Altamar Retail", "Lima", "remote",
     "full-time", "Senior", 1, 4, [], "Kafka", (25, 27, 15, 14)),
    ("finlima", "bumeran", "Data Platform Engineer", "Finlima S.A.", "San Isidro", "onsite",
     "contractor", "Senior", 2, 0, [], "Terraform", (23, 25, 13, 12)),
    ("nortia", "indeed", "Analytics Engineer", "Nortia Seguros", "Miraflores", "hybrid",
     "full-time", "Senior", 3, 6, [], "Looker", (18, 24, 12, 14)),
    ("cobre", "linkedin", "BI Engineer", "Cobre Logística", "Lima", None, "part-time",
     "Senior", 4, 0, [], "Power BI", (15, 22, 12, 10)),
    ("vertiz", "computrabajo", "Ingeniero de Datos", "Vértiz Salud", "Surco", "onsite",
     "full-time", "Semi Senior", 5, 0, ["Seniority appears lower than yours"], "Spark",
     (18, 20, 8, 10)),
    ("quena", "linkedin", "Data Engineer (Contractor)", "Quena Labs", "LATAM", "remote",
     "contractor", "Senior", 6, 3, [], "Kafka", (20, 24, 12, 9)),
    ("ribera", "bumeran", "ETL Developer", "Ribera Consultores", "San Isidro", "onsite",
     "contractor", "Senior", 7, 0, ["Asks for SSIS, which is not in your resume"], "SSIS",
     (10, 18, 10, 8)),
    ("altamar-in", "indeed", "Senior Data Engineer", "Altamar Retail S.A.C.", "Lima",
     "remote", "full-time", "Senior", 2, 0, [], "Kafka", (25, 27, 15, 14)),
    ("mistral", "linkedin", "Data Engineer", "Mistral Pagos", "Lima", "remote", "full-time",
     "Senior", 2, 0, [], "dbt", (22, 26, 14, 13)),
    ("pukara", "computrabajo", "Data Analyst Sr.", "Pukara Foods", "Miraflores", "hybrid",
     "full-time", "Senior", 3, 0, [], "Tableau", (8, 15, 10, 12)),
)
FILTERED = (
    ("andes", "bumeran", "Data Engineer", "Andes Minería", "Arequipa", "onsite", "full-time",
     "Senior", 2, "location", "Onsite in Arequipa; the profile accepts Lima districts only"),
    ("tambo", "linkedin", "Junior Data Engineer", "Tambo Digital", "Lima", "hybrid",
     "full-time", "Junior", 3, "title", "Junior role, outside the target titles"),
    ("lucuma", "indeed", "Data Engineer", "Lúcuma Tech", "Lima", "remote", "part-time",
     "Senior", 4, "contract_type", "Part-time only; the profile asks for full-time or contract"),
)
EARLIER = (
    ("kallpa", "linkedin", "Senior Data Engineer", "Kallpa Energía", "Lima", "remote",
     "full-time", "Senior", 1, 0, [], "Kafka", (25, 25, 15, 13)),
    ("inti", "indeed", "Data Platform Engineer", "Inti Bank", "San Isidro", "hybrid",
     "full-time", "Senior", 2, 2, [], "Kubernetes", (22, 23, 14, 12)),
)
NOTES = {
    "en": {
        "title": "Matches the target title “{title}”.",
        "skills": "Matches: {matched}. Missing: {extra}.",
        "seniority": "Asks for {years}+ years; the resume shows 7.",
        "conditions": "{mode}, {contract}.",
    },
    "es": {
        "title": "Coincide con el título objetivo “{title}”.",
        "skills": "Coinciden: {matched}. Falta: {extra}.",
        "seniority": "Pide {years}+ años; tu CV muestra 7.",
        "conditions": "{mode}, {contract}.",
    },
}
SKILLS = ("Python", "SQL", "Airflow", "dbt", "BigQuery")
MODES = {"remote": "Remoto", "hybrid": "Híbrido", "onsite": "Presencial"}
NO_MODE = {"en": "work mode not stated", "es": "modalidad no indicada"}
# How some postings describe their arrangement beyond the mode (as the agent would note it).
WORK_MODE_DETAILS = {
    "nortia": "Híbrido: 2 días presencial por semana",
    "mistral": "Horario de verano: viernes hasta el mediodía",
    "ceibo": "Híbrido: martes y jueves en oficina",
}
CONTRACTS = {"full-time": "Tiempo completo", "part-time": "Medio tiempo",
             "contractor": "Contrato por proyecto"}


def _description(key: str, company: str, title: str, extra: str, location: str,
                 mode: str | None, contract: str) -> str:
    text = DESCRIPTION.format(
        company=company, title=title, years=5, extra=extra,
        mode=(MODES[mode] + (" desde Perú" if mode == "remote" else f" en {location}"))
        if mode else "", contract=CONTRACTS[contract])
    if not mode:  # the posting does not say where the work is done
        text = text.replace("Modalidad: . ", "")
    if key in WORK_MODE_DETAILS:
        text += "\n" + WORK_MODE_DETAILS[key] + "."
    return text


def _record(row: tuple, today: date) -> dict:
    key, provider, title, company, location, mode, contract, level, age = row[:9]
    questions = row[9] if len(row) > 9 and isinstance(row[9], int) else 0
    flags = row[10] if len(row) > 10 and isinstance(row[10], list) else []
    extra = row[11] if len(row) > 11 and isinstance(row[11], str) else "Kafka"
    return {
        "provider": provider,
        "external_id": f"demo-{key}",
        "url": f"https://example.com/demo/{provider}/{key}",
        "title": title, "company": company, "location": location, "country": "PE",
        "work_mode": mode, "work_mode_detail": WORK_MODE_DETAILS.get(key),
        "contract_type": contract, "seniority": level,
        "posted_at": (today - timedelta(days=age)).isoformat(),
        "description": _description(key, company, title, extra, location, mode, contract),
        "language": "es", "flags": flags,
        "form_questions": [
            {"text": f"Pregunta de ejemplo {n + 1}", "kind": "text", "required": n == 0}
            for n in range(questions)
        ],
    }


def _score(conn: sqlite3.Connection, posting_id: int, row: tuple, language: str,
           run_id: int, resume: dict | None = None) -> None:
    title, mode, contract, extra, points = row[2], row[5], row[6], row[11], row[12]
    notes = NOTES.get(language, NOTES["en"])
    # A missing skill is never also listed as matched.
    matched = [s for s in SKILLS if s.casefold() != extra.casefold()]
    values = {"title": title, "extra": extra, "years": 5, "matched": ", ".join(matched),
              "mode": MODES[mode] if mode else NO_MODE.get(language, NO_MODE["en"]),
              "contract": CONTRACTS[contract].lower()}
    components = {
        name: {"points": points[index], "note": notes[name].format(**values)}
        for index, name in enumerate(scoring.JUDGED)
    }
    components["skills"].update(matched=matched, missing=[extra])
    submission: dict = {"components": components}
    if resume:
        submission["resume"] = resume
    scoring.set_score(conn, posting_id, submission, run_id=run_id, language=language)


def _evidence(conn: sqlite3.Connection, posting_id: int, currency: str, amounts: list,
              today: date) -> list[int]:
    sources = ("Glassdoor", "Indeed Salaries", "Bumeran")
    records = []
    for index, (low, high) in enumerate(amounts):
        records.append({
            "source": sources[index % len(sources)],
            "url": f"https://example.com/demo/salary/{posting_id}/{index + 1}",
            "summary": "Fictional demo report · same level · remote · retail",
            "amount_min": low, "amount_max": high, "currency": currency, "basis": "gross",
            "period": "month", "sample_size": 3 + index,
            "observed_on": (today - timedelta(days=30 * (index + 1))).isoformat(),
            "country": "PE", "level": "Senior", "work_mode": "remote", "industry": "Retail",
            "company_size": "1,000+", "posting_id": posting_id,
        })
    return [item["id"] for item in salary.add_evidence(conn, records, today)]


def _suggest(conn: sqlite3.Connection, posting_id: int, currency: str, amounts: list,
             today: date) -> None:
    ids = _evidence(conn, posting_id, currency, amounts, today)
    salary.set_suggestion(conn, posting_id, {
        "evidence_ids": ids,
        "criteria": {"currency": currency, "basis": "gross", "industry": "Retail",
                     "company_size": "1,000+"},
    }, today)


def _run(conn: sqlite3.Connection, paths: Paths, started: datetime, rows: tuple,
         filtered: tuple, extra_records: list[dict], language: str) -> tuple[int, dict]:
    started_at = started.strftime("%Y-%m-%dT%H:%M:%SZ")
    run = search.start_run(conn, paths, 7, demo=True, started_at=started_at,
                           demo_providers=list(PROVIDERS), demo_titles=TITLES)
    run_id = run["run_id"]
    day = started.astimezone().date()
    records = [_record(row, day) for row in rows]
    records += [_record(row[:9], day) for row in filtered]
    records += extra_records
    report = search.import_postings(conn, run_id, records)
    ids = {item["external_id"]: item.get("posting_id") for item in report["postings"]}
    if filtered:
        search.filter_postings(conn, run_id, [
            {"posting_id": ids[f"demo-{row[0]}"], "reason": row[9], "detail": row[10]}
            for row in filtered
        ])
    for row in rows:
        _score(conn, ids[f"demo-{row[0]}"], row, language, run_id)
    return run_id, ids


# An older search whose postings the user has been following for weeks, each with
# a different status, so the Applications board has something to show.
OLDER = (
    ("ceibo", "linkedin", "Lead Data Engineer", "Ceibo Pagos", "San Isidro", "hybrid",
     "full-time", "Senior", 2, 0, [], "Kafka", (22, 28, 13, 13)),
    ("lumen", "indeed", "Analytics Engineer", "Lumen Edu", "Lima", "remote", "full-time",
     "Senior", 1, 3, [], "Looker", (18, 25, 12, 14)),
    ("puna", "computrabajo", "Data Engineer", "Puna Energía", "Surco", "onsite", "full-time",
     "Senior", 3, 0, [], "Spark", (20, 24, 13, 9)),
    ("huaral", "bumeran", "Senior Data Engineer", "Huaral Minerals", "Lima", "remote",
     "full-time", "Senior", 2, 4, [], "Kafka", (25, 22, 15, 14)),
    ("quipu", "linkedin", "Data Engineer", "Quipu Analytics", "Lima", "remote", "contractor",
     "Senior", 1, 3, [], "dbt", (21, 26, 13, 12)),
    ("altiplano", "indeed", "BI Developer", "Altiplano Seguros", "Miraflores", "hybrid",
     "full-time", "Senior", 4, 0, [], "Power BI", (12, 18, 12, 12)),
    ("tika", "bumeran", "Data Engineer", "Tika Foods", "Lima", "remote", "full-time",
     "Senior", 2, 0, [], "Airflow", (20, 26, 13, 13)),
)
DEMO_PDF = b"%PDF-1.4\n% Fictional demo resume. Not a real person.\n"
DEMO_DOCX = b"PK\x03\x04 Fictional demo resume. Not a real person."
DEMO_LETTER = ("Estimado equipo de Huaral Minerals:\n\nCarta de presentación ficticia, "
               "generada para la demo del panel.\n\nSaludos.")


def _older_applications(conn: sqlite3.Connection, paths: Paths, now: datetime, language: str,
                        today: date) -> int:
    from . import applications

    started = now - timedelta(days=20)
    run_id, ids = _run(conn, paths, started, OLDER, (), [], language)
    for provider in ("linkedin", "bumeran", "indeed", "computrabajo"):
        search.record_provider(conn, run_id, provider, "ok")
    search.finish_run(conn, run_id)
    posting = {row[0]: ids[f"demo-{row[0]}"] for row in OLDER}
    _suggest(conn, posting["ceibo"], "PEN", [(15500, 17000), (16000, 16800)], today)
    _suggest(conn, posting["huaral"], "PEN", [(14000, 16000), (14500, 15500)], today)
    _suggest(conn, posting["puna"], "PEN", [(12000, 13500), (12500, 13200)], today)
    salary.mark_no_data(conn, posting["lumen"], ["Glassdoor (demo): no reports for this role"])
    tracked = tracking.track(conn, [posting[key] for key, *_ in OLDER])
    job = {key: item["job_id"] for (key, *_), item in zip(OLDER, tracked, strict=True)}

    def applied(key: str, days_ago: int, status: str, ends: bool | None = None,
                **details: object) -> None:
        applications.set_status(conn, [job[key]], status, ends=ends)
        when = now - timedelta(days=days_ago)
        conn.execute("UPDATE applications SET applied_on = ?, status_changed_at = ?"
                     " WHERE job_id = ?",
                     (when.astimezone().date().isoformat(), when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                      job[key]))
        if details:
            applications.update_details(conn, job[key], details)
        conn.execute("UPDATE events SET data = json_set(data, '$.on', ?)"
                     " WHERE entity_type = 'application' AND entity_id = ? AND kind = 'applied'",
                     (when.astimezone().date().isoformat(), job[key]))

    in_days = lambda n: (today + timedelta(days=n)).isoformat()  # noqa: E731
    applied("ceibo", 14, "interview", channel="Company site",
            asked_salary={"amount": 17000, "currency": "PEN"},
            next_step_on=in_days(3), next_step_note="Technical interview")
    applications.set_tags(conn, job["ceibo"], ["Technical 2 of 3"])
    applied("lumen", 25, "applied", channel="Referral",
            asked_salary={"amount": 11500, "currency": "PEN"})
    applications.set_tags(conn, job["lumen"], ["Referral"])
    applied("puna", 27, "offer", channel="Computrabajo",
            asked_salary={"amount": 13000, "currency": "PEN"},
            offered_salary={"amount": 12500, "currency": "PEN"},
            next_step_on=in_days(4), next_step_note="Answer the offer")
    applied("altiplano", 30, "rejected", channel="Indeed")
    applied("tika", 18, "Position frozen", ends=True, channel="Bumeran")

    # Documents for one application: proposed and sent resume, cover letter, rescore.
    folder = applications.folder(conn, paths, job["huaral"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "resume-proposed-v1.docx").write_bytes(DEMO_DOCX)
    applications.register_document(conn, paths, job["huaral"], "resume_proposed",
                                   "resume-proposed-v1.docx", "agent")
    (folder / "cover-letter-v1.md").write_text(DEMO_LETTER, encoding="utf-8")
    applications.register_document(conn, paths, job["huaral"], "cover_letter",
                                   "cover-letter-v1.md", "agent")
    applications.upload_sent_resume(conn, paths, job["huaral"], "demo-resume-final.pdf",
                                    DEMO_PDF)
    applied("huaral", 9, "applied", channel="LinkedIn",
            asked_salary={"amount": 15000, "currency": "PEN"})
    huaral = next(row for row in OLDER if row[0] == "huaral")
    _score(conn, posting["huaral"], (*huaral[:12], (25, 31, 15, 14)), language, run_id,
           resume={"kind": "sent", "ref": "resume-sent.pdf#v1"})
    return run_id


def seed(paths: Paths, learning: str | None = None) -> dict:
    if not workspace.is_initialized(paths):
        workspace.initialize(paths)
    language = str(config.load(paths.config)["language"])
    with session(paths) as conn:
        real = conn.execute("SELECT COUNT(*) FROM postings WHERE is_demo = 0").fetchone()[0]
        if real:
            raise JobTrackerError(
                "has_real_data",
                "This workspace already has real search results; demo data would mix with "
                "them. Use a separate home (JOBTRACKER_HOME) to try the demo.",
            )
        if conn.execute("SELECT COUNT(*) FROM search_runs WHERE is_demo = 1").fetchone()[0]:
            raise JobTrackerError("already_seeded",
                                  "Demo data is already loaded. Run `demo clear` first.")
        now = datetime.now(UTC).replace(microsecond=0)
        today = datetime.now().date()

        older_id = _older_applications(conn, paths, now, language, today)

        earlier_id, earlier_ids = _run(conn, paths, now - timedelta(days=3), EARLIER, (), [],
                                       language)
        for provider in ("linkedin", "bumeran", "indeed", "computrabajo"):
            search.record_provider(conn, earlier_id, provider, "ok")
        search.record_provider(conn, earlier_id, "glassdoor", "skipped", "live_walk")
        search.finish_run(conn, earlier_id)

        earlier_day = (now - timedelta(days=3)).astimezone().date()
        again = [_record(EARLIER[0], earlier_day)]                        # seen before
        twice = [_record(LATEST[0], now.astimezone().date())]             # same URL, same run
        run_id, ids = _run(conn, paths, now, LATEST, FILTERED, again + twice, language)
        search.record_provider(conn, run_id, "glassdoor", "skipped", "live_walk",
                               "Needs you present to browse; run the search while you are here")
        summary = search.finish_run(conn, run_id)

        posting = {row[0]: ids[f"demo-{row[0]}"] for row in LATEST}
        _suggest(conn, posting["altamar-li"], "PEN", [(14000, 16500), (14500, 15500),
                                                      (13800, 15200)], today)
        _suggest(conn, posting["finlima"], "PEN", [(12000, 13500), (12500, 13000)], today)
        _suggest(conn, posting["cobre"], "USD", [(2200, 2600), (2300, 2500)], today)
        _suggest(conn, posting["quena"], "USD", [(3500, 4200), (3600, 4000)], today)
        salary.mark_no_data(conn, posting["nortia"], [
            "Glassdoor (demo): one report, a different level",
            "Indeed Salaries (demo): no reports for this company",
        ])
        salary.mark_no_data(conn, posting["mistral"], ["Glassdoor (demo): no reports"])
        tracking.track(conn, [posting["finlima"]])
        tracking.track(conn, [earlier_ids["demo-inti"]], applied=True)
        tracking.dismiss(conn, [posting["pukara"]], "industry")
        history = None
        if learning:
            from . import demo_learning

            history = demo_learning.add_history(conn, paths, learning)
        bump_changes(conn)
        return {"seeded": True, "runs": [older_id, earlier_id, run_id], "latest_run": summary,
                "learning": history}


def clear(paths: Paths) -> dict:
    """Remove every demo row. Real data is never touched."""
    with session(paths) as conn:
        ids = [r[0] for r in conn.execute("SELECT id FROM postings WHERE is_demo = 1")]
        marks = ",".join("?" * len(ids))
        if ids:
            found = conn.execute(
                f"SELECT a.job_id, p.company FROM applications a JOIN postings p"
                f" ON p.id = a.posting_id WHERE a.posting_id IN ({marks})", ids).fetchall()
            jobs = [r[0] for r in found]
            base = paths.applications.resolve()
            for job_id, company in found:          # demo files only, inside the private home
                folder = paths.job_folder(job_id, company).resolve()
                if folder.is_relative_to(base) and folder.is_dir():
                    shutil.rmtree(folder)
            conn.execute(f"DELETE FROM salary_research_log WHERE posting_id IN ({marks})", ids)
            conn.execute(f"DELETE FROM salary_suggestions WHERE posting_id IN ({marks})", ids)
            conn.execute(f"DELETE FROM salary_evidence WHERE posting_id IN ({marks})", ids)
            conn.execute(f"DELETE FROM applications WHERE posting_id IN ({marks})", ids)
            conn.execute(
                f"DELETE FROM events WHERE entity_type = 'posting' AND entity_id IN ({marks})",
                [str(i) for i in ids])
            if jobs:
                conn.execute(
                    f"DELETE FROM events WHERE entity_type = 'application' AND entity_id IN"
                    f" ({','.join('?' * len(jobs))})", jobs)
            conn.execute(f"DELETE FROM postings WHERE id IN ({marks})", ids)
        runs = conn.execute("DELETE FROM search_runs WHERE is_demo = 1").rowcount
        # Models and influence records were computed from the demo data.
        conn.execute("DELETE FROM analyses")
        conn.execute("DELETE FROM experiments")
        conn.execute("DELETE FROM rule_influence")
        bump_changes(conn)
        return {"cleared": True, "postings": len(ids), "runs": runs}
