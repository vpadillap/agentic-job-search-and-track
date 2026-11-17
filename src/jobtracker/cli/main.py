"""`jobtracker <command>`: JSON on stdout, diagnostics on stderr, non-zero on failure.

Success: {"ok": true, ...}. Failure: {"ok": false, "error": {"code", "message"}}.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jobtracker.core import config, context, db, doctor, rules, workspace
from jobtracker.core.errors import JobTrackerError
from jobtracker.core.paths import get_paths, next_version_path

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
        text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
        return json.loads(text)
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
    return {"config": settings}


def cmd_rules_list(args: argparse.Namespace) -> dict:
    status = None if args.status == "all" else args.status
    with db.session(get_paths()) as conn:
        return {"rules": rules.list_rules(conn, status)}


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
    parser = _Parser(prog="jobtracker", description="Job Tracker data interface for agents.")
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
