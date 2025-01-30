from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy import (Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey,
                       Integer, String, Table)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return current UTC datetime with timezone information."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# Association table for script tags
script_tags = Table(
    "script_tags",
    Base.metadata,
    Column("script_id", Integer, ForeignKey("scripts.id")),
    Column("tag_id", Integer, ForeignKey("tags.id")),
)


class ExecutionStatus(str, Enum):
    """Script execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"


class Script(Base):
    """Model for Python scripts."""
    
    __tablename__ = "scripts"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    content: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    tags: Mapped[List["Tag"]] = relationship(
        secondary=script_tags, back_populates="scripts"
    )
    executions: Mapped[List["Execution"]] = relationship(back_populates="script")
    schedules: Mapped[List["Schedule"]] = relationship(back_populates="script")
    dependencies: Mapped[List["Dependency"]] = relationship(back_populates="script")


class Tag(Base):
    """Model for script tags."""
    
    __tablename__ = "tags"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    
    # Relationships
    scripts: Mapped[List[Script]] = relationship(
        secondary=script_tags, back_populates="tags"
    )


class Execution(Base):
    """Model for script executions."""
    
    __tablename__ = "executions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id"))
    schedule_id: Mapped[Optional[int]] = mapped_column(ForeignKey("schedules.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING
    )
    log_output: Mapped[Optional[str]] = mapped_column(String)
    error_message: Mapped[Optional[str]] = mapped_column(String)
    
    # Relationships
    script: Mapped[Script] = relationship(back_populates="executions")
    schedule: Mapped[Optional["Schedule"]] = relationship()


class Schedule(Base):
    """Model for script schedules."""
    
    __tablename__ = "schedules"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id"))
    cron_expression: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    # Relationships
    script: Mapped[Script] = relationship(back_populates="schedules")


class Dependency(Base):
    """Model for script dependencies."""
    
    __tablename__ = "dependencies"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id"))
    package_name: Mapped[str] = mapped_column(String(255))
    version_spec: Mapped[str] = mapped_column(String(100))
    installed_version: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Relationships
    script: Mapped[Script] = relationship(back_populates="dependencies") 