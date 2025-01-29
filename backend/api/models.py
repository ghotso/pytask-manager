"""Pydantic models for API request/response validation."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TagBase(BaseModel):
    """Base model for tag data."""
    name: str = Field(..., description="Name of the tag")


class TagCreate(TagBase):
    """Model for creating a new tag."""
    pass


class TagRead(TagBase):
    """Model for reading a tag."""
    id: int = Field(..., description="Unique identifier for the tag")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class DependencyBase(BaseModel):
    """Base model for dependency data."""
    package_name: str = Field(..., description="Name of the Python package")
    version_spec: str = Field(default="", description="Version specification (e.g., '>=1.0.0')")


class DependencyCreate(DependencyBase):
    """Model for creating a new dependency."""
    pass


class DependencyRead(DependencyBase):
    """Model for reading a dependency."""
    id: int = Field(..., description="Unique identifier for the dependency")
    installed_version: Optional[str] = Field(None, description="Currently installed version")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class ScheduleBase(BaseModel):
    """Base model for schedule data."""
    cron_expression: str = Field(..., description="Cron expression for scheduling")
    description: str = Field(default="", description="Description of the schedule")


class ScheduleCreate(ScheduleBase):
    """Model for creating a new schedule."""
    pass


class ScheduleUpdate(BaseModel):
    """Model for updating a schedule."""
    cron_expression: Optional[str] = Field(None, description="Cron expression for scheduling")
    description: Optional[str] = Field(None, description="Description of the schedule")


class ScheduleRead(ScheduleBase):
    """Model for reading a schedule."""
    id: int = Field(..., description="Unique identifier for the schedule")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class ScriptBase(BaseModel):
    """Base model for script data."""
    name: str = Field(..., description="Name of the script")
    description: str = Field(default="", description="Description of the script")
    content: str = Field(..., description="Python code content")
    is_active: bool = Field(default=True, description="Whether the script is active")


class ScriptCreate(ScriptBase):
    """Model for creating a new script."""
    tags: List[str] = Field(default_factory=list, description="List of tag names")
    dependencies: List[DependencyCreate] = Field(default_factory=list, description="List of dependencies")
    schedules: List[ScheduleCreate] = Field(default_factory=list, description="List of schedules")


class ScriptUpdate(BaseModel):
    """Model for updating a script."""
    name: Optional[str] = Field(None, description="Name of the script")
    description: Optional[str] = Field(None, description="Description of the script")
    content: Optional[str] = Field(None, description="Python code content")
    is_active: Optional[bool] = Field(None, description="Whether the script is active")
    tags: Optional[List[str]] = Field(None, description="List of tag names")
    dependencies: Optional[List[DependencyCreate]] = Field(None, description="List of dependencies")
    schedules: Optional[List[ScheduleCreate]] = Field(None, description="List of schedules")


class ScriptRead(ScriptBase):
    """Model for reading a script."""
    id: int = Field(..., description="Unique identifier for the script")
    tags: List[TagRead] = Field(default_factory=list, description="List of tags")
    dependencies: List[DependencyRead] = Field(default_factory=list, description="List of dependencies")
    schedules: List[ScheduleRead] = Field(default_factory=list, description="List of schedules")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class ExecutionRead(BaseModel):
    """Model for reading an execution."""
    id: int = Field(..., description="Unique identifier for the execution")
    script_id: int = Field(..., description="ID of the script that was executed")
    status: str = Field(..., description="Status of the execution")
    started_at: datetime = Field(..., description="When the execution started")
    completed_at: Optional[datetime] = Field(None, description="When the execution completed")
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    log_output: Optional[str] = Field(None, description="Output logs from the execution")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class ExecutionResponse(BaseModel):
    """Response model for script execution."""
    execution_id: int = Field(..., description="ID of the created execution")
    status: str = Field(..., description="Initial status of the execution") 