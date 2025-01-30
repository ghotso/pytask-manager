"""Application configuration."""
import os
import logging
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings."""
    
    # Environment settings
    debug: bool = True  # Set to False in production
    
    # Base directory for all data
    data_dir: Path = get_project_root() / "data"
    
    # Scripts directory
    scripts_dir: Path = get_project_root() / "scripts"
    
    # Logs directory (independent of data_dir)
    logs_dir: Path = get_project_root() / "logs"
    
    # Database settings
    database_url: str = "sqlite+aiosqlite:///data/data.db"  # Relative path for development
    
    # CORS settings
    cors_origins: list[str] = [
        "http://localhost:5173",  # Vite development server
        "http://localhost:8000",  # Production/development server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[Path] = logs_dir / "app.log"
    error_log_file: Optional[Path] = logs_dir / "error.log"
    
    # Script execution settings
    max_execution_time: int = 300  # 5 minutes in seconds
    
    def configure_logging(self) -> None:
        """Configure logging for the application."""
        handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(self.log_format))
        handlers.append(console_handler)
        
        # File handlers
        if self.log_file:
            os.makedirs(str(self.logs_dir), exist_ok=True)
            file_handler = logging.FileHandler(str(self.log_file))
            file_handler.setFormatter(logging.Formatter(self.log_format))
            handlers.append(file_handler)
            
        if self.error_log_file:
            error_handler = logging.FileHandler(str(self.error_log_file))
            error_handler.setFormatter(logging.Formatter(self.log_format))
            error_handler.setLevel(logging.ERROR)
            handlers.append(error_handler)
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            handlers=handlers,
            force=True
        )
        
        # Set SQLAlchemy logging to WARNING unless in debug mode
        if not self.debug:
            logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    class Config:
        """Pydantic config."""
        env_prefix = "PYTASK_"


# Create settings instance
settings = Settings()

# Ensure required directories exist with proper permissions
for directory in [settings.data_dir, settings.scripts_dir, settings.logs_dir]:
    os.makedirs(str(directory), exist_ok=True)

# Get database path from URL
db_path = Path(settings.database_url.split("sqlite+aiosqlite:///")[1])
if db_path.is_absolute():
    db_file = db_path
else:
    db_file = settings.data_dir / db_path

# Create database directory if it doesn't exist
os.makedirs(str(db_file.parent), exist_ok=True)

# Create database file with proper permissions if it doesn't exist
if not db_file.exists():
    db_file.touch()
    os.chmod(str(db_file), 0o666)  # rw-rw-rw- permissions for database file
    logging.info(f"Created database file at {db_file} with permissions 666") 