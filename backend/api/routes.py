"""API routes for the application."""
import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, cast

from fastapi import APIRouter, WebSocket, HTTPException, Depends, Query, BackgroundTasks
from starlette.websockets import WebSocketDisconnect
from pydantic import ValidationError, BaseModel
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..database import get_session, get_session_context
from ..models import Dependency, Execution, ExecutionStatus, Schedule, Script, Tag
from ..scheduler import scheduler_service
from ..script_manager import ScriptManager
from .models import (DependencyCreate, DependencyRead, ExecutionRead, ExecutionResponse,
                    ScheduleCreate, ScheduleRead, ScheduleUpdate, ScriptCreate,
                    ScriptRead, ScriptUpdate, TagCreate, TagRead)

logger = logging.getLogger(__name__)
router = APIRouter()

# Script manager instances
script_managers: Dict[int, ScriptManager] = {}

def get_script_manager(script_id: int) -> Optional[ScriptManager]:
    """Get or create a script manager for the given script ID."""
    return script_managers.get(script_id)

async def get_execution(execution_id: int, session: AsyncSession = Depends(get_session)) -> Optional[Execution]:
    """Get an execution by ID."""
    return await session.get(Execution, execution_id)


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
    try:
        logger.info(f"Deleting script {script_id}")
        
        # Get script with all relationships loaded
        script = await _get_script(session, script_id)
        
        # Remove any active schedules from the scheduler
        for schedule in script.schedules:
            await scheduler_service.remove_job(schedule)
        
        # Delete script and clean up its environment
        manager = ScriptManager(script_id, base_dir=str(settings.scripts_dir))
        try:
            manager.cleanup()
        except Exception as e:
            logger.warning(f"Failed to clean up script directory: {e}")
            # Continue with deletion even if cleanup fails
        
        # Delete all related records first
        # This is handled by SQLAlchemy's cascade settings, but we'll do it explicitly
        # to ensure proper order and avoid foreign key constraint issues
        await session.execute(delete(Dependency).where(Dependency.script_id == script_id))
        await session.execute(delete(Schedule).where(Schedule.script_id == script_id))
        await session.execute(delete(Execution).where(Execution.script_id == script_id))
        
        # Delete the script itself
        await session.delete(script)
        await session.commit()
        logger.info(f"Successfully deleted script {script_id}")
        
    except Exception as e:
        logger.error(f"Error deleting script: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


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

    # Check if there are any running executions for this script
    result = await session.execute(
        select(Execution)
        .where(
            Execution.script_id == script_id,
            Execution.status == ExecutionStatus.RUNNING
        )
    )
    running_execution = result.scalar_one_or_none()
    
    if running_execution:
        # Mark old execution as failed
        running_execution.status = ExecutionStatus.FAILURE
        running_execution.completed_at = datetime.now(timezone.utc)
        running_execution.error_message = "Execution interrupted by new execution request"
        await session.commit()

    # Create execution record
    execution: Execution = Execution(
        script_id=script_id,
        status=ExecutionStatus.PENDING,
        started_at=datetime.now(timezone.utc),
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
            script_id,
            execution.id,
        )
        
        return ExecutionResponse(
            execution_id=execution.id,
            status=ExecutionStatus.PENDING
        )
        
    except Exception as e:
        # Update execution record with error
        execution.status = ExecutionStatus.FAILURE
        execution.completed_at = datetime.now(timezone.utc)
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
    logger.info("WebSocket connection initiated")
    output_buffer = []
    
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        
        # Get the most recent running execution for this script
        result = await session.execute(
            select(Execution)
            .where(
                Execution.script_id == script_id,
                Execution.status.in_([ExecutionStatus.PENDING, ExecutionStatus.RUNNING])
            )
            .order_by(Execution.started_at.desc())
        )
        execution = result.scalar_one_or_none()
        
        if not execution:
            logger.warning(f"No running execution found for script {script_id}")
            await websocket.send_text("No running execution found")
            await websocket.close(code=1000, reason="No running execution found")
            return
            
        logger.info(f"Found running execution {execution.id}")
        
        # Create script manager to read output
        manager = ScriptManager(script_id, base_dir=str(settings.scripts_dir))
        last_status = execution.status
        has_sent_initial = False
        
        try:
            # Send initial connection message
            await websocket.send_text("Connected to execution stream...")
            has_sent_initial = True
            logger.info("Sent initial connection message")
            
            # Stream output from the running execution
            async for output in manager.read_output(execution.id):
                if not output:
                    continue
                
                logger.debug(f"Received output: {output!r}")
                output_buffer.append(output)
                
                # Send buffered output
                if output_buffer:
                    try:
                        for line in output_buffer:
                            await websocket.send_text(line)
                            logger.debug(f"Sent output: {line!r}")
                        output_buffer.clear()
                    except WebSocketDisconnect:
                        logger.warning("WebSocket disconnected during streaming")
                        return
                    except Exception as e:
                        logger.error(f"Error sending output: {e}")
                        return
                
                # Check if execution status has changed
                await session.refresh(execution)
                if execution.status != last_status:
                    status_message = f"STATUS: {execution.status}"
                    if execution.error_message:
                        status_message += f" - {execution.error_message}"
                    try:
                        await websocket.send_text(status_message)
                        logger.info(f"Sent status update: {status_message}")
                    except Exception as e:
                        logger.error(f"Error sending status update: {e}")
                        return
                    last_status = execution.status
                
                # If execution is complete, send final message and close
                if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
                    # Send any remaining buffered output
                    if output_buffer:
                        try:
                            for line in output_buffer:
                                await websocket.send_text(line)
                            output_buffer.clear()
                        except Exception as e:
                            logger.error(f"Error sending final buffered output: {e}")
                    
                    try:
                        await websocket.send_text("Execution finished.")
                        logger.info("Sent execution finished message")
                        return
                    except Exception as e:
                        logger.error(f"Error sending finished message: {e}")
                        return
                
                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
                
        except Exception as e:
            logger.exception("Error streaming output")
            try:
                await websocket.send_text(f"Error: {str(e)}")
            except:
                pass
            
    except Exception as e:
        logger.exception("Error in WebSocket endpoint")
        try:
            await websocket.send_text(f"Error: {str(e)}")
            await websocket.close(code=1011, reason=str(e))
        except:
            pass
    finally:
        try:
            if output_buffer:
                try:
                    for line in output_buffer:
                        await websocket.send_text(line)
                except:
                    pass
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket: {e}")


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


async def _execute_script(script_id: int, execution_id: int) -> None:
    """Execute a script and update its execution record."""
    logger.info(f"Executing script {script_id}")
    manager = None
    
    try:
        async with get_session_context() as session:
            # Get the script
            script = await session.get(Script, script_id)
            if not script:
                raise ValueError(f"Script {script_id} not found")
            
            # Get the execution
            execution = await session.get(Execution, execution_id)
            if not execution:
                raise ValueError(f"Execution {execution_id} not found")
            
            # Update execution status to RUNNING
            execution.status = ExecutionStatus.RUNNING
            await session.commit()
            
            # Create script manager
            manager = ScriptManager(script_id)
            
            # Collect output
            output_lines = []
            exit_code = 0
            try:
                async for line in manager.execute(execution_id):
                    output_lines.append(line)
                    # Check if this is an exit code line
                    if line.startswith("Error: Script exited with return code"):
                        try:
                            exit_code = int(line.split("return code")[-1].strip())
                        except (ValueError, IndexError):
                            exit_code = 1
            except Exception as e:
                logger.exception("Error during script execution")
                raise
            
            # Update execution record
            execution.completed_at = datetime.now(timezone.utc)
            execution.log_output = "".join(output_lines)
            
            if exit_code != 0:
                execution.status = ExecutionStatus.FAILURE
                execution.error_message = f"Script exited with return code {exit_code}"
            else:
                execution.status = ExecutionStatus.SUCCESS
            
            await session.commit()
            logger.info(f"Script execution completed with status: {execution.status} (exit code: {exit_code})")
            
    except Exception as e:
        logger.exception(f"Error executing script {script_id}")
        try:
            async with get_session_context() as session:
                execution = await session.get(Execution, execution_id)
                if execution:
                    execution.completed_at = datetime.now(timezone.utc)
                    execution.status = ExecutionStatus.FAILURE
                    execution.error_message = str(e)
                    await session.commit()
        except Exception as commit_error:
            logger.error(f"Error updating execution status: {commit_error}")
    
    finally:
        # Always clean up the script manager
        if manager:
            try:
                manager.cleanup()
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up script manager: {cleanup_error}")


@router.websocket("/api/executions/{execution_id}/output")
async def stream_execution_output(websocket: WebSocket, execution_id: int):
    """Stream execution output via WebSocket."""
    logger.info(f"WebSocket connection initiated for execution {execution_id}")
    await websocket.accept()
    
    try:
        async with get_session_context() as session:
            # Get execution with explicit refresh
            execution = await session.get(Execution, execution_id)
            if not execution:
                logger.error(f"Execution {execution_id} not found")
                await websocket.close(code=4004, reason="Execution not found")
                return

            # Get script manager
            script_manager = ScriptManager(execution.script_id, base_dir=str(settings.scripts_dir))
            if not script_manager:
                logger.error(f"Failed to create script manager for script {execution.script_id}")
                await websocket.close(code=4004, reason="Failed to create script manager")
                return

            logger.info(f"Starting output stream for execution {execution_id}")
            await websocket.send_text("Connected to execution stream...")

            # Keep track of last status to detect changes
            last_status = execution.status
            last_position = 0

            while True:
                try:
                    # Refresh execution status
                    await session.refresh(execution)
                    
                    # Check if status has changed
                    if execution.status != last_status:
                        status_msg = f"Status changed to: {execution.status.value}"
                        logger.info(status_msg)
                        await websocket.send_text(status_msg)
                        last_status = execution.status

                    # Read output file
                    output_file = script_manager.script_dir / f"output_{execution_id}.txt"
                    if output_file.exists():
                        try:
                            with open(output_file, "r") as f:
                                f.seek(last_position)
                                new_content = f.read()
                                if new_content:
                                    logger.debug(f"Sending new content: {new_content!r}")
                                    await websocket.send_text(new_content)
                                    last_position = f.tell()
                        except Exception as e:
                            logger.error(f"Error reading output file: {e}")

                    # If execution is complete, send final message and break
                    if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
                        # One final read attempt
                        if output_file.exists():
                            try:
                                with open(output_file, "r") as f:
                                    f.seek(last_position)
                                    final_content = f.read()
                                    if final_content:
                                        await websocket.send_text(final_content)
                            except Exception as e:
                                logger.error(f"Error reading final output: {e}")
                        
                        await websocket.send_text("Execution finished.")
                        break

                    await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

                except WebSocketDisconnect:
                    logger.warning("WebSocket disconnected during streaming")
                    return
                except Exception as e:
                    logger.error(f"Error during output streaming: {e}")
                    await websocket.close(code=4005, reason=str(e))
                    return

    except Exception as e:
        logger.exception("Error in WebSocket connection")
        try:
            await websocket.close(code=4007, reason=str(e))
        except:
            pass
    finally:
        logger.info(f"WebSocket connection closed for execution {execution_id}")