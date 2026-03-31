"""Service layer for persisting run history to Oracle DB."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_RUN_HISTORY_PATH = Path("reports") / "run_history.json"


def load_run_history() -> list[dict[str, Any]]:
    """Load run history from Oracle DB or the JSON fallback file.

    Tries the database path first when ``ORACLE_USER`` is set, then falls
    back to reading ``reports/run_history.json``.  Returns all available
    entries — callers are responsible for any time-window filtering.

    Returns:
        List of run history entry dicts, each containing at minimum:
        ``run_id``, ``suite_name``, ``timestamp``, ``status``.
        Returns an empty list if no data source is available.
    """
    if os.getenv("ORACLE_USER"):
        try:
            return fetch_history_from_db(limit=1000)
        except Exception:
            pass

    if not _RUN_HISTORY_PATH.exists():
        return []
    try:
        return json.loads(_RUN_HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def write_run_to_db(
    entry: dict[str, Any],
    run_id: str,
    results: list[dict[str, Any]],
) -> None:
    """Persist run summary and per-test rows to Oracle.

    Thin service wrapper so the commands layer does not import the
    database layer directly (preserving the CLI/API → Commands →
    Services → DB layering from the architecture principles).

    Args:
        entry: Run summary dict with keys matching run_history.json entries.
        run_id: UUID of the run (used as foreign key for test rows).
        results: List of per-test result dicts from ``_run_single_test``.
    """
    from src.database.run_history import RunHistoryRepository

    repo = RunHistoryRepository()
    repo.insert_run(entry)
    repo.insert_tests(run_id, results)


def fetch_history_from_db(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent run summaries from Oracle.

    Args:
        limit: Maximum number of rows to return (default 20).

    Returns:
        List of run summary dicts, newest first.
    """
    from src.database.run_history import RunHistoryRepository

    repo = RunHistoryRepository()
    return repo.fetch_history(limit=limit)
