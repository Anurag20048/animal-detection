"""Restore the complete backend source from the supplied backend.zip archive.

This helper preserves the Phase 2/3 files already tracked in the repository and
copies only source/configuration files that are missing from the checkout.
It intentionally excludes .venv, caches, generated runtime data, databases,
and model binaries.

Usage:
    python scripts/restore_from_archive.py path/to/backend.zip
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

EXCLUDED_PARTS = {".venv", "__pycache__"}
EXCLUDED_SUFFIXES = {".pyc", ".db"}
EXCLUDED_PREFIXES = ("backend/data/",)
EXCLUDED_BINARY_SUFFIXES = {".pt", ".onnx", ".pth"}


def should_restore(name: str) -> bool:
    path = Path(name)
    if not name.startswith("backend/") or name.endswith("/"):
        return False
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return False
    if name.startswith(EXCLUDED_PREFIXES):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES | EXCLUDED_BINARY_SUFFIXES:
        return False
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/restore_from_archive.py path/to/backend.zip")
        return 2

    archive = Path(sys.argv[1]).expanduser().resolve()
    if not archive.is_file():
        print(f"Archive not found: {archive}")
        return 1

    repo_root = Path(__file__).resolve().parents[1]
    restored = 0
    skipped_existing = 0

    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            if not should_restore(member.filename):
                continue
            destination = repo_root / member.filename
            if destination.exists():
                skipped_existing += 1
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as source, destination.open("wb") as target:
                target.write(source.read())
            restored += 1
            print(f"restored: {member.filename}")

    print(f"Restored {restored} missing source files; preserved {skipped_existing} existing files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
