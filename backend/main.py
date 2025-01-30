"""Main application module."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
if static_dir.exists():
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Serve frontend static files in production
if not settings.debug:
    static_dir = Path(__file__).parent.parent / "frontend" / "dist"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

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