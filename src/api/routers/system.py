"""System endpoints - health check and system information."""

from datetime import UTC, datetime
import os
import sys

from fastapi import APIRouter

from src.api.models.response import HealthResponse, SystemInfoResponse

router = APIRouter()


def _db_signals() -> tuple[bool, bool, str]:
    """Return (database_connected, database_configured, message)."""
    configured = bool(os.getenv("ORACLE_USER") and os.getenv("ORACLE_DSN"))
    if not configured:
        return False, False, "ORACLE_USER/ORACLE_DSN not configured"

    try:
        import oracledb  # type: ignore

        # lightweight signal: driver available + config present.
        return True, True, f"oracledb {oracledb.__version__} available; configuration detected"
    except Exception as e:
        return False, True, f"driver/config check failed: {e}"


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with runtime signals."""
    db_connected, db_configured, msg = _db_signals()
    checks = {
        "api": {"ok": True},
        "database": {
            "ok": db_connected,
            "configured": db_configured,
            "message": msg,
        },
    }

    status = "healthy" if checks["api"]["ok"] else "degraded"
    return HealthResponse(
        status=status,
        version="1.0.0",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        checks=checks,
    )


@router.get("/info", response_model=SystemInfoResponse)
async def system_info():
    """Get system information."""
    db_connected, db_configured, msg = _db_signals()
    return SystemInfoResponse(
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        api_version="1.0.0",
        supported_formats=["pipe_delimited", "fixed_width", "csv", "tsv"],
        database_connected=db_connected,
        database_configured=db_configured,
        database_message=msg,
    )
