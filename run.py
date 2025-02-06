"""Development server runner."""
import asyncio
import logging
import os
import sys
from pathlib import Path

from alembic.config import Config
from alembic import command

async def run_migrations():
    """Run database migrations and setup."""
    # Get the directory containing this script
    root_dir = Path(__file__).parent.absolute()
    
    # Add the root directory to Python path
    sys.path.insert(0, str(root_dir))
    
    from backend.config import settings
    from backend.database import create_tables
    
    # Configure logging
    settings.configure_logging()
    logger = logging.getLogger(__name__)
    
    # Run database migrations
    try:
        # Ensure the data directory exists
        Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
        
        # Create alembic.ini configuration
        alembic_cfg = Config()
        alembic_cfg.set_main_option('script_location', str(root_dir / 'migrations'))
        alembic_cfg.set_main_option('sqlalchemy.url', 
                                   settings.database_url.replace('sqlite+aiosqlite:', 'sqlite:'))
        
        # Run migrations
        command.upgrade(alembic_cfg, 'head')
        logger.info("Database migrations completed successfully")
        
        # Create tables
        await create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error during setup: {e}")
        raise

if __name__ == "__main__":
    # Run migrations first
    asyncio.run(run_migrations())
    
    import uvicorn
    
    # Set environment variable for reloader process detection
    # The WatchFiles reloader sets this environment variable
    if os.environ.get("WATCHFILES_FORCE_POLLING") or os.environ.get("WATCHFILES_FORCE_NOTIFY"):
        os.environ["PYTASK_RELOADER_PROCESS"] = "1"
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",  # Listen on all interfaces
        port=8000,
        reload="--reload" in sys.argv,
        reload_excludes=["scripts/**/*", "scripts/*", "data/*"],
    ) 