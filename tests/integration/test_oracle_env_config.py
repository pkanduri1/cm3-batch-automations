"""Integration-style checks for Oracle env configuration."""

import os
import pytest

from src.database.connection import OracleConnection


def test_oracle_connection_from_env_uses_defaults_when_not_set(monkeypatch):
    monkeypatch.delenv("ORACLE_USER", raising=False)
    monkeypatch.delenv("ORACLE_DSN", raising=False)

    conn = OracleConnection.from_env()

    assert conn.username == "CM3INT"
    assert conn.dsn == "localhost:1521/FREEPDB1"


@pytest.mark.skipif(
    not (os.getenv("ORACLE_USER") and os.getenv("ORACLE_PASSWORD") and os.getenv("ORACLE_DSN")),
    reason="Oracle environment not configured",
)
def test_oracle_connection_attempts_configured_dsn():
    conn = OracleConnection.from_env()
    # Connection creation should at least carry configured DSN in runtime object.
    assert conn.dsn == os.getenv("ORACLE_DSN")
