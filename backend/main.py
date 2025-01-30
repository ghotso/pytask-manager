"""Main application module."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .api import routes
from .config import settings
from .database import create_tables, get_session_context
from .logging_config import configure_logging
from .scheduler import scheduler_service

# Configure logging
settings.configure_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    logger.info("Starting up...")
    
    try:
        # Create database tables
        await create_tables()
        logger.info("Database tables created")
        
        # Only start scheduler in the main process, not in reloader processes
        if not os.environ.get("PYTASK_RELOADER_PROCESS"):
            logger.info("Starting scheduler service")
            await scheduler_service.start()
        
        yield
        
        # Only stop scheduler in the main process
        if not os.environ.get("PYTASK_RELOADER_PROCESS"):
            logger.info("Shutting down scheduler service")
            if scheduler_service.scheduler.running:
                await scheduler_service.shutdown()
    except Exception as e:
        logger.error(f"Error during application lifecycle: {str(e)}", exc_info=True)
        raise

# Create FastAPI app
app = FastAPI(
    title="PyTask Manager",
    description="A modern web application for managing, scheduling, and executing Python scripts",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes first
app.include_router(routes.router, prefix="/api")

# Mount static files for frontend
static_dir = Path("static")

# Serve frontend static files
@app.get("/{full_path:path}")
async def serve_frontend(request: Request, full_path: str):
    """Serve frontend files and handle client-side routing."""
    # If path starts with /api, let it be handled by API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
        
    # Check if the path points to a static file
    static_file = static_dir / full_path
    if static_file.is_file():
        return FileResponse(static_file)
        
    # For all other paths, serve the index.html for client-side routing
    return FileResponse(static_dir / "index.html")

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info("Starting PyTask Manager")
    try:
        await create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables: %s", str(e))
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down PyTask Manager") 