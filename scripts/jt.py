#!/usr/bin/env python3
"""Run the jobtracker CLI straight from the clone: `python scripts/jt.py doctor`.

Works before anything is installed (the core needs only the standard library).
Once the project's virtual environment exists (.venv), the command is handed
over to it so installed packages are available.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"


def venv_python() -> Path | None:
    for candidate in (VENV / "Scripts" / "python.exe", VENV / "bin" / "python"):
        if candidate.is_file():
            return candidate
    return None


if __name__ == "__main__":
    python = venv_python()
    inside_venv = Path(sys.prefix).resolve() == VENV.resolve()
    if python and not inside_venv and not os.environ.get("JOBTRACKER_NO_VENV"):
        sys.exit(subprocess.call([str(python), __file__, *sys.argv[1:]]))

    os.environ.setdefault("JOBTRACKER_PROG", "python scripts/jt.py")
    sys.path.insert(0, str(ROOT / "src"))
    from jobtracker.cli.main import main

    sys.exit(main())
