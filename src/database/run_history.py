"""Oracle-backed persistence for test suite run history."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .connection import OracleConnection

logger = logging.getLogger(__name__)

_INSERT_RUN = """
INSERT INTO CM3INT.CM3_RUN_HISTORY
  (RUN_ID, SUITE_NAME, ENVIRONMENT, RUN_TIMESTAMP, STATUS,
   PASS_COUNT, FAIL_COUNT, SKIP_COUNT, TOTAL_COUNT, REPORT_URL, ARCHIVE_PATH)
VALUES
  (:run_id, :suite_name, :environment, :run_timestamp, :status,
   :pass_count, :fail_count, :skip_count, :total_count, :report_url, :archive_path)
"""

_INSERT_TEST = """
INSERT INTO CM3INT.CM3_RUN_TESTS
  (RUN_ID, TEST_NAME, TEST_TYPE, STATUS, ROW_COUNT, ERROR_COUNT, DURATION_SECS, REPORT_PATH)
VALUES
  (:run_id, :test_name, :test_type, :status, :row_count, :error_count, :duration_secs, :report_path)
"""

_FETCH_HISTORY = """
SELECT RUN_ID, SUITE_NAME, ENVIRONMENT, RUN_TIMESTAMP, STATUS,
       PASS_COUNT, FAIL_COUNT, SKIP_COUNT, TOTAL_COUNT, REPORT_URL, ARCHIVE_PATH
FROM CM3INT.CM3_RUN_HISTORY
ORDER BY RUN_TIMESTAMP DESC
FETCH FIRST :limit ROWS ONLY
"""


def _parse_ts(ts_str: str) -> datetime:
    """Parse ISO-8601 UTC string (with or without trailing Z) to aware datetime.

    Args:
        ts_str: UTC timestamp string, e.g. ``'2026-03-02T10:00:00.000000Z'``.

    Returns:
        Timezone-aware datetime in UTC.

    Raises:
        ValueError: If ts_str contains an explicit non-UTC offset.
    """
    if "+" in ts_str:
        raise ValueError(f"_parse_ts expects a UTC string, got: {ts_str!r}")
    return datetime.fromisoformat(ts_str.rstrip("Z")).replace(tzinfo=timezone.utc)


def _ts_to_iso(value: Any) -> Any:
    """Convert a datetime to ISO-8601 UTC string; pass non-datetime values through.

    Args:
        value: A datetime instance or any other value.

    Returns:
        ISO-8601 string ending in ``'Z'`` if value is a datetime,
        otherwise the original value unchanged.
    """
    if isinstance(value, datetime):
        ts = value.astimezone(timezone.utc)
        return ts.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    return value


class RunHistoryRepository:
    """Reads and writes suite run history to/from Oracle.

    Args:
        conn: Optional OracleConnection to use. Defaults to OracleConnection.from_env().

    Example::

        repo = RunHistoryRepository()
        repo.insert_run(entry)
        repo.insert_tests(run_id, results)
        history = repo.fetch_history(limit=20)
    """

    def __init__(self, conn: OracleConnection | None = None) -> None:
        self._conn = conn if conn is not None else OracleConnection.from_env()

    def insert_run(self, entry: dict[str, Any]) -> None:
        """Insert one run summary row into CM3INT.CM3_RUN_HISTORY.

        Args:
            entry: Dict with keys matching run_history.json entries.
        """
        with self._conn as conn:
            cursor = conn.cursor()
            cursor.execute(_INSERT_RUN, {
                "run_id":        entry["run_id"],
                "suite_name":    entry["suite_name"],
                "environment":   entry["environment"],
                "run_timestamp": _parse_ts(entry["timestamp"]),
                "status":        entry["status"],
                "pass_count":    entry.get("pass_count", 0),
                "fail_count":    entry.get("fail_count", 0),
                "skip_count":    entry.get("skip_count", 0),
                "total_count":   entry.get("total_count", 0),
                "report_url":    entry.get("report_url", ""),
                "archive_path":  entry.get("archive_path", ""),
            })
            conn.commit()

    def insert_tests(self, run_id: str, results: list[dict[str, Any]]) -> None:
        """Insert one row per test into CM3INT.CM3_RUN_TESTS.

        Args:
            run_id: The parent run UUID.
            results: List of per-test result dicts from _run_single_test.
        """
        if not results:
            return
        rows = [
            {
                "run_id":        run_id,
                "test_name":     r.get("name", ""),
                "test_type":     r.get("type", ""),
                "status":        r.get("status", ""),
                "row_count":     r.get("rows_processed"),
                "error_count":   r.get("error_count", 0),
                "duration_secs": r.get("duration_secs"),
                "report_path":   r.get("report_path", ""),
            }
            for r in results
        ]
        with self._conn as conn:
            cursor = conn.cursor()
            cursor.executemany(_INSERT_TEST, rows)
            conn.commit()

    def fetch_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most recent run summaries from CM3INT.CM3_RUN_HISTORY.

        Args:
            limit: Maximum number of rows to return (default 20).

        Returns:
            List of dicts with the same keys as run_history.json entries,
            ordered newest-first.
        """
        with self._conn as conn:
            cursor = conn.cursor()
            cursor.execute(_FETCH_HISTORY, {"limit": limit})
            cols = [d[0].lower() for d in cursor.description]
            rows = cursor.fetchall()

        result = []
        for row in rows:
            d = dict(zip(cols, row))
            # Normalize RUN_TIMESTAMP (Oracle returns datetime) → ISO string, rename key
            if "run_timestamp" in d:
                d["timestamp"] = _ts_to_iso(d.pop("run_timestamp"))
            result.append(d)
        return result
