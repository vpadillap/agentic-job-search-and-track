#!/usr/bin/env python3
"""Run the jobtracker CLI straight from the clone, before anything is installed.

    python scripts/jt.py doctor

Once dependencies are installed, `jobtracker <command>` does the same.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jobtracker.cli.main import main  # noqa: E402

sys.exit(main())
