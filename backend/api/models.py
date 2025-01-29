from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DependencyBase(BaseModel):
    """Base model for dependencies."""
    package_name: str = Field(..., description="Name of the pip package")
    version_spec: str = Field('*', description="Version specification (e.g., '>=1.0.0', '*' for latest)")


class DependencyCreate(DependencyBase):
    """Model for creating dependencies."""
    pass


class DependencyRead(DependencyBase):
    """Model for reading dependencies."""
    id: int
    script_id: int
    installed_version: Optional[str] = None
    
    class Config:
        from_attributes = True


class TagBase(BaseModel):
    """Base model for tags."""
    name: str = Field(..., description="Tag name")


class TagCreate(TagBase):
    """Model for creating tags."""
    pass


class TagRead(TagBase):
    """Model for reading tags."""
    id: int
    
    class Config:
        from_attributes = True


class ScheduleBase(BaseModel):
    """Base model for schedules."""
    cron_expression: str = Field(..., description="Cron expression for schedule")
    description: Optional[str] = Field(None, description="Schedule description")


class ScheduleCreate(ScheduleBase):
    """Model for creating schedules."""
    pass


class ScheduleUpdate(BaseModel):
    """Model for updating schedules."""
    cron_expression: Optional[str] = None
    description: Optional[str] = None


class ScheduleRead(ScheduleBase):
    """Model for reading schedules."""
    id: int
    script_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ScriptBase(BaseModel):
    """Base model for scripts."""
    name: str = Field(..., description="Script name")
    description: Optional[str] = Field(None, description="Script description")
    content: str = Field(..., description="Python script content")
    is_active: bool = Field(False, description="Whether the script is active")


class ScriptCreate(ScriptBase):
    """Model for creating scripts."""
    tags: List[str] = Field(default_factory=list, description="List of tag names")
    dependencies: List[DependencyCreate] = Field(
        default_factory=list,
        description="List of dependencies",
    )
    schedules: List[ScheduleCreate] = Field(
        default_factory=list,
        description="List of schedules",
    )


class ScriptUpdate(BaseModel):
    """Model for updating scripts."""
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None
    dependencies: Optional[List[DependencyCreate]] = None
    schedules: Optional[List[ScheduleCreate]] = None


class ScriptRead(ScriptBase):
    """Model for reading scripts."""
    id: int
    created_at: datetime
    updated_at: datetime
    tags: List[TagRead]
    dependencies: List[DependencyRead]
    schedules: List[ScheduleRead]
    
    class Config:
        from_attributes = True


class ExecutionRead(BaseModel):
    """Model for reading executions."""
    id: int
    script_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    log_output: Optional[str] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class ExecutionResponse(BaseModel):
    """Response model for script execution."""
    execution_id: int
    status: str

    class Config:
        from_attributes = True 