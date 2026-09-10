#!/usr/bin/env python
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
VENV_PYTHON = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python"

if VENV_PYTHON.exists():
    try:
        current_python = Path(sys.executable).resolve()
        venv_python = VENV_PYTHON.resolve()
    except Exception:
        current_python = None
        venv_python = None

    if venv_python and current_python != venv_python:
        script_path = ROOT_DIR / "manage.py"
        if not script_path.exists():
            script_path = Path(__file__).resolve()
        import subprocess

        result = subprocess.run(
            [str(venv_python), str(script_path)] + sys.argv[1:]
        )
        sys.exit(result.returncode)

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_site.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and available on your PYTHONPATH? "
            "Did you forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
