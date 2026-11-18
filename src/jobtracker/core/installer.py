"""Install what an enabled provider needs, so a search never fails because a tool is
missing: the agent runs `jt providers install`, the user never installs by hand.

Only the tools listed here are installed, into the Python that runs this command (the
project's own environment). Each install ends with a check that the tool really works.
"""
from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable

from . import doctor, providers
from .errors import JobTrackerError
from .paths import Paths

Runner = Callable[[list[str]], tuple[int, str]]

SMOKE_SCRAPLING = ("from scrapling.fetchers import StealthySession\n"
                   "s = StealthySession(headless=True)\n"
                   "s.__enter__()\n"
                   "s.__exit__(None, None, None)\n"
                   "print('ok')\n")
SMOKE_PLAYWRIGHT = ("from playwright.sync_api import sync_playwright\n"
                    "with sync_playwright() as p:\n"
                    "    p.chromium.launch(headless=True).close()\n"
                    "print('ok')\n")


def steps(tool: str) -> dict | None:
    """The commands that install `tool` and the check that proves it works."""
    python = sys.executable
    known = {
        "scrapling": {
            "size": "about 150 MB (the package and its browser)",
            "install": [[python, "-m", "pip", "install", "scrapling[fetchers]"],
                        [python, "-m", "patchright", "install", "chromium"]],
            "check": [python, "-c", SMOKE_SCRAPLING],
        },
        "playwright": {
            "size": "about 150 MB (the package and Chromium)",
            "install": [[python, "-m", "pip", "install", "playwright"],
                        [python, "-m", "playwright", "install", "chromium"]],
            "check": [python, "-c", SMOKE_PLAYWRIGHT],
        },
    }
    return known.get(tool)


def run_command(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=1800,
                            check=False)
    return result.returncode, (result.stdout + result.stderr)[-2000:]


def install(paths: Paths, provider_id: str | None = None, *, enabled: bool = False,
            runner: Runner = run_command) -> dict:
    """Install the missing tools of one provider, or of every enabled provider."""
    listed = {str(p["id"]): p for p in providers.list_providers()}
    if enabled:
        targets = sorted(doctor._enabled_provider_ids(paths) & set(listed))
    elif provider_id:
        if provider_id not in listed:
            raise JobTrackerError("not_found", f"There is no provider '{provider_id}'")
        targets = [provider_id]
    else:
        raise JobTrackerError("usage", "give a provider id, or --enabled")
    report = []
    done: dict[str, dict] = {}
    for target in targets:
        item = {"provider": target, "installed": [], "already": [], "failed": [],
                "unknown": []}
        for tool in [str(d) for d in listed[target].get("dependencies") or []]:
            if tool in done:
                (item["installed"] if done[tool]["ok"] else item["failed"]).append(
                    done[tool] if not done[tool]["ok"] else tool)
                continue
            if doctor._tool_available(tool):
                item["already"].append(tool)
                continue
            recipe = steps(tool)
            if recipe is None:
                item["unknown"].append({"tool": tool, "how": providers.install_hint(
                    tool, str(listed[target]["file"]))})
                continue
            outcome = {"tool": tool, "ok": True, "size": recipe["size"], "detail": None}
            for command in [*recipe["install"], recipe["check"]]:
                code, output = runner(command)
                if code != 0:
                    outcome.update(ok=False, detail=f"`{' '.join(command[1:4])}…` failed: "
                                                    f"{output.strip()[-400:]}")
                    break
            done[tool] = outcome
            if outcome["ok"]:
                item["installed"].append(tool)
            else:
                item["failed"].append(outcome)
        item["ok"] = not item["failed"] and not item["unknown"]
        report.append(item)
    installed = sorted({tool for r in report for tool in r["installed"]})
    return {"providers": report, "installed": installed,
            "sizes": {tool: done[tool]["size"] for tool in installed},
            "ok": all(r["ok"] for r in report)}
