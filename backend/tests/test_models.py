"""Tests for database models."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Script, Tag, Dependency, Execution, ExecutionStatus

@pytest.mark.asyncio
async def test_script_creation(session: AsyncSession):
    """Test creating a script with tags and dependencies."""
    script = Script(
        name="test_script",
        description="Test script",
        content="print('hello')",
        is_active=True
    )
    session.add(script)
    
    # Add tags
    tag = Tag(name="test")
    script.tags.append(tag)
    
    # Add dependency
    dep = Dependency(
        script=script,
        package_name="requests",
        version_spec=">=2.25.1"
    )
    session.add(dep)
    
    await session.commit()
    
    # Verify script was created
    result = await session.execute(
        select(Script).where(Script.name == "test_script")
    )
    saved_script = result.scalar_one()
    assert saved_script.name == "test_script"
    assert saved_script.description == "Test script"
    assert len(saved_script.tags) == 1
    assert saved_script.tags[0].name == "test"
    assert len(saved_script.dependencies) == 1
    assert saved_script.dependencies[0].package_name == "requests"

@pytest.mark.asyncio
async def test_script_execution(session: AsyncSession):
    """Test script execution records."""
    script = Script(
        name="test_script",
        description="Test script",
        content="print('hello')",
        is_active=True
    )
    session.add(script)
    
    # Create execution record
    execution = Execution(
        script=script,
        status=ExecutionStatus.RUNNING
    )
    session.add(execution)
    await session.commit()
    
    # Verify execution was created
    result = await session.execute(
        select(Execution).where(Execution.script_id == script.id)
    )
    saved_execution = result.scalar_one()
    assert saved_execution.status == ExecutionStatus.RUNNING
    assert saved_execution.script_id == script.id 