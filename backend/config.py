"""Application configuration."""
import os
import logging
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Environment settings
    debug: bool = True  # Set to False in production
    
    # Base directory for all data
    data_dir: Path = Path("/app/data")
    
    # Scripts directory
    scripts_dir: Path = Path("/app/scripts")
    
    # Logs directory (independent of data_dir)
    logs_dir: Path = Path("/app/logs")
    
    # Database settings
    database_url: str = "sqlite+aiosqlite:///data/data.db"
    
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
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o777)  # Full permissions for mounted volumes

# Create database file with proper permissions if it doesn't exist
db_path = Path(settings.database_url.split("///")[1])
db_path.parent.mkdir(parents=True, exist_ok=True)
if not db_path.exists():
    db_path.touch()
    os.chmod(db_path, 0o666)  # rw-rw-rw- permissions for database file 