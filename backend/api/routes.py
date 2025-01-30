"""API routes for the application."""
import logging
from typing import List, Optional, cast
from datetime import datetime
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, WebSocket, BackgroundTasks
from starlette.websockets import WebSocketDisconnect
from pydantic import ValidationError, BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_session, get_session_context
from ..models import Dependency, Execution, ExecutionStatus, Schedule, Script, Tag
from ..scheduler import scheduler_service
from ..script_manager import ScriptManager
from .models import (DependencyCreate, DependencyRead, ExecutionRead, ExecutionResponse,
                    ScheduleCreate, ScheduleRead, ScheduleUpdate, ScriptCreate,
                    ScriptRead, ScriptUpdate, TagCreate, TagRead)
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


class DependencyUninstall(BaseModel):
    package_name: str


@router.get("/scripts", response_model=List[ScriptRead])
async def list_scripts(
    session: AsyncSession = Depends(get_session),
    tag: Optional[str] = None,
) -> List[Script]:
    """List all scripts, optionally filtered by tag."""
    query = (
        select(Script)
        .options(selectinload(Script.tags))
        .options(selectinload(Script.dependencies))
        .options(selectinload(Script.schedules))
    )
    if tag:
        query = query.join(Script.tags).where(Tag.name == tag)
    result = await session.execute(query)
    return cast(List[Script], result.scalars().all())


@router.post("/scripts", response_model=ScriptRead)
async def create_script(
    script_data: ScriptCreate,
    session: AsyncSession = Depends(get_session),
) -> Script:
    """Create a new script with all its relationships in a single transaction."""
    try:
        logger.info("Received create script request")
        logger.info(f"Script data: {script_data.model_dump_json(indent=2)}")
        
        # Check if script with same name exists
        existing_script = await session.execute(
            select(Script).where(Script.name == script_data.name)
        )
        if existing_script.scalar_one_or_none():
            msg = f"A script with the name '{script_data.name}' already exists"
            logger.error(msg)
            raise HTTPException(status_code=400, detail=msg)

        # Create script instance
        script = Script(
            name=script_data.name,
            description=script_data.description,
            content=script_data.content,
            is_active=script_data.is_active,
            tags=[],  # Initialize empty list
            dependencies=[],  # Initialize empty list
            schedules=[],  # Initialize empty list
        )
        session.add(script)
        await session.flush()  # Flush to get the script ID

        # Create script directory structure
        script_dir = Path(settings.scripts_dir) / str(script.id)
        script_dir.mkdir(parents=True, exist_ok=True)
        script_path = script_dir / "script.py"
        script_path.write_text(script.content)
        logger.info(f"Created script directory at {script_dir}")
        
        # Get or create tags in a single query
        if script_data.tags:
            logger.info(f"Processing tags: {script_data.tags}")
            # First, get all existing tags
            existing_tags = await session.execute(
                select(Tag).where(Tag.name.in_(script_data.tags))
            )
            existing_tags_dict = {tag.name: tag for tag in existing_tags.scalars().all()}
            
            # Create any missing tags
            new_tags = []
            for tag_name in script_data.tags:
                if tag_name not in existing_tags_dict:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                    new_tags.append(tag)
            
            if new_tags:
                await session.flush()  # Flush to get IDs for new tags
            
            # Now add all tags to the script
            for tag_name in script_data.tags:
                if tag_name in existing_tags_dict:
                    script.tags.append(existing_tags_dict[tag_name])
                else:
                    script.tags.append(next(tag for tag in new_tags if tag.name == tag_name))
        
        # Add all dependencies at once
        if script_data.dependencies:
            logger.info(f"Processing dependencies: {script_data.dependencies}")
            for dep_data in script_data.dependencies:
                dependency = Dependency(
                    script=script,
                    package_name=dep_data.package_name,
                    version_spec=dep_data.version_spec,
                )
                session.add(dependency)
                script.dependencies.append(dependency)
        
        # Add all schedules at once
        if script_data.schedules:
            logger.info(f"Processing schedules: {script_data.schedules}")
            for schedule_data in script_data.schedules:
                schedule = Schedule(
                    script=script,
                    cron_expression=schedule_data.cron_expression,
                    description=schedule_data.description,
                )
                session.add(schedule)
                script.schedules.append(schedule)
        
        # Commit everything in a single transaction
        await session.commit()
        logger.info("Successfully committed all changes")
        
        # Refresh to get all relationships
        await session.refresh(script, ['tags', 'dependencies', 'schedules'])
        return script
        
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating script: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/scripts/{script_id}", response_model=ScriptRead)
async def get_script(
    script_id: int,
    session: AsyncSession = Depends(get_session),
) -> Script:
    """Get a script by ID."""
    return await _get_script(session, script_id)


@router.put("/scripts/{script_id}", response_model=ScriptRead)
async def update_script(
    script_id: int,
    script_data: ScriptUpdate,
    session: AsyncSession = Depends(get_session),
) -> Script:
    """Update a script."""
    try:
        script = await _get_script(session, script_id)
        
        # Update basic fields
        if script_data.name is not None:
            script.name = script_data.name
        if script_data.description is not None:
            script.description = script_data.description
        if script_data.content is not None:
            script.content = script_data.content
        if script_data.is_active is not None:
            script.is_active = script_data.is_active
            # Update scheduler jobs when activation status changes
            for schedule in script.schedules:
                await session.refresh(schedule, ['script'])  # Ensure script relationship is loaded
                if script.is_active:
                    await scheduler_service.add_job(schedule)
                else:
                    await scheduler_service.remove_job(schedule)
        
        # Update tags
        if script_data.tags is not None:
            # First, get all existing tags
            existing_tags = await session.execute(
                select(Tag).where(Tag.name.in_(script_data.tags))
            )
            existing_tags_dict = {tag.name: tag for tag in existing_tags.scalars().all()}
            
            # Create any missing tags
            new_tags = []
            for tag_name in script_data.tags:
                if tag_name not in existing_tags_dict:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                    new_tags.append(tag)
            
            if new_tags:
                await session.flush()
            
            # Clear and update tags
            script.tags.clear()
            for tag_name in script_data.tags:
                if tag_name in existing_tags_dict:
                    script.tags.append(existing_tags_dict[tag_name])
                else:
                    script.tags.append(next(tag for tag in new_tags if tag.name == tag_name))
        
        # Update dependencies
        if script_data.dependencies is not None:
            # Create new dependencies first
            new_dependencies = []
            for dep_data in script_data.dependencies:
                dependency = Dependency(
                    script_id=script.id,  # Set script_id explicitly
                    package_name=dep_data.package_name,
                    version_spec=dep_data.version_spec,
                )
                new_dependencies.append(dependency)
            
            # Remove old dependencies
            await session.execute(
                select(Dependency).where(Dependency.script_id == script.id)
            )
            for dep in script.dependencies:
                await session.delete(dep)
            
            # Add new dependencies
            script.dependencies = new_dependencies
            for dep in new_dependencies:
                session.add(dep)
        
        # Update schedules
        if script_data.schedules is not None:
            # Remove old schedules from scheduler
            for schedule in script.schedules:
                await scheduler_service.remove_job(schedule)
                await session.delete(schedule)
            
            # Create and add new schedules
            new_schedules = []
            for schedule_data in script_data.schedules:
                schedule = Schedule(
                    script_id=script.id,  # Set script_id explicitly
                    cron_expression=schedule_data.cron_expression,
                    description=schedule_data.description,
                )
                new_schedules.append(schedule)
                session.add(schedule)
                
                # Add to scheduler if script is active
                if script.is_active:
                    await scheduler_service.add_job(schedule)
            
            script.schedules = new_schedules
        
        await session.commit()
        await session.refresh(script, ['tags', 'dependencies', 'schedules'])
        return script
        
    except Exception as e:
        logger.error(f"Error updating script: {str(e)}", exc_info=True)
        await session.rollback()  # Rollback on error
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/scripts/{script_id}")
async def delete_script(
    script_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a script."""
    script = await _get_script(session, script_id)
    
    # Delete script and clean up its environment
    manager = ScriptManager(script_id, base_dir=str(settings.scripts_dir))
    manager.cleanup()
    await session.delete(script)
    await session.commit()


@router.post("/scripts/{script_id}/schedules", response_model=ScheduleRead)
async def create_schedule(
    script_id: int,
    schedule_data: ScheduleCreate,
    session: AsyncSession = Depends(get_session),
) -> Schedule:
    """Create a new schedule for a script."""
    script = await _get_script(session, script_id)
    
    schedule = Schedule(
        script=script,
        cron_expression=schedule_data.cron_expression,
        description=schedule_data.description,
    )
    session.add(schedule)
    await session.commit()
    
    # Refresh with script relationship to ensure it's loaded
    await session.refresh(schedule, ['script'])
    
    # Add job to scheduler if script is active
    if schedule.script and schedule.script.is_active:
        logger.info(f"Adding schedule {schedule.id} to scheduler with cron: {schedule.cron_expression}")
        await scheduler_service.add_job(schedule)
    else:
        logger.info(f"Not adding schedule {schedule.id} to scheduler because script is not active")
    
    return schedule


@router.put("/scripts/{script_id}/schedules/{schedule_id}", response_model=ScheduleRead)
async def update_schedule(
    script_id: int,
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    session: AsyncSession = Depends(get_session),
) -> Schedule:
    """Update a schedule."""
    schedule = await _get_schedule(session, script_id, schedule_id)
    
    if schedule_data.cron_expression is not None:
        schedule.cron_expression = schedule_data.cron_expression
    if schedule_data.description is not None:
        schedule.description = schedule_data.description
    
    await session.commit()
    await session.refresh(schedule)
    
    # Update scheduler if script is active
    if schedule.script.is_active:
        await scheduler_service.add_job(schedule)
    
    return schedule


@router.delete("/scripts/{script_id}/schedules/{schedule_id}")
async def delete_schedule(
    script_id: int,
    schedule_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a schedule."""
    schedule = await _get_schedule(session, script_id, schedule_id)
    
    # Remove from scheduler
    await scheduler_service.remove_job(schedule)
    
    # Delete from database
    await session.delete(schedule)
    await session.commit()


@router.get("/scripts/{script_id}/executions", response_model=List[ExecutionRead])
async def list_executions(
    script_id: int,
    session: AsyncSession = Depends(get_session),
    limit: int = 100,
    offset: int = 0,
) -> List[Execution]:
    """List executions for a script."""
    result = await session.execute(
        select(Execution)
        .where(Execution.script_id == script_id)
        .order_by(Execution.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return cast(List[Execution], result.scalars().all())


@router.post("/scripts/{script_id}/check-dependencies")
async def check_dependencies(
    script_id: int,
    session: AsyncSession = Depends(get_session),
) -> List[str]:
    """Check for outdated dependencies in a script."""
    script = await _get_script(session, script_id)
    manager = ScriptManager(script_id, base_dir=str(settings.scripts_dir))
    return await manager.check_dependencies()


@router.post("/scripts/{script_id}/update-dependencies")
async def update_dependencies(
    script_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Update all dependencies to their latest versions."""
    script = await _get_script(session, script_id)
    
    # Update dependencies to latest versions
    for dep in script.dependencies:
        if not dep.version_spec or dep.version_spec == "":
            dep.version_spec = ""  # This will make pip install the latest version
    
    await session.commit()
    
    # Schedule dependency update in background
    background_tasks.add_task(
        _update_script_environment,
        script_id,
        script.content,
        script.dependencies
    )
    
    return {"message": "Dependency update started"}


@router.post("/scripts/{script_id}/execute", response_model=ExecutionResponse)
async def execute_script(
    script_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> ExecutionResponse:
    """Execute a script and return its execution ID."""
    # Get script
    script = await _get_script(session, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # Create execution record
    execution: Execution = Execution(
        script_id=script_id,
        status=ExecutionStatus.PENDING,
        started_at=datetime.utcnow(),
    )
    session.add(execution)
    await session.commit()
    await session.refresh(execution)

    # Initialize script manager
    script_manager = ScriptManager(script_id, base_dir=str(settings.scripts_dir))
    
    try:
        # Set up environment first
        await script_manager.setup_environment(
            script_content=script.content,
            dependencies=script.dependencies
        )
        
        # Schedule execution
        background_tasks.add_task(
            _execute_script,
            script_manager=script_manager,
            execution_id=execution.id,
            session=session,
        )
        
        return ExecutionResponse(
            execution_id=execution.id,
            status=ExecutionStatus.PENDING
        )
        
    except Exception as e:
        # Update execution record with error
        execution.status = ExecutionStatus.FAILURE
        execution.completed_at = datetime.utcnow()
        execution.error_message = f"Failed to set up script environment: {str(e)}"
        await session.commit()
        
        # Clean up failed environment
        script_manager.cleanup()
        
        # Re-raise as HTTP exception
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set up script environment: {str(e)}"
        )


@router.get("/scripts/{script_id}/executions/{execution_id}/logs")
async def get_execution_logs(
    script_id: int,
    execution_id: int,
    session: AsyncSession = Depends(get_session),
) -> str:
    """Get logs for a specific execution."""
    try:
        logger.info(f"Fetching logs for execution {execution_id} of script {script_id}")
        
        # Get execution with explicit log_output loading
        result = await session.execute(
            select(Execution)
            .where(
                Execution.script_id == script_id,
                Execution.id == execution_id
            )
        )
        execution = result.scalar_one_or_none()
        
        if not execution:
            logger.warning(f"Execution {execution_id} not found")
            raise HTTPException(status_code=404, detail="Execution not found")
            
        logger.info(f"Found execution {execution_id} with status {execution.status}")
        logger.debug(f"Log output type: {type(execution.log_output)}")
        logger.debug(f"Raw log output: {repr(execution.log_output)}")
        
        if execution.log_output is None:
            logger.warning(f"No logs found for execution {execution_id}")
            return ""
            
        # Ensure we return a string
        log_output = str(execution.log_output)
        logger.info(f"Returning log output (length: {len(log_output)})")
        logger.debug(f"Log content:\n{log_output}")
        return log_output
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching logs for execution {execution_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch execution logs: {str(e)}"
        )


@router.websocket("/scripts/{script_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    script_id: int,
    session: AsyncSession = Depends(get_session),
):
    """WebSocket endpoint for real-time script execution."""
    logger.debug("WebSocket connection initiated")
    await websocket.accept()
    logger.debug("WebSocket connection accepted")
    execution: Optional[Execution] = None
    output_buffer = []
    
    try:
        script = await _get_script(session, script_id)
        logger.debug(f"Retrieved script {script_id}")
        
        # Create execution record
        execution = Execution(
            script=script,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        session.add(execution)
        await session.commit()
        await session.refresh(execution)
        logger.debug(f"Created execution record {execution.id}")
        
        try:
            # Set up environment
            manager = ScriptManager(script_id, base_dir=str(settings.scripts_dir))
            await manager.setup_environment(script.content, script.dependencies)
            logger.debug("Environment setup complete")
            
            # Execute and stream output
            try:
                async for output in manager.execute(execution.id):
                    logger.debug(f"Received output: {output!r}")
                    output_buffer.append(output)
                    try:
                        await websocket.send_text(output)
                        logger.debug("Sent output to WebSocket")
                    except (WebSocketDisconnect, RuntimeError) as e:
                        logger.warning(f"WebSocket disconnected during execution: {e}")
                        break
                
                # Only mark as success if we got here without exceptions
                if execution is not None:
                    execution.status = ExecutionStatus.SUCCESS
                    execution.log_output = "".join(output_buffer)
                    logger.debug(f"Execution successful. Full log output:\n{execution.log_output}")
                    await session.commit()
                
            except Exception as e:
                logger.exception("Script execution failed")
                if execution is not None:
                    execution.status = ExecutionStatus.FAILURE
                    execution.error_message = str(e)
                    execution.log_output = "".join(output_buffer)
                    logger.debug(f"Execution failed. Error log output:\n{execution.log_output}")
                    await session.commit()
                try:
                    await websocket.send_text(f"Error: {str(e)}")
                except (WebSocketDisconnect, RuntimeError):
                    pass
                
        except Exception as e:
            logger.exception("Failed to set up script environment")
            if execution is not None:
                execution.status = ExecutionStatus.FAILURE
                execution.error_message = f"Setup failed: {str(e)}"
                execution.log_output = "".join(output_buffer)
                await session.commit()
            try:
                await websocket.send_text(f"Error: Setup failed: {str(e)}")
            except (WebSocketDisconnect, RuntimeError):
                pass
            
    except Exception as e:
        logger.exception("WebSocket endpoint error")
        if execution is not None:
            execution.status = ExecutionStatus.FAILURE
            execution.error_message = str(e)
            execution.log_output = "".join(output_buffer)
            await session.commit()
    finally:
        # Always update completion time and ensure status is set
        if execution:
            execution.completed_at = datetime.utcnow()
            if execution.status == ExecutionStatus.RUNNING:
                execution.status = ExecutionStatus.FAILURE
                execution.error_message = "Execution interrupted"
            execution.log_output = "".join(output_buffer)
            try:
                await session.commit()
                logger.debug(f"Final execution status: {execution.status}")
                logger.debug(f"Final log output:\n{execution.log_output}")
            except Exception as e:
                logger.exception("Failed to save execution status")
        
        try:
            await websocket.close()
            logger.debug("WebSocket connection closed")
        except (WebSocketDisconnect, RuntimeError):
            pass


@router.post("/scripts/{script_id}/install-dependencies")
async def install_dependencies(
    script_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Install dependencies for a script."""
    try:
        logger.info(f"Installing dependencies for script {script_id}")
        script = await _get_script(session, script_id)
        
        # Create script manager and set up environment
        manager = ScriptManager(script_id, base_dir=str(settings.scripts_dir))
        await manager.setup_environment(script.content, script.dependencies)
        
        # Get installed versions
        installed_versions = await manager.get_installed_versions()
        logger.debug(f"Got installed versions: {installed_versions}")
        
        # Update dependencies with installed versions
        for dep in script.dependencies:
            if dep.package_name.lower() in {k.lower() for k in installed_versions.keys()}:
                # Find the actual package name with correct case
                actual_name = next(
                    k for k in installed_versions.keys() 
                    if k.lower() == dep.package_name.lower()
                )
                dep.installed_version = installed_versions[actual_name]
                logger.debug(f"Updated {dep.package_name} with version {dep.installed_version}")
        
        await session.commit()
        await session.refresh(script)
        
        return {
            "message": "Dependencies installed successfully",
            "dependencies": [
                {
                    "package_name": dep.package_name,
                    "version_spec": dep.version_spec,
                    "installed_version": dep.installed_version
                }
                for dep in script.dependencies
            ]
        }
        
    except Exception as e:
        logger.exception(f"Error installing dependencies for script {script_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to install dependencies: {str(e)}"
        )


@router.post("/scripts/{script_id}/dependencies/uninstall")
async def uninstall_dependency(
    script_id: int,
    data: DependencyUninstall,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Uninstall a dependency from a script's virtual environment and update requirements.txt."""
    script = await _get_script(session, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    script_manager = ScriptManager(script_id, base_dir=str(settings.scripts_dir))
    
    try:
        # Find the dependency to delete
        dependency = next(
            (dep for dep in script.dependencies if dep.package_name == data.package_name),
            None
        )
        
        if dependency:
            # Delete the dependency from the database first
            await session.delete(dependency)
            await session.commit()
            
            try:
                # Try to uninstall from venv if it exists
                await script_manager.uninstall_dependency(data.package_name)
            except Exception as e:
                logger.warning(f"Failed to uninstall {data.package_name} from venv: {e}")
                # Continue since we still want to update requirements.txt
            
            # Update requirements.txt if it exists
            requirements_path = script_manager.get_requirements_path()
            if os.path.exists(requirements_path):
                with open(requirements_path, 'r') as f:
                    requirements = f.readlines()
                
                # Filter out the uninstalled package
                updated_requirements = [
                    req for req in requirements 
                    if not req.strip().lower().startswith(data.package_name.lower())
                ]
                
                with open(requirements_path, 'w') as f:
                    f.writelines(updated_requirements)
        
        return {
            "status": "success",
            "message": f"Successfully uninstalled {data.package_name}"
        }
        
    except Exception as e:
        logger.error(f"Error uninstalling dependency: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uninstalling dependency: {str(e)}"
        )


async def _get_script(session: AsyncSession, script_id: int) -> Script:
    """Get a script by ID with all relationships loaded."""
    query = (
        select(Script)
        .options(selectinload(Script.tags))
        .options(selectinload(Script.dependencies))
        .options(selectinload(Script.schedules))
        .where(Script.id == script_id)
    )
    result = await session.execute(query)
    script = result.scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


async def _get_schedule(
    session: AsyncSession,
    script_id: int,
    schedule_id: int,
) -> Schedule:
    """Get a schedule by ID or raise 404."""
    result = await session.execute(
        select(Schedule)
        .options(selectinload(Schedule.script))
        .where(
            Schedule.script_id == script_id,
            Schedule.id == schedule_id,
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


async def _get_or_create_tag(session: AsyncSession, tag_name: str) -> Tag:
    """Get an existing tag or create a new one."""
    result = await session.execute(
        select(Tag).where(Tag.name == tag_name)
    )
    tag = result.scalar_one_or_none()
    
    if not tag:
        tag = Tag(name=tag_name)
        session.add(tag)
        await session.flush()  # Just flush instead of commit
    
    return tag


async def _update_script_environment(script_id: int, content: str, dependencies: List[Dependency]) -> None:
    """Update a script's virtual environment."""
    manager = ScriptManager(script_id, base_dir=str(settings.scripts_dir))
    await manager.setup_environment(content, dependencies)


async def _execute_script(
    script_manager: ScriptManager,
    execution_id: int,
    session: AsyncSession,
) -> None:
    """Execute script and update execution record."""
    try:
        # Get execution record
        execution = await session.get(Execution, execution_id)
        if not execution:
            logger.error(f"Execution {execution_id} not found")
            return

        # Update status to running
        execution.status = ExecutionStatus.RUNNING
        await session.commit()

        # Execute script and collect output
        output = []
        async for line in script_manager.execute(execution_id):
            output.append(line)

        # Update execution record with success
        execution.status = ExecutionStatus.SUCCESS
        execution.completed_at = datetime.utcnow()
        execution.log_output = "".join(output)
        await session.commit()

    except Exception as e:
        logger.error(f"Script execution failed: {str(e)}", exc_info=True)
        
        # Update execution record with error
        execution.status = ExecutionStatus.FAILURE
        execution.completed_at = datetime.utcnow()
        execution.error_message = str(e)
        execution.log_output = "".join(output) if output else ""
        await session.commit()

    finally:
        # Clean up environment
        script_manager.cleanup()