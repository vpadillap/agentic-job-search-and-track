"""`jobtracker <command>`: JSON on stdout, diagnostics on stderr, non-zero on failure.

Success: {"ok": true, ...}. Failure: {"ok": false, "error": {"code", "message"}}.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jobtracker.core import (
    answers,
    applications,
    board,
    config,
    context,
    db,
    demo,
    doctor,
    documents,
    docx_tools,
    privacy,
    profile,
    providers,
    resume,
    rules,
    salary,
    scoring,
    search,
    setup,
    skills,
    workspace,
)
from jobtracker.core.errors import JobTrackerError
from jobtracker.core.paths import cli_name, get_paths, next_version_path

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):  # usage errors are reported as JSON too
        raise JobTrackerError("usage", f"{message}. Try `{self.prog} --help`.")


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _read_json(source: str) -> object:
    try:
        if source == "-":
            # JSON is UTF-8 whatever the console's code page is (cp1252 on Windows).
            raw = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read()
            text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
        else:
            text = Path(source).read_text(encoding="utf-8-sig")
        return json.loads(text)
    except UnicodeDecodeError as error:
        raise JobTrackerError("invalid_json", f"'{source}' is not UTF-8 text: {error}") from error
    except OSError as error:
        raise JobTrackerError("unreadable_input", f"Cannot read '{source}': {error}") from error
    except json.JSONDecodeError as error:
        raise JobTrackerError("invalid_json", f"'{source}' is not valid JSON: {error}") from error


# ── commands ──────────────────────────────────────────────────────────────

def cmd_doctor(args: argparse.Namespace) -> dict:
    return doctor.run(get_paths())


def cmd_init(args: argparse.Namespace) -> dict:
    return workspace.initialize(get_paths(), language=args.language)


def cmd_paths(args: argparse.Namespace) -> dict:
    paths = get_paths()
    result: dict = {"paths": paths.as_dict()}
    if args.document and not args.job:
        raise JobTrackerError("usage", "--document requires --job and --company")
    if args.job:
        folder = paths.job_folder(args.job, args.company or "")
        result["job_folder"] = str(folder)
        if args.document:
            result["document"] = str(next_version_path(folder, args.document, args.ext))
    return result


def cmd_context(args: argparse.Namespace) -> dict:
    return context.build(get_paths())


def cmd_config_show(args: argparse.Namespace) -> dict:
    return {"config": config.load(get_paths().config)}


def cmd_config_set(args: argparse.Namespace) -> dict:
    paths = get_paths()
    if not workspace.is_initialized(paths):
        raise JobTrackerError("not_initialized", "The workspace is not initialized. Run /setup.")
    settings = config.set_value(paths.config, args.key, args.value)
    with db.session(paths) as conn:
        db.bump_changes(conn)
    result: dict = {"config": settings}
    if args.key == "language":
        result["skills"] = skills.sync(str(settings["language"]))
    return result


def cmd_profile_show(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        if args.version is not None:
            return {"profile": profile.get_version(conn, args.version)}
        return {"profile": profile.get_active(conn)}


def cmd_profile_set(args: argparse.Namespace) -> dict:
    changes = _read_json(args.file)
    with db.session(get_paths()) as conn:
        return {"profile": profile.update(conn, changes)}


def cmd_profile_title(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"profile": profile.set_title_state(conn, args.title, args.state, args.reason)}


def cmd_profile_titles(args: argparse.Namespace) -> dict:
    changes = _read_json(args.file)
    with db.session(get_paths()) as conn:
        return {"profile": profile.set_titles(conn, changes)}


def cmd_profile_remove_title(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"profile": profile.remove_title(conn, args.title)}


def cmd_profile_history(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"versions": profile.history(conn)}


def cmd_resume_import(args: argparse.Namespace) -> dict:
    paths = get_paths()
    text_file = Path(args.text) if args.text else None
    with db.session(paths) as conn:
        return {"resume": resume.import_resume(conn, paths, Path(args.file), text_file)}


def cmd_resume_show(args: argparse.Namespace) -> dict:
    paths = get_paths()
    with db.session(paths) as conn:
        return {"resume": resume.current(conn, paths)}


def cmd_privacy_terms_add(args: argparse.Namespace) -> dict:
    return privacy.add_terms(get_paths(), args.terms)


def cmd_privacy_terms_list(args: argparse.Namespace) -> dict:
    return {"terms": privacy.list_terms(get_paths())}


def cmd_skills_sync(args: argparse.Namespace) -> dict:
    language = str(config.load(get_paths().config)["language"])
    return skills.sync(language)


def cmd_skills_list(args: argparse.Namespace) -> dict:
    language = str(config.load(get_paths().config)["language"])
    return {"commands": skills.command_list(language)}


def cmd_setup_status(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return setup.status(conn)


def cmd_setup_done(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return setup.mark_done(conn, args.steps)


def cmd_setup_redo(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return setup.redo(conn, args.step)


def cmd_providers_list(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"providers": providers.with_state(conn)}


def cmd_providers_enable(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"providers": providers.set_enabled(conn, args.provider, args.enabled)}


def cmd_rules_list(args: argparse.Namespace) -> dict:
    status = None if args.status == "all" else args.status
    paths = get_paths()
    language = str(config.load(paths.config)["language"])
    with db.session(paths) as conn:
        return {"rules": rules.list_rules(conn, status, language)}


def cmd_rules_edit(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"rule": rules.edit_rule(conn, args.id, args.text)}


def cmd_rules_retire(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"rule": rules.retire_rule(conn, args.id)}


def cmd_rules_add(args: argparse.Namespace) -> dict:
    record = {"origin": args.origin, "area": args.area, "text": args.text}
    if args.evidence:
        record["evidence"] = args.evidence
    with db.session(get_paths()) as conn:
        return {"rules": rules.add_rules(conn, [record])}


def cmd_rules_import(args: argparse.Namespace) -> dict:
    records = _read_json(args.file)
    with db.session(get_paths()) as conn:
        return {"rules": rules.add_rules(conn, records)}  # type: ignore[arg-type]


def cmd_providers_validate(args: argparse.Namespace) -> dict:
    return providers.validate(file=Path(args.file) if args.file else None)


def _language() -> str:
    return str(config.load(get_paths().config)["language"])


def cmd_run_start(args: argparse.Namespace) -> dict:
    paths = get_paths()
    with db.session(paths) as conn:
        return search.start_run(conn, paths, args.days)


def cmd_run_provider(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"run": search.record_provider(conn, args.run_id, args.provider, args.status,
                                              args.reason, args.detail)}


def cmd_run_finish(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"run": search.finish_run(conn, args.run_id)}


def cmd_run_show(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        run_id = args.run_id or search.latest_run_id(conn)
        if run_id is None:
            raise JobTrackerError("not_found", "There are no search runs yet")
        return {"run": search.summary(conn, run_id)}


def cmd_run_list(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"runs": search.list_runs(conn)}


def cmd_postings_import(args: argparse.Namespace) -> dict:
    records = _read_json(args.file)
    with db.session(get_paths()) as conn:
        return search.import_postings(conn, args.run_id, records)


def cmd_postings_filter(args: argparse.Namespace) -> dict:
    records = _read_json(args.file)
    with db.session(get_paths()) as conn:
        return search.filter_postings(conn, args.run_id, records)


def cmd_postings_flag(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"posting": search.add_flag(conn, args.id, args.text)}


def cmd_postings_questions(args: argparse.Namespace) -> dict:
    records = _read_json(args.file)
    with db.session(get_paths()) as conn:
        return {"posting": search.set_questions(conn, args.id, records)}


def cmd_postings_list(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"postings": search.list_postings(conn, args.run_id, args.outcome)}


def cmd_postings_show(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        item = search.posting(conn, args.id)
        item["score"] = scoring.current(conn, args.id)
        item["salary"] = salary.current(conn, args.id)
        item["possible_duplicates"] = search.possible_duplicates(
            conn, args.id, search.latest_run_id(conn))
        return {"posting": item}


def cmd_score_set(args: argparse.Namespace) -> dict:
    submission = _read_json(args.file)
    with db.session(get_paths()) as conn:
        return {"score": scoring.set_score(conn, args.id, submission, run_id=args.run_id,
                                           language=_language())}


def cmd_score_show(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        result: dict = {"score": scoring.current(conn, args.id)}
        if args.history:
            result["history"] = scoring.history(conn, args.id)
            result["at_application"] = scoring.at_application(conn, args.id)
        return result


def cmd_score_weights(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        if args.set:
            return {"weights": scoring.set_weights(conn, _read_json(args.set), args.note)}
        return {"weights": scoring.active_weights(conn),
                "history": scoring.weights_history(conn)}


def cmd_salary_evidence_add(args: argparse.Namespace) -> dict:
    records = _read_json(args.file)
    with db.session(get_paths()) as conn:
        return {"evidence": salary.add_evidence(conn, records)}


def cmd_salary_set(args: argparse.Namespace) -> dict:
    submission = _read_json(args.file)
    with db.session(get_paths()) as conn:
        return {"salary": salary.set_suggestion(conn, args.id, submission)}


def cmd_salary_none(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"salary": salary.mark_no_data(conn, args.id, args.checked)}


def cmd_salary_lookup(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return salary.lookup(conn, args.id)


def cmd_salary_show(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"salary": salary.current(conn, args.id)}


def cmd_applications_list(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        items = applications.list_applications(conn, _language(), args.stage,
                                               include_closed=not args.hide_closed)
        return {"applications": items, "funnel": applications.funnel(items),
                "attention": applications.attention(items)}


def cmd_applications_show(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"application": applications.detail(conn, args.job_id, _language())}


def cmd_applications_set_status(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        changed = applications.set_status(conn, args.job_ids, args.to, stage=args.stage)
        return {"applications": [applications.application(conn, j, _language())
                                 for j in changed]}


def cmd_applications_update(args: argparse.Namespace) -> dict:
    changes = _read_json(args.file)
    with db.session(get_paths()) as conn:
        return {"application": applications.update_details(conn, args.job_id, changes)}


def cmd_applications_tag(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"tags": applications.set_tags(conn, args.job_id, args.add, args.remove)}


def cmd_applications_upload_resume(args: argparse.Namespace) -> dict:
    paths = get_paths()
    source = Path(args.file)
    if not source.is_file():
        raise JobTrackerError("not_found", f"There is no file at '{source}'")
    with db.session(paths) as conn:
        return {"document": applications.upload_sent_resume(
            conn, paths, args.job_id, source.name, source.read_bytes())}


def cmd_statuses_list(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"statuses": applications.list_statuses(conn, _language(), args.all)}


def cmd_statuses_create(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"status": applications.create_status(conn, args.name, args.stage)}


def cmd_statuses_rename(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"status": applications.rename_status(conn, args.id, args.name)}


def cmd_statuses_retire(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"status": applications.retire_status(conn, args.id, not args.restore)}


def cmd_pending(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        items = board.pending(conn)
    if args.ids:
        wanted = set(args.ids)
        unknown = sorted(wanted - {i["job_id"] for i in items if i.get("job_id")})
        items = [i for i in items if i.get("job_id") in wanted]
        return {"pending": items, "nothing_pending_for": unknown}
    return {"pending": items}


def _in_folder(conn, paths, job_id: str, file_name: str) -> Path:
    base = applications.folder(conn, paths, job_id).resolve()
    path = (base / Path(file_name).name).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise JobTrackerError("not_found",
                              f"'{file_name}' is not a file in the folder of {job_id}")
    return path


def _base_resume_file(conn, paths) -> Path:
    base = resume.current(conn, paths)
    if base is None:
        raise JobTrackerError("no_base_resume", "There is no base resume. Run /setup.")
    return Path(base["path"])


def cmd_documents_path(args: argparse.Namespace) -> dict:
    paths = get_paths()
    with db.session(paths) as conn:
        path = documents.next_path(conn, paths, args.job_id, args.kind, args.ext)
    return {"path": str(path), "file_name": path.name}


def cmd_documents_register(args: argparse.Namespace) -> dict:
    meta = _read_json(args.meta)
    paths = get_paths()
    with db.session(paths) as conn:
        return {"document": documents.register(conn, paths, args.job_id, args.kind,
                                               args.file, meta)}


def cmd_documents_list(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        app = applications.application(conn, args.job_id, _language())
        return {"documents": documents.list_for(conn, args.job_id),
                "cover_letter": app["cover_letter"]}


def cmd_documents_diff(args: argparse.Namespace) -> dict:
    paths = get_paths()
    with db.session(paths) as conn:
        return documents.diff(conn, paths, args.job_id, args.document)


def cmd_documents_tailor(args: argparse.Namespace) -> dict:
    request = _read_json(args.file)
    if not isinstance(request, dict) or "edits" not in request:
        raise JobTrackerError("invalid_edit", 'expected an object {"edits": [...]}')
    paths = get_paths()
    with db.session(paths) as conn:
        base = _base_resume_file(conn, paths)
        target = documents.next_path(conn, paths, args.job_id, "resume-proposed", "docx")
    result = docx_tools.tailor(base, target, request["edits"])
    result["file_name"] = target.name
    result["layout"] = docx_tools.layout_check(base, target)
    return result


def cmd_documents_check(args: argparse.Namespace) -> dict:
    paths = get_paths()
    with db.session(paths) as conn:
        base = _base_resume_file(conn, paths)
        proposed = _in_folder(conn, paths, args.job_id, args.file)
    if base.suffix.lower() != ".docx" or proposed.suffix.lower() != ".docx":
        raise JobTrackerError("invalid_document", "the layout check compares two DOCX files")
    return {"layout": docx_tools.layout_check(base, proposed)}


def cmd_documents_cover_letter(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"cover_letter": documents.set_cover_letter_need(conn, args.job_id, args.need,
                                                                args.reason)}


def cmd_answers_list(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        questions = answers.list_answers(conn, args.job_id)
    result: dict = {"questions": questions}
    if not questions:
        result["message"] = (f"{args.job_id} has no captured form questions: "
                             "there is no form to answer")
    return result


def cmd_answers_set(args: argparse.Namespace) -> dict:
    proposals = _read_json(args.file)
    with db.session(get_paths()) as conn:
        return answers.propose(conn, args.job_id, proposals, as_alternative=args.alternative)


def cmd_answers_edit(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"question": answers.edit(conn, args.job_id, args.position, args.text)}


def cmd_answers_pick(args: argparse.Namespace) -> dict:
    with db.session(get_paths()) as conn:
        return {"question": answers.pick(conn, args.job_id, args.answer_id)}


def cmd_demo_seed(args: argparse.Namespace) -> dict:
    return demo.seed(get_paths())


def cmd_demo_clear(args: argparse.Namespace) -> dict:
    return demo.clear(get_paths())


def cmd_reset(args: argparse.Namespace) -> dict:
    return workspace.reset(get_paths(), args.confirm, args.label)


def cmd_panel(args: argparse.Namespace) -> dict:
    paths = get_paths()
    settings = config.load(paths.config)
    port = config.validate("port", args.port) if args.port else settings["port"]
    try:
        import uvicorn

        from jobtracker.web.app import create_app
    except ImportError as error:
        raise JobTrackerError(
            "missing_dependency", f"The panel needs packages that are not installed ({error.name})."
            f" {doctor.INSTALL_HINT}",
        ) from error
    print(f"Panel running at http://{settings['host']}:{port} (Ctrl+C to stop)", file=sys.stderr)
    uvicorn.run(create_app(), host=str(settings["host"]), port=int(port), log_level="warning")
    return {"stopped": True}


# ── parser ────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog=cli_name(), description="Job Tracker data interface for agents.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    sub.add_parser("doctor", help="check the environment (changes nothing)").set_defaults(
        run=cmd_doctor)

    init = sub.add_parser("init", help="create the private workspace (safe to repeat)")
    init.add_argument("--language", choices=config.LANGUAGES)
    init.set_defaults(run=cmd_init)

    paths = sub.add_parser("paths", help="show where everything is stored")
    paths.add_argument("--job", help="job id, e.g. J0007")
    paths.add_argument("--company", help="company name, used for the folder slug")
    paths.add_argument("--document", help="document name, e.g. resume-proposed")
    paths.add_argument("--ext", default="md", help="extension for --document")
    paths.set_defaults(run=cmd_paths)

    sub.add_parser("context", help="everything an agent must load before acting").set_defaults(
        run=cmd_context)

    config_parser = sub.add_parser("config", help="panel settings")
    config_sub = config_parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    config_sub.add_parser("show").set_defaults(run=cmd_config_show)
    config_set = config_sub.add_parser("set")
    config_set.add_argument("key", choices=sorted(config.DEFAULTS))
    config_set.add_argument("value")
    config_set.set_defaults(run=cmd_config_set)

    profile_parser = sub.add_parser("profile", help="job needs and target titles")
    profile_sub = profile_parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    profile_show = profile_sub.add_parser("show")
    profile_show.add_argument("--version", type=int)
    profile_show.set_defaults(run=cmd_profile_show)
    profile_set = profile_sub.add_parser("set", help="change fields; creates a new version")
    profile_set.add_argument("file", help="JSON object with the fields to change, or - for stdin")
    profile_set.set_defaults(run=cmd_profile_set)
    profile_title = profile_sub.add_parser("title", help="set the state of one target title")
    profile_title.add_argument("title")
    profile_title.add_argument("state", choices=profile.TITLE_STATES)
    profile_title.add_argument("--reason")
    profile_title.set_defaults(run=cmd_profile_title)
    profile_titles = profile_sub.add_parser(
        "titles", help="set the state of several titles at once (one new version)")
    profile_titles.add_argument("file", help="JSON list of {title, state, reason}, or - for stdin")
    profile_titles.set_defaults(run=cmd_profile_titles)
    profile_remove = profile_sub.add_parser("remove-title", help="delete a mistyped title")
    profile_remove.add_argument("title")
    profile_remove.set_defaults(run=cmd_profile_remove_title)
    profile_sub.add_parser("history").set_defaults(run=cmd_profile_history)

    resume_parser = sub.add_parser("resume", help="the base resume")
    resume_sub = resume_parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    resume_import = resume_sub.add_parser("import", help="store a resume as the base resume")
    resume_import.add_argument("file")
    resume_import.add_argument("--text", help="text of the resume when it cannot be extracted")
    resume_import.set_defaults(run=cmd_resume_import)
    resume_sub.add_parser("show").set_defaults(run=cmd_resume_show)

    privacy_parser = sub.add_parser("privacy", help="privacy guard settings")
    privacy_sub = privacy_parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    terms = privacy_sub.add_parser("terms")
    terms_sub = terms.add_subparsers(dest="terms_action", required=True, parser_class=_Parser)
    terms_add = terms_sub.add_parser("add", help="register identifying terms (name, email...)")
    terms_add.add_argument("terms", nargs="+")
    terms_add.set_defaults(run=cmd_privacy_terms_add)
    terms_sub.add_parser("list", help="show the registered terms").set_defaults(
        run=cmd_privacy_terms_list)

    skills_parser = sub.add_parser("skills", help="agent commands and their aliases")
    skills_sub = skills_parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    skills_sub.add_parser("sync", help="install aliases for the panel language").set_defaults(
        run=cmd_skills_sync)
    skills_sub.add_parser("list").set_defaults(run=cmd_skills_list)

    setup_parser = sub.add_parser("setup", help="first-run progress")
    setup_sub = setup_parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    setup_sub.add_parser("status").set_defaults(run=cmd_setup_status)
    setup_done = setup_sub.add_parser("done")
    setup_done.add_argument("steps", nargs="+", choices=setup.STEP_IDS)
    setup_done.set_defaults(run=cmd_setup_done)
    setup_redo = setup_sub.add_parser("redo")
    setup_redo.add_argument("step", choices=setup.STEP_IDS)
    setup_redo.set_defaults(run=cmd_setup_redo)

    providers_parser = sub.add_parser("providers", help="job sites")
    providers_sub = providers_parser.add_subparsers(
        dest="action", required=True, parser_class=_Parser)
    providers_sub.add_parser("list").set_defaults(run=cmd_providers_list)
    for action, enabled in (("enable", True), ("disable", False)):
        toggle = providers_sub.add_parser(action)
        toggle.add_argument("provider")
        toggle.set_defaults(run=cmd_providers_enable, enabled=enabled)

    providers_validate = providers_sub.add_parser(
        "validate", help="check provider files against the template")
    providers_validate.add_argument("file", nargs="?", help="one file (default: all)")
    providers_validate.set_defaults(run=cmd_providers_validate)

    run_parser = sub.add_parser("run", help="search runs")
    run_sub = run_parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    run_start = run_sub.add_parser("start", help="open a run: titles, providers, capture folder")
    run_start.add_argument("--days", type=int, help="posting age window (default: profile)")
    run_start.set_defaults(run=cmd_run_start)
    run_provider = run_sub.add_parser("provider", help="record how a provider went")
    run_provider.add_argument("run_id", type=int, metavar="run")
    run_provider.add_argument("provider")
    run_provider.add_argument("--status", required=True, choices=("ok", "skipped", "failed"))
    run_provider.add_argument("--reason", choices=search.SKIP_REASONS)
    run_provider.add_argument("--detail")
    run_provider.set_defaults(run=cmd_run_provider)
    run_finish = run_sub.add_parser("finish", help="close a run and get its summary")
    run_finish.add_argument("run_id", type=int, metavar="run")
    run_finish.set_defaults(run=cmd_run_finish)
    run_show = run_sub.add_parser("show", help="summary of a run (default: latest)")
    run_show.add_argument("run_id", type=int, nargs="?", metavar="run")
    run_show.set_defaults(run=cmd_run_show)
    run_sub.add_parser("list").set_defaults(run=cmd_run_list)

    postings_parser = sub.add_parser("postings", help="postings found by searches")
    postings_sub = postings_parser.add_subparsers(
        dest="action", required=True, parser_class=_Parser)
    postings_import = postings_sub.add_parser("import", help="store what providers returned")
    postings_import.add_argument("run_id", type=int, metavar="run")
    postings_import.add_argument("file", help="JSON list of postings, or - for stdin")
    postings_import.set_defaults(run=cmd_postings_import)
    postings_filter = postings_sub.add_parser("filter", help="record exclusions with reasons")
    postings_filter.add_argument("run_id", type=int, metavar="run")
    postings_filter.add_argument("file", help="JSON list of {posting_id, reason, detail}")
    postings_filter.set_defaults(run=cmd_postings_filter)
    postings_flag = postings_sub.add_parser("flag", help="add a visible doubt to a posting")
    postings_flag.add_argument("id", type=int)
    postings_flag.add_argument("--text", required=True)
    postings_flag.set_defaults(run=cmd_postings_flag)
    postings_questions = postings_sub.add_parser("questions", help="store form questions")
    postings_questions.add_argument("id", type=int)
    postings_questions.add_argument("file", help="JSON list of questions, or - for stdin")
    postings_questions.set_defaults(run=cmd_postings_questions)
    postings_list = postings_sub.add_parser("list", help="postings of a run (default: latest)")
    postings_list.add_argument("--run", type=int, dest="run_id")
    postings_list.add_argument("--outcome", choices=("new", "filtered", "duplicate", "seen"))
    postings_list.set_defaults(run=cmd_postings_list)
    postings_show = postings_sub.add_parser("show")
    postings_show.add_argument("id", type=int)
    postings_show.set_defaults(run=cmd_postings_show)

    score_parser = sub.add_parser("score", help="alignment scores")
    score_sub = score_parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    score_set = score_sub.add_parser("set", help="store a score (history is kept)")
    score_set.add_argument("id", type=int, help="posting id")
    score_set.add_argument("file", help="JSON with components, or - for stdin")
    score_set.add_argument("--run", type=int, dest="run_id")
    score_set.set_defaults(run=cmd_score_set)
    score_show = score_sub.add_parser("show")
    score_show.add_argument("id", type=int, help="posting id")
    score_show.add_argument("--history", action="store_true")
    score_show.set_defaults(run=cmd_score_show)
    score_weights = score_sub.add_parser("weights", help="show or change component maximums")
    score_weights.add_argument("--set", help="JSON file with new maximums (creates a version)")
    score_weights.add_argument("--note")
    score_weights.set_defaults(run=cmd_score_weights)

    salary_parser = sub.add_parser("salary", help="salary evidence and suggestions")
    salary_sub = salary_parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    evidence_parser = salary_sub.add_parser("evidence")
    evidence_sub = evidence_parser.add_subparsers(
        dest="evidence_action", required=True, parser_class=_Parser)
    evidence_add = evidence_sub.add_parser("add", help="store salary reports with links")
    evidence_add.add_argument("file", help="JSON list of evidence, or - for stdin")
    evidence_add.set_defaults(run=cmd_salary_evidence_add)
    salary_set = salary_sub.add_parser("set", help="suggest a salary from 2+ comparable sources")
    salary_set.add_argument("id", type=int, help="posting id")
    salary_set.add_argument("file", help="JSON {evidence_ids, criteria}, or - for stdin")
    salary_set.set_defaults(run=cmd_salary_set)
    salary_none = salary_sub.add_parser("none", help="record that there is no reliable data")
    salary_none.add_argument("id", type=int, help="posting id")
    salary_none.add_argument("--checked", action="append", required=True,
                             help="a source or search that was tried (repeat)")
    salary_none.set_defaults(run=cmd_salary_none)
    salary_lookup = salary_sub.add_parser("lookup", help="recent evidence for the same job")
    salary_lookup.add_argument("id", type=int, help="posting id")
    salary_lookup.set_defaults(run=cmd_salary_lookup)
    salary_show = salary_sub.add_parser("show")
    salary_show.add_argument("id", type=int, help="posting id")
    salary_show.set_defaults(run=cmd_salary_show)

    apps_parser = sub.add_parser("applications", help="tracked applications")
    apps_sub = apps_parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    apps_list = apps_sub.add_parser("list")
    apps_list.add_argument("--stage", choices=applications.STAGES)
    apps_list.add_argument("--hide-closed", action="store_true",
                           help="leave out the closed negative stage")
    apps_list.set_defaults(run=cmd_applications_list)
    apps_show = apps_sub.add_parser("show", help="details, documents, questions, history")
    apps_show.add_argument("job_id")
    apps_show.set_defaults(run=cmd_applications_show)
    apps_status = apps_sub.add_parser("set-status", help="change the status of applications")
    apps_status.add_argument("job_ids", nargs="+")
    apps_status.add_argument("--to", required=True, help="status name, key, or id")
    apps_status.add_argument("--stage", choices=applications.STAGES,
                             help="create the status in this stage if it does not exist")
    apps_status.set_defaults(run=cmd_applications_set_status)
    apps_update = apps_sub.add_parser("update", help="change application details")
    apps_update.add_argument("job_id")
    apps_update.add_argument("file", help="JSON object with the fields to change, or -")
    apps_update.set_defaults(run=cmd_applications_update)
    apps_tag = apps_sub.add_parser("tag", help="add or remove free-form tags")
    apps_tag.add_argument("job_id")
    apps_tag.add_argument("--add", action="append", default=[])
    apps_tag.add_argument("--remove", action="append", default=[])
    apps_tag.set_defaults(run=cmd_applications_tag)
    apps_upload = apps_sub.add_parser("upload-resume", help="store the resume actually sent")
    apps_upload.add_argument("job_id")
    apps_upload.add_argument("file", help="PDF or DOCX")
    apps_upload.set_defaults(run=cmd_applications_upload_resume)
    statuses_parser = apps_sub.add_parser("statuses", help="built-in and custom statuses")
    statuses_sub = statuses_parser.add_subparsers(
        dest="status_action", required=True, parser_class=_Parser)
    statuses_list = statuses_sub.add_parser("list")
    statuses_list.add_argument("--all", action="store_true", help="include retired statuses")
    statuses_list.set_defaults(run=cmd_statuses_list)
    statuses_create = statuses_sub.add_parser("create")
    statuses_create.add_argument("name")
    statuses_create.add_argument("--stage", required=True, choices=applications.STAGES)
    statuses_create.set_defaults(run=cmd_statuses_create)
    statuses_rename = statuses_sub.add_parser("rename")
    statuses_rename.add_argument("id", type=int)
    statuses_rename.add_argument("name")
    statuses_rename.set_defaults(run=cmd_statuses_rename)
    statuses_retire = statuses_sub.add_parser("retire", help="stop offering a custom status")
    statuses_retire.add_argument("id", type=int)
    statuses_retire.add_argument("--restore", action="store_true")
    statuses_retire.set_defaults(run=cmd_statuses_retire)

    pending = sub.add_parser("pending", help="work items waiting for the agent")
    pending.add_argument("--ids", nargs="+", help="only these applications (job ids)")
    pending.set_defaults(run=cmd_pending)

    docs_parser = sub.add_parser("documents", help="tailored resumes and cover letters")
    docs_sub = docs_parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    kinds = ("resume-proposed", "cover-letter")
    docs_path = docs_sub.add_parser("path", help="where to write the next version")
    docs_path.add_argument("job_id")
    docs_path.add_argument("--kind", required=True, choices=kinds)
    docs_path.add_argument("--ext", required=True, help="docx or md")
    docs_path.set_defaults(run=cmd_documents_path)
    docs_register = docs_sub.add_parser("register", help="register a document you wrote")
    docs_register.add_argument("job_id")
    docs_register.add_argument("kind", choices=kinds)
    docs_register.add_argument("file", help="file name inside the application folder")
    docs_register.add_argument("meta", help="JSON: language, summary, support, gaps... or -")
    docs_register.set_defaults(run=cmd_documents_register)
    docs_list = docs_sub.add_parser("list")
    docs_list.add_argument("job_id")
    docs_list.set_defaults(run=cmd_documents_list)
    docs_diff = docs_sub.add_parser("diff", help="a proposed resume against the base resume")
    docs_diff.add_argument("job_id")
    docs_diff.add_argument("--document", type=int, help="document id (default: current)")
    docs_diff.set_defaults(run=cmd_documents_diff)
    docs_tailor = docs_sub.add_parser(
        "tailor", help="copy the DOCX base resume with text edits, design untouched")
    docs_tailor.add_argument("job_id")
    docs_tailor.add_argument("file", help='JSON {"edits": [...]}, or -')
    docs_tailor.set_defaults(run=cmd_documents_tailor)
    docs_check = docs_sub.add_parser("check", help="compare a DOCX's shape with the base resume")
    docs_check.add_argument("job_id")
    docs_check.add_argument("file")
    docs_check.set_defaults(run=cmd_documents_check)
    docs_letter = docs_sub.add_parser("cover-letter", help="record whether one is needed")
    docs_letter.add_argument("job_id")
    docs_letter.add_argument("--need", required=True, choices=documents.COVER_LETTER_NEEDS)
    docs_letter.add_argument("--reason")
    docs_letter.set_defaults(run=cmd_documents_cover_letter)

    answers_parser = sub.add_parser("answers", help="answers to application-form questions")
    answers_sub = answers_parser.add_subparsers(dest="action", required=True,
                                                parser_class=_Parser)
    answers_list = answers_sub.add_parser("list")
    answers_list.add_argument("job_id")
    answers_list.set_defaults(run=cmd_answers_list)
    answers_set = answers_sub.add_parser(
        "set", help="propose answers (an answer the user edited is never replaced)")
    answers_set.add_argument("job_id")
    answers_set.add_argument("file", help="JSON list of answers, or -")
    answers_set.set_defaults(run=cmd_answers_set, alternative=False)
    answers_alt = answers_sub.add_parser("alternative",
                                         help="propose other versions to pick from")
    answers_alt.add_argument("job_id")
    answers_alt.add_argument("file", help="JSON list of answers, or -")
    answers_alt.set_defaults(run=cmd_answers_set, alternative=True)
    answers_edit = answers_sub.add_parser("edit", help="the user's own wording for an answer")
    answers_edit.add_argument("job_id")
    answers_edit.add_argument("position", type=int)
    answers_edit.add_argument("--text", required=True)
    answers_edit.set_defaults(run=cmd_answers_edit)
    answers_pick = answers_sub.add_parser("pick", help="make an alternative the current answer")
    answers_pick.add_argument("job_id")
    answers_pick.add_argument("answer_id", type=int)
    answers_pick.set_defaults(run=cmd_answers_pick)

    demo_parser = sub.add_parser("demo", help="fictional data for trying the panel")
    demo_sub = demo_parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    demo_sub.add_parser("seed", help="load fictional searches").set_defaults(run=cmd_demo_seed)
    demo_sub.add_parser("clear", help="remove the demo data").set_defaults(run=cmd_demo_clear)

    rules_parser = sub.add_parser("rules", help="rules the agent obeys")
    rules_sub = rules_parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    rules_list = rules_sub.add_parser("list")
    rules_list.add_argument("--status", default="active", choices=(*rules.STATUSES, "all"))
    rules_list.set_defaults(run=cmd_rules_list)
    rules_add = rules_sub.add_parser("add")
    rules_add.add_argument("--text", required=True)
    rules_add.add_argument("--area", default="general")
    rules_add.add_argument("--origin", default="user")
    rules_add.add_argument("--evidence")
    rules_add.set_defaults(run=cmd_rules_add)
    rules_edit = rules_sub.add_parser("edit", help="reword a user or learned rule")
    rules_edit.add_argument("id", type=int)
    rules_edit.add_argument("--text", required=True)
    rules_edit.set_defaults(run=cmd_rules_edit)
    rules_retire = rules_sub.add_parser("retire", help="stop applying a user or learned rule")
    rules_retire.add_argument("id", type=int)
    rules_retire.set_defaults(run=cmd_rules_retire)
    rules_import = rules_sub.add_parser("import", help="add several rules from a JSON list")
    rules_import.add_argument("file", help="JSON file, or - for standard input")
    rules_import.set_defaults(run=cmd_rules_import)

    reset = sub.add_parser("reset", help="archive all data and start empty")
    reset.add_argument("--confirm")
    reset.add_argument("--label", default="reset")
    reset.set_defaults(run=cmd_reset)

    panel = sub.add_parser("panel", help="start the local panel")
    panel.add_argument("--port")
    panel.set_defaults(run=cmd_panel)

    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        args = build_parser().parse_args(argv)
        result = args.run(args)
    except JobTrackerError as error:
        print(f"error: {error.message}", file=sys.stderr)
        _emit({"ok": False, "error": error.to_dict()})
        return EXIT_USAGE if error.code == "usage" else EXIT_ERROR
    except KeyboardInterrupt:
        return EXIT_OK
    except Exception as error:  # unexpected: still machine-readable
        print(f"unexpected error: {error!r}", file=sys.stderr)
        _emit({"ok": False, "error": {"code": "internal_error", "message": str(error)}})
        return EXIT_ERROR
    _emit({"ok": True, **result})
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
