"""Structured audit logging with JSON events and SHA-256 integrity hashing.

Emits one-JSON-object-per-line audit events to a configurable log file.
Designed for ingestion by Splunk, ELK, or any JSON-capable log aggregator.

Configuration:
    Set ``AUDIT_LOG_PATH`` environment variable to override the default
    log file location (``logs/audit.log``).

Example event::

    {
        "event_id": "a1b2c3...",
        "timestamp": "2026-03-14T12:00:00+00:00",
        "event_type": "cli.test_run.started",
        "actor": "cli",
        "source_ip": null,
        "detail": {"suite": "smoke", "env": "dev"},
        "event_hash": "e3b0c44..."
    }
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def file_sha256(path: str | Path) -> str | None:
    """Return SHA-256 hex for a file path.

    Args:
        path: File path to hash.

    Returns:
        Hex digest string when the file exists and is readable; otherwise ``None``.
    """
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None

    hasher = hashlib.sha256()
    with open(file_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# Default audit log path — overridable via AUDIT_LOG_PATH env var.
AUDIT_LOG_PATH: str = os.getenv("AUDIT_LOG_PATH", "logs/audit.log")


def sha256_hex(data: bytes | str) -> str:
    """Return the SHA-256 hex digest of *data*.

    Args:
        data: Raw bytes or a UTF-8 string to hash.

    Returns:
        Lowercase hex string (64 characters).
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


@dataclass
class AuditEvent:
    """Immutable audit event with automatic ID, timestamp, and integrity hash.

    Args:
        event_type: Dot-namespaced event category
            (e.g. ``cli.test_run.started``, ``api.auth_failure``).
        actor: Originator — ``cli``, ``api``, or ``system``.
        detail: Arbitrary key/value payload for the event.
        source_ip: Client IP address (API events only).
    """

    event_type: str
    actor: str
    detail: dict[str, Any] | None = None
    source_ip: str | None = None
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event to a dictionary with an ``event_hash`` field.

        Returns:
            Dict containing all event fields plus a SHA-256 ``event_hash``
            computed over the canonical JSON representation.
        """
        payload: dict[str, Any] = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor,
            "source_ip": self.source_ip,
            "detail": self.detail,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload["event_hash"] = sha256_hex(canonical)
        return payload

    def to_json(self) -> str:
        """Serialize the event to a single-line JSON string.

        Returns:
            JSON string suitable for appending to an audit log file.
        """
        return json.dumps(self.to_dict(), separators=(",", ":"))


class AuditLogger:
    """Append-only JSON audit logger backed by a file.

    Each call to :meth:`emit` writes one JSON object per line.  Parent
    directories are created on first write if they do not exist.

    Args:
        log_path: Filesystem path for the audit log file.
    """

    def __init__(self, log_path: str | None = None) -> None:
        self.log_path: str = log_path or os.getenv("AUDIT_LOG_PATH", AUDIT_LOG_PATH)

    def emit(
        self,
        event_type: str,
        actor: str,
        detail: dict[str, Any] | None = None,
        source_ip: str | None = None,
    ) -> AuditEvent:
        """Create and persist an audit event.

        Args:
            event_type: Dot-namespaced event category.
            actor: Originator — ``cli``, ``api``, or ``system``.
            detail: Arbitrary key/value payload.
            source_ip: Client IP address (API events).

        Returns:
            The :class:`AuditEvent` that was written.
        """
        event = AuditEvent(
            event_type=event_type,
            actor=actor,
            detail=detail,
            source_ip=source_ip,
        )
        path = Path(self.log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(event.to_json() + "\n")
        return event


def get_audit_logger() -> AuditLogger:
    """Return an :class:`AuditLogger` configured from the environment.

    The log path is read from the ``AUDIT_LOG_PATH`` environment variable,
    falling back to the module-level :data:`AUDIT_LOG_PATH` default.

    Returns:
        A ready-to-use :class:`AuditLogger` instance.
    """
    return AuditLogger(log_path=os.getenv("AUDIT_LOG_PATH", AUDIT_LOG_PATH))
