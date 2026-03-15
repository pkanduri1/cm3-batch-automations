"""Unit tests for src.utils.audit_logger."""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.utils.audit_logger import (
    AuditEvent,
    AuditLogger,
    sha256_hex,
    get_audit_logger,
    AUDIT_LOG_PATH,
    file_sha256,
)


# ---------------------------------------------------------------------------
# sha256_hex helper
# ---------------------------------------------------------------------------

class TestSha256Hex:
    """Tests for the sha256_hex hashing helper."""

    def test_bytes_input(self):
        data = b"hello world"
        expected = hashlib.sha256(data).hexdigest()
        assert sha256_hex(data) == expected

    def test_string_input(self):
        data = "hello world"
        expected = hashlib.sha256(data.encode("utf-8")).hexdigest()
        assert sha256_hex(data) == expected

    def test_empty_input(self):
        assert sha256_hex(b"") == hashlib.sha256(b"").hexdigest()

    def test_deterministic(self):
        assert sha256_hex("abc") == sha256_hex("abc")

    def test_different_inputs_differ(self):
        assert sha256_hex("a") != sha256_hex("b")


class TestFileSha256:
    """Tests for hashing files by path."""

    def test_returns_hash_for_existing_file(self, tmp_path):
        target = tmp_path / "sample.txt"
        target.write_text("abc123", encoding="utf-8")
        assert file_sha256(target) == hashlib.sha256(b"abc123").hexdigest()

    def test_returns_none_for_missing_file(self, tmp_path):
        assert file_sha256(tmp_path / "missing.txt") is None


# ---------------------------------------------------------------------------
# AuditEvent dataclass
# ---------------------------------------------------------------------------

class TestAuditEvent:
    """Tests for AuditEvent construction and serialization."""

    def test_required_fields(self):
        evt = AuditEvent(event_type="test.started", actor="cli")
        assert evt.event_type == "test.started"
        assert evt.actor == "cli"
        assert evt.event_id  # auto-generated UUID
        assert evt.timestamp  # auto-generated ISO timestamp

    def test_optional_detail(self):
        evt = AuditEvent(event_type="x", actor="api", detail={"key": "val"})
        assert evt.detail == {"key": "val"}

    def test_to_dict_contains_all_fields(self):
        evt = AuditEvent(
            event_type="file.upload",
            actor="api",
            detail={"filename": "test.csv"},
            source_ip="10.0.0.1",
        )
        d = evt.to_dict()
        assert d["event_type"] == "file.upload"
        assert d["actor"] == "api"
        assert d["source_ip"] == "10.0.0.1"
        assert d["detail"]["filename"] == "test.csv"
        assert "event_id" in d
        assert "timestamp" in d

    def test_to_json_is_valid(self):
        evt = AuditEvent(event_type="x", actor="cli")
        parsed = json.loads(evt.to_json())
        assert parsed["event_type"] == "x"

    def test_hash_field_populated(self):
        evt = AuditEvent(event_type="x", actor="cli", detail={"a": 1})
        d = evt.to_dict()
        assert "event_hash" in d
        # Hash should be SHA-256 of the canonical JSON payload
        assert len(d["event_hash"]) == 64

    def test_hash_deterministic(self):
        kwargs = dict(event_type="x", actor="cli", detail={"a": 1})
        e1 = AuditEvent(**kwargs)
        e2 = AuditEvent(**kwargs)
        # Different event_id / timestamp → different hash, that's fine
        # But same event should produce consistent hash per call
        d = e1.to_dict()
        assert d["event_hash"] == e1.to_dict()["event_hash"]


# ---------------------------------------------------------------------------
# AuditLogger
# ---------------------------------------------------------------------------

class TestAuditLogger:
    """Tests for the AuditLogger wrapper."""

    def test_emit_writes_json_line(self, tmp_path):
        log_path = tmp_path / "audit.log"
        al = AuditLogger(log_path=str(log_path))

        al.emit(event_type="cli.test_run.started", actor="cli", detail={"suite": "smoke"})

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["event_type"] == "cli.test_run.started"
        assert parsed["actor"] == "cli"

    def test_emit_multiple_events(self, tmp_path):
        log_path = tmp_path / "audit.log"
        al = AuditLogger(log_path=str(log_path))

        al.emit(event_type="a", actor="cli")
        al.emit(event_type="b", actor="api")

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_emit_creates_parent_dirs(self, tmp_path):
        log_path = tmp_path / "nested" / "deep" / "audit.log"
        al = AuditLogger(log_path=str(log_path))
        al.emit(event_type="x", actor="cli")
        assert log_path.exists()

    def test_emit_returns_event(self, tmp_path):
        log_path = tmp_path / "audit.log"
        al = AuditLogger(log_path=str(log_path))
        evt = al.emit(event_type="y", actor="api", source_ip="1.2.3.4")
        assert isinstance(evt, AuditEvent)
        assert evt.source_ip == "1.2.3.4"

    def test_default_log_path_from_env(self, tmp_path, monkeypatch):
        custom = str(tmp_path / "custom_audit.log")
        monkeypatch.setenv("AUDIT_LOG_PATH", custom)
        al = get_audit_logger()
        al.emit(event_type="z", actor="cli")
        assert Path(custom).exists()

    def test_cli_test_run_started_event(self, tmp_path):
        log_path = tmp_path / "audit.log"
        al = AuditLogger(log_path=str(log_path))
        al.emit(
            event_type="cli.test_run.started",
            actor="cli",
            detail={"suite": "regression", "env": "dev"},
        )
        parsed = json.loads(log_path.read_text().strip())
        assert parsed["event_type"] == "cli.test_run.started"
        assert parsed["detail"]["suite"] == "regression"

    def test_cli_test_run_completed_event(self, tmp_path):
        log_path = tmp_path / "audit.log"
        al = AuditLogger(log_path=str(log_path))
        al.emit(
            event_type="cli.test_run.completed",
            actor="cli",
            detail={"suite": "smoke", "passed": 5, "failed": 1, "status": "FAILED"},
        )
        parsed = json.loads(log_path.read_text().strip())
        assert parsed["event_type"] == "cli.test_run.completed"
        assert parsed["detail"]["status"] == "FAILED"

    def test_api_test_run_event(self, tmp_path):
        log_path = tmp_path / "audit.log"
        al = AuditLogger(log_path=str(log_path))
        al.emit(
            event_type="api.test_run",
            actor="api",
            source_ip="192.168.1.10",
            detail={"endpoint": "/api/v1/files/validate", "mapping_id": "p327"},
        )
        parsed = json.loads(log_path.read_text().strip())
        assert parsed["source_ip"] == "192.168.1.10"

    def test_api_auth_failure_event(self, tmp_path):
        log_path = tmp_path / "audit.log"
        al = AuditLogger(log_path=str(log_path))
        al.emit(
            event_type="api.auth_failure",
            actor="api",
            source_ip="10.0.0.99",
            detail={"reason": "invalid_token", "path": "/api/v1/files/validate"},
        )
        parsed = json.loads(log_path.read_text().strip())
        assert parsed["event_type"] == "api.auth_failure"
        assert parsed["source_ip"] == "10.0.0.99"

    def test_file_upload_event(self, tmp_path):
        log_path = tmp_path / "audit.log"
        al = AuditLogger(log_path=str(log_path))
        al.emit(
            event_type="file.upload",
            actor="api",
            detail={
                "filename": "data.csv",
                "size_bytes": 1024,
                "content_hash": sha256_hex(b"file content"),
            },
        )
        parsed = json.loads(log_path.read_text().strip())
        assert parsed["event_type"] == "file.upload"
        assert parsed["detail"]["size_bytes"] == 1024

    def test_file_cleanup_event(self, tmp_path):
        log_path = tmp_path / "audit.log"
        al = AuditLogger(log_path=str(log_path))
        al.emit(
            event_type="file.cleanup",
            actor="system",
            detail={"deleted_count": 3, "deleted_bytes": 8192},
        )
        parsed = json.loads(log_path.read_text().strip())
        assert parsed["event_type"] == "file.cleanup"
        assert parsed["detail"]["deleted_count"] == 3

    def test_source_ip_defaults_to_none(self, tmp_path):
        log_path = tmp_path / "audit.log"
        al = AuditLogger(log_path=str(log_path))
        evt = al.emit(event_type="x", actor="cli")
        assert evt.source_ip is None
        parsed = json.loads(log_path.read_text().strip())
        assert parsed.get("source_ip") is None


# ---------------------------------------------------------------------------
# get_audit_logger singleton
# ---------------------------------------------------------------------------

class TestGetAuditLogger:
    """Tests for the module-level get_audit_logger factory."""

    def test_returns_audit_logger_instance(self):
        al = get_audit_logger()
        assert isinstance(al, AuditLogger)

    def test_uses_default_path_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("AUDIT_LOG_PATH", raising=False)
        al = get_audit_logger()
        assert al.log_path == AUDIT_LOG_PATH

    def test_uses_env_override(self, tmp_path, monkeypatch):
        custom = str(tmp_path / "override.log")
        monkeypatch.setenv("AUDIT_LOG_PATH", custom)
        al = get_audit_logger()
        assert al.log_path == custom
