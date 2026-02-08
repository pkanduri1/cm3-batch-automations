"""FastAPI main application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.routers import mappings, files, system

# Create FastAPI application
app = FastAPI(
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
