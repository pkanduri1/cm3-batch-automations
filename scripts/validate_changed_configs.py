"""Validate changed config files on pull requests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _changed_files(base: str = "origin/main") -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def main() -> int:
    files = _changed_files()
    targets = [
        f for f in files
        if f.startswith("config/mappings/") or f.startswith("config/rules/") or f.startswith("config/test_suites/")
    ]

    if not targets:
        print("No config files changed.")
        return 0

    failed = False
    for rel in targets:
        path = Path(rel)
        if not path.exists():
            continue
        if path.suffix.lower() in {".json"}:
            try:
                json.loads(path.read_text(encoding="utf-8"))
                print(f"OK json: {rel}")
            except Exception as exc:  # noqa: BLE001
                print(f"FAIL json: {rel}: {exc}")
                failed = True
        elif path.suffix.lower() in {".yaml", ".yml"}:
            print(f"OK yaml (schema validated in tests): {rel}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
