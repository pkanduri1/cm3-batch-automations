"""Unit tests for RunHistoryRepository — all Oracle calls are mocked."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest


SAMPLE_ENTRY = {
    "run_id": "abc-123",
    "suite_name": "My Suite",
    "environment": "uat",
    "timestamp": "2026-03-02T10:00:00.000000Z",
    "status": "PASS",
    "pass_count": 3,
    "fail_count": 0,
    "skip_count": 1,
    "total_count": 4,
    "report_url": "/reports/My_Suite_abc-123_suite.html",
    "archive_path": "/reports/archive/2026/03/02/abc-123",
}

SAMPLE_RESULTS = [
    {"name": "Test A", "type": "structural", "status": "PASS",
     "rows_processed": 100, "error_count": 0, "duration_secs": 0.5, "report_path": ""},
    {"name": "Test B", "type": "api_check", "status": "FAIL",
     "rows_processed": None, "error_count": 1, "duration_secs": 0.1, "report_path": ""},
]


def _make_repo():
    """Return a RunHistoryRepository with a fully mocked OracleConnection."""
    from src.database.run_history import RunHistoryRepository
    mock_conn = MagicMock()          # stands in for OracleConnection (the wrapper)
    mock_raw_conn = MagicMock()      # stands in for the raw oracledb.Connection
    mock_cursor = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_raw_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_raw_conn.cursor.return_value = mock_cursor
    repo = RunHistoryRepository(conn=mock_conn)
    return repo, mock_raw_conn, mock_cursor


class TestInsertRun:
    def test_executes_insert_with_correct_params(self):
        repo, mock_conn, mock_cursor = _make_repo()
        repo.insert_run(SAMPLE_ENTRY)
        assert mock_cursor.execute.called
        sql, params = mock_cursor.execute.call_args.args
        assert "CM3INT.CM3_RUN_HISTORY" in sql
        assert params["run_id"] == "abc-123"
        assert params["suite_name"] == "My Suite"
        assert params["status"] == "PASS"
        assert params["pass_count"] == 3
        assert params["total_count"] == 4

    def test_timestamp_converted_to_datetime(self):
        repo, mock_conn, mock_cursor = _make_repo()
        repo.insert_run(SAMPLE_ENTRY)
        _, params = mock_cursor.execute.call_args.args
        assert isinstance(params["run_timestamp"], datetime)
        assert params["run_timestamp"].tzinfo is not None

    def test_commits_after_insert(self):
        repo, mock_raw_conn, mock_cursor = _make_repo()
        repo.insert_run(SAMPLE_ENTRY)
        mock_raw_conn.commit.assert_called_once()


class TestInsertTests:
    def test_executemany_called_with_all_rows(self):
        repo, mock_conn, mock_cursor = _make_repo()
        repo.insert_tests("abc-123", SAMPLE_RESULTS)
        assert mock_cursor.executemany.called
        sql, rows = mock_cursor.executemany.call_args.args
        assert "CM3INT.CM3_RUN_TESTS" in sql
        assert len(rows) == 2
        assert rows[0]["run_id"] == "abc-123"
        assert rows[0]["test_name"] == "Test A"
        assert rows[1]["status"] == "FAIL"

    def test_empty_results_skips_db_call(self):
        repo, mock_conn, mock_cursor = _make_repo()
        repo.insert_tests("abc-123", [])
        mock_cursor.executemany.assert_not_called()

    def test_commits_after_insert(self):
        repo, mock_raw_conn, mock_cursor = _make_repo()
        repo.insert_tests("abc-123", SAMPLE_RESULTS)
        mock_raw_conn.commit.assert_called_once()


class TestFetchHistory:
    def test_returns_list_of_dicts(self):
        repo, mock_conn, mock_cursor = _make_repo()
        mock_cursor.description = [
            ("RUN_ID",), ("SUITE_NAME",), ("ENVIRONMENT",), ("RUN_TIMESTAMP",),
            ("STATUS",), ("PASS_COUNT",), ("FAIL_COUNT",), ("SKIP_COUNT",),
            ("TOTAL_COUNT",), ("REPORT_URL",), ("ARCHIVE_PATH",),
        ]
        mock_cursor.fetchall.return_value = [
            ("abc-123", "My Suite", "uat", datetime(2026, 3, 2, 10, 0, 0, tzinfo=timezone.utc),
             "PASS", 3, 0, 1, 4, "/reports/x.html", "/archive/abc-123"),
        ]
        results = repo.fetch_history(limit=20)
        assert len(results) == 1
        assert results[0]["run_id"] == "abc-123"
        assert results[0]["status"] == "PASS"

    def test_timestamp_serialized_to_iso_string(self):
        repo, mock_conn, mock_cursor = _make_repo()
        mock_cursor.description = [("RUN_ID",), ("RUN_TIMESTAMP",)]
        mock_cursor.fetchall.return_value = [
            ("abc-123", datetime(2026, 3, 2, 10, 0, 0, tzinfo=timezone.utc)),
        ]
        results = repo.fetch_history()
        assert isinstance(results[0]["timestamp"], str)
        assert "2026" in results[0]["timestamp"]

    def test_passes_limit_to_query(self):
        repo, mock_conn, mock_cursor = _make_repo()
        mock_cursor.description = []
        mock_cursor.fetchall.return_value = []
        repo.fetch_history(limit=5)
        _, params = mock_cursor.execute.call_args.args
        assert params.get("limit") == 5
