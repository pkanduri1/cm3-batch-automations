"""FastAPI main application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.routers import mappings, files, system, tasks
from src.api.routers.ui import router as ui_router
from src.api.routers.runs import router as runs_router
from src.api.routers import rules as rules_router_mod
from src.api.routers.api_tester import router as api_tester_router
from src.utils.cleanup import cleanup_old_files
from src.utils.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)
_audit = get_audit_logger()

FILE_RETENTION_HOURS = float(os.getenv("FILE_RETENTION_HOURS", "24"))
_UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler: runs startup cleanup, then yields."""
    # Startup: remove stale uploaded files
    result = cleanup_old_files(_UPLOADS_DIR, FILE_RETENTION_HOURS)
    if result["deleted_count"] > 0:
        logger.info(
            "Startup cleanup: removed %d files (%d bytes)",
            result["deleted_count"],
            result["deleted_bytes"],
        )
        _audit.emit(
            event_type="file.cleanup",
            actor="system",
            detail={
                "deleted_count": result["deleted_count"],
                "deleted_bytes": result["deleted_bytes"],
                "trigger": "startup",
            },
        )
    yield
    # Shutdown: nothing needed


# Create FastAPI application
app = FastAPI(
    lifespan=lifespan,
    title="CM3 Batch Automations API",
    description="""
    REST API for CM3 Batch Automations - File parsing, validation, and comparison tool.
    
    ## Features
    
    * **Universal Mapping Management**: Create and manage file mappings
    * **File Operations**: Parse, validate, and compare files
    * **Format Detection**: Automatically detect file formats
    * **Database Integration**: Oracle database connectivity
    * **Report Generation**: Generate HTML comparison reports
    
    ## Getting Started
    
    1. Upload an Excel/CSV template to create a mapping
    2. Use the mapping to parse and validate files
    3. Compare files and generate reports
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class AuditMiddleware(BaseHTTPMiddleware):
    """Emit audit events for API requests that trigger auth failures."""

    async def dispatch(self, request: Request, call_next):
        """Log auth failures (401/403) with client IP."""
        response: Response = await call_next(request)
        if response.status_code in (401, 403):
            _audit.emit(
                event_type="api.auth_failure",
                actor="api",
                source_ip=request.client.host if request.client else None,
                detail={
                    "path": str(request.url.path),
                    "method": request.method,
                    "status_code": response.status_code,
                },
            )
        return response


app.add_middleware(AuditMiddleware)

# Include routers
app.include_router(
    mappings.router,
    prefix="/api/v1/mappings",
    tags=["Mappings"]
)
app.include_router(
    files.router,
    prefix="/api/v1/files",
    tags=["Files"]
)
app.include_router(
    system.router,
    prefix="/api/v1/system",
    tags=["System"]
)
app.include_router(
    tasks.router,
    prefix="/api/v1/tasks",
    tags=["Tasks"]
)
app.include_router(ui_router)
app.include_router(runs_router)
app.include_router(
    rules_router_mod.router,
    prefix="/api/v1/rules",
    tags=["Rules"]
)
app.include_router(api_tester_router)

# Serve generated reports
_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_UPLOADS_DIR)), name="uploads")
_REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"
_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(_REPORTS_DIR)), name="reports")

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information."""
    return {
        "name": "CM3 Batch Automations API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/system/health"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "details": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
