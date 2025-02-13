"""Database configuration and utilities."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                  create_async_engine)
from sqlalchemy import event, text

from .config import settings
from .models import Base, Script, Tag, Execution, Schedule, Dependency  # Import all models

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
)

# Enable SQLite foreign key constraints
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def create_tables() -> None:
    """Create all tables in the database."""
    # Ensure database file exists with proper permissions
    db_file = settings.data_dir / "data.db"
    if not db_file.exists():
        db_file.touch()
        os.chmod(db_file, 0o666)  # rw-rw-rw- permissions
        logger.info(f"Created database file at {db_file} with permissions 666")
    
    try:
        async with engine.begin() as conn:
            # Enable foreign key constraints
            await conn.execute(text("PRAGMA foreign_keys=ON"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    async with async_session_factory() as session:
        try:
            # Enable foreign key constraints for this session
            await session.execute(text("PRAGMA foreign_keys=ON"))
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session as a context manager."""
    async with async_session_factory() as session:
        try:
            # Enable foreign key constraints for this session
            await session.execute(text("PRAGMA foreign_keys=ON"))
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close() 