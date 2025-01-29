"""Application configuration."""
import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Environment settings
    debug: bool = True  # Set to False in production
    
    # Base directory for all data
    data_dir: Path = Path("data")
    
    # Scripts directory
    scripts_dir: Path = data_dir / "scripts"
    
    # Logs directory
    logs_dir: Path = data_dir / "logs"
    
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
    
    # Script execution settings
    max_execution_time: int = 300  # 5 minutes in seconds
    
    class Config:
        """Pydantic config."""
        env_prefix = "PYTASK_"


# Create settings instance
settings = Settings()

# Ensure required directories exist
settings.data_dir.mkdir(exist_ok=True)
settings.scripts_dir.mkdir(exist_ok=True)
settings.logs_dir.mkdir(exist_ok=True)

# Create parent directory for database if needed
Path(settings.database_url.split("///")[1]).parent.mkdir(exist_ok=True) 