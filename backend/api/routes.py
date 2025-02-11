"""API routes for the application."""
import asyncio
import logging
import os
import time
import venv
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
    # Base query with all needed relationships
    query = (
        select(Script)
        .options(selectinload(Script.tags))
        .options(selectinload(Script.dependencies))
        .options(selectinload(Script.schedules))
        .options(
            selectinload(
                Script.executions
            )
        )
    )
    
    # Add tag filter if specified
    if tag:
        query = query.join(Script.tags).where(Tag.name == tag)
    
    # Order by script ID to ensure consistent results
    query = query.order_by(Script.id)
    
    # Execute query and get results
    result = await session.execute(query)
    scripts = list(result.scalars().all())
    
    # For each script, find its last execution
    for script in scripts:
        if script.executions:
            # Sort executions by started_at in descending order and take the first one
            sorted_executions = sorted(
                script.executions,
                key=lambda x: x.started_at if x.started_at is not None else datetime.min.replace(tzinfo=timezone.utc),
                reverse=True
            )
            if sorted_executions:
                # Set the most recent execution as last_execution
                setattr(script, 'last_execution', sorted_executions[0])
            else:
                setattr(script, 'last_execution', None)
        else:
            setattr(script, 'last_execution', None)
    
    return scripts


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
            manager.cleanup(remove_environment=True)  # Remove everything since script is being deleted
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


@router.post("/scripts/{script_id}/execute", response_model=ExecutionRead)
async def execute_script(
    script_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> Execution:
    """Execute a script and return its execution details."""
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
        
        return execution
        
    except Exception as e:
        # Update execution record with error
        execution.status = ExecutionStatus.FAILURE
        execution.completed_at = datetime.now(timezone.utc)
        execution.error_message = f"Failed to set up script environment: {str(e)}"
        await session.commit()
        
        # Clean up temporary files only
        script_manager.cleanup(remove_environment=False)
        
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
    """WebSocket endpoint for script execution output streaming."""
    await websocket.accept()
    
    try:
        # Get the execution ID from the query parameters
        execution_id = int(websocket.query_params.get("execution_id", 0))
        if not execution_id:
            await websocket.send_text("Error: No execution ID provided")
            return
            
        # Get execution details
        result = await session.execute(
            select(Execution).where(Execution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        
        if not execution:
            await websocket.send_text(f"Error: Execution {execution_id} not found")
            return
        
        # Create script manager to read output
        manager = ScriptManager(script_id, base_dir=str(settings.scripts_dir))
        output_file = manager.script_dir / f"output_{execution.id}.txt"
        
        # Send initial connection message
        await websocket.send_text("Connected to execution stream...")
        
        # Wait for output file to be created (max 60 seconds)
        start_time = time.monotonic()
        should_break = False
        last_status = None
        
        while not output_file.exists() and not should_break:
            if time.monotonic() - start_time > 60:
                logger.warning(f"Output file not created within timeout for execution {execution_id}")
                await websocket.send_text("Error: Output file not created within timeout")
                return
            
            try:
                # Check execution status in a new session context
                async with get_session_context() as check_session:
                    result = await check_session.execute(
                        select(Execution).where(Execution.id == execution.id)
                    )
                    current_execution = result.scalar_one_or_none()
                    
                    if not current_execution:
                        logger.error(f"Execution {execution.id} not found during status check")
                        continue
                    
                    # Only send status update if it changed
                    if current_execution.status != last_status:
                        await websocket.send_text(f"STATUS: {current_execution.status}")
                        last_status = current_execution.status
                    
                    # Check if execution completed before output file was created
                    if current_execution.status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILURE]:
                        if current_execution.error_message:
                            await websocket.send_text(f"Error: {current_execution.error_message}")
                        
                        # For successful executions, wait a bit longer for the file
                        if current_execution.status == ExecutionStatus.SUCCESS:
                            if time.monotonic() - start_time <= 5:  # Give extra 5 seconds for file creation
                                await asyncio.sleep(0.5)
                                continue
                            else:
                                logger.warning(f"Execution {execution_id} succeeded but output file was not created")
                                await websocket.send_text("Warning: Execution completed but output file was not created")
                                return
                        
                        should_break = True
                        continue
            
            except Exception as e:
                logger.error(f"Error checking execution status: {e}")
                await asyncio.sleep(0.5)
                continue
            
            await asyncio.sleep(0.5)
        
        if should_break:
            return
            
        # Start reading output
        try:
            async for line in manager.read_output(execution.id):
                await websocket.send_text(line.rstrip())
                
                # Check execution status periodically
                async with get_session_context() as check_session:
                    result = await check_session.execute(
                        select(Execution).where(Execution.id == execution.id)
                    )
                    current_execution = result.scalar_one_or_none()
                    
                    if current_execution and current_execution.status != last_status:
                        await websocket.send_text(f"STATUS: {current_execution.status}")
                        last_status = current_execution.status
                        
                        if current_execution.status == ExecutionStatus.FAILURE and current_execution.error_message:
                            await websocket.send_text(f"Error: {current_execution.error_message}")
                    
        except Exception as e:
            logger.error(f"Error reading output: {e}")
            await websocket.send_text(f"Error reading output: {str(e)}")
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_text(f"Error: {str(e)}")
        except Exception:
            pass


@router.websocket("/scripts/{script_id}/dependencies/ws")
async def dependency_websocket_endpoint(
    websocket: WebSocket,
    script_id: int,
    session: AsyncSession = Depends(get_session),
):
    """WebSocket endpoint for real-time dependency installation logs."""
    logger = logging.getLogger(__name__)
    logger.info("Dependency WebSocket connection initiated")
    
    # Track file handle and position to prevent race conditions
    file_handle = None
    last_position = 0
    sent_messages = set()  # Track sent messages to prevent duplicates
    
    # Standard packages to filter out
    standard_packages = {'pip', 'setuptools', 'wheel'}
    
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        
        # Create script manager to read output
        manager = ScriptManager(script_id, base_dir=str(settings.scripts_dir))
        output_file = manager.script_dir / "pip_output.txt"
        
        # Send initial connection message only if not sent before
        initial_message = "Connected to dependency installation stream..."
        if initial_message not in sent_messages:
            await websocket.send_text(initial_message)
            sent_messages.add(initial_message)
            logger.info("Sent initial connection message")
        
        # Wait for output file to be created (max 30 seconds)
        start_time = time.monotonic()
        while not output_file.exists():
            if time.monotonic() - start_time > 30:
                logger.warning("Output file not created within timeout")
                await websocket.send_text("Error: Output file not created within timeout")
                return
            await asyncio.sleep(0.1)
            
            # Check for pip_finished file to detect early failures
            if (manager.script_dir / "pip_finished").exists():
                if not (manager.script_dir / "pip_success").exists():
                    logger.warning("Dependency installation failed")
                    await websocket.send_text("Error: Dependency installation failed")
                    return
        
        # Open file in binary mode for better buffering
        with open(output_file, 'rb') as file:
            file_handle = file
            
            while True:
                # Read new content
                file.seek(last_position)
                new_content = file.read()
                
                if new_content:
                    try:
                        # Decode and process new content line by line
                        text = new_content.decode('utf-8')
                        lines = text.splitlines()
                        
                        for line in lines:
                            # Remove ERROR: prefix from log lines
                            clean_line = line.replace('ERROR: ', '')
                            
                            # Skip lines related to standard packages
                            should_skip = any(
                                pkg in clean_line.lower()
                                for pkg in standard_packages
                            )
                            
                            if clean_line and not should_skip and clean_line not in sent_messages:
                                await websocket.send_text(clean_line)
                                sent_messages.add(clean_line)
                        
                        last_position = file.tell()
                    except UnicodeDecodeError as e:
                        logger.error(f"Failed to decode file content: {e}")
                        continue
                
                # Check if installation is complete by looking for a marker file
                if (manager.script_dir / "pip_finished").exists():
                    success = (manager.script_dir / "pip_success").exists()
                    status = "SUCCESS" if success else "FAILURE"
                    await websocket.send_text(f"STATUS: {status}")
                    await websocket.send_text("Installation finished.")
                    break
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
    except Exception as e:
        logger.error(f"Error in dependency WebSocket: {e}")
        try:
            await websocket.send_text(f"Error: {str(e)}")
        except:
            pass
    finally:
        if file_handle:
            file_handle.close()


async def _install_dependencies_task(script_id: int) -> None:
    """Background task for installing dependencies."""
    logger = logging.getLogger(__name__)
    manager = None
    
    try:
        async with get_session_context() as session:
            # Get the script
            script = await _get_script(session, script_id)
            
            # Create script manager
            manager = ScriptManager(script_id, base_dir=str(settings.scripts_dir))
            
            # Create marker files
            pip_finished = manager.script_dir / "pip_finished"
            pip_success = manager.script_dir / "pip_success"
            pip_output = manager.script_dir / "pip_output.txt"
            
            # Remove old marker files if they exist
            for file in [pip_finished, pip_success, pip_output]:
                if file.exists():
                    file.unlink()
            
            try:
                # Ensure script directory exists
                manager.script_dir.mkdir(parents=True, exist_ok=True)
                
                # Write requirements.txt
                requirements = []
                for dep in script.dependencies:
                    if not dep.version_spec or dep.version_spec in ['*', '']:
                        requirements.append(dep.package_name)
                    elif dep.version_spec.startswith('=='):
                        requirements.append(f"{dep.package_name}{dep.version_spec}")
                    elif dep.version_spec.startswith(('>=', '<=', '>', '<', '~=')):
                        requirements.append(f"{dep.package_name}{dep.version_spec}")
                    else:
                        requirements.append(dep.package_name)
                
                manager.requirements_path.write_text("\n".join(requirements))
                
                # Create virtual environment if it doesn't exist
                if not manager.venv_dir.exists() or not manager.python_path.exists():
                    builder = venv.EnvBuilder(
                        system_site_packages=False,
                        clear=True,
                        with_pip=True,
                        upgrade_deps=True,
                        symlinks=False
                    )
                    builder.create(manager.venv_dir)
                
                # Silently upgrade pip, setuptools, and wheel (no output logging)
                await manager._run_pip("install", "--upgrade", "pip", "setuptools", "wheel", "--quiet")
                
                # Install each dependency individually with full logging
                for dep in script.dependencies:
                    if not dep.version_spec or dep.version_spec in ['*', '']:
                        package_spec = dep.package_name
                    elif dep.version_spec.startswith('=='):
                        package_spec = f"{dep.package_name}{dep.version_spec}"
                    elif dep.version_spec.startswith(('>=', '<=', '>', '<', '~=')):
                        package_spec = f"{dep.package_name}{dep.version_spec}"
                    else:
                        package_spec = dep.package_name
                    await manager._run_pip("install", package_spec, "--no-cache-dir")
                
                # Get installed versions
                installed_versions = await manager.get_installed_versions()
                
                # Update dependencies with installed versions
                for dep in script.dependencies:
                    if dep.package_name.lower() in {k.lower() for k in installed_versions.keys()}:
                        actual_name = next(
                            k for k in installed_versions.keys() 
                            if k.lower() == dep.package_name.lower()
                        )
                        dep.installed_version = installed_versions[actual_name]
                
                await session.commit()
                
                # Mark installation as successful
                pip_success.touch()
                
            except Exception as e:
                logger.error(f"Error during dependency installation: {e}")
                # Don't create success file, but do create finished file
                raise
            
            finally:
                # Mark installation as finished regardless of outcome
                pip_finished.touch()
                
    except Exception as e:
        logger.exception(f"Error installing dependencies for script {script_id}")
        raise


@router.post("/scripts/{script_id}/install-dependencies")
async def install_dependencies(
    script_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Install dependencies for a script."""
    try:
        logger.info(f"Starting dependency installation for script {script_id}")
        
        # Schedule the installation in the background
        background_tasks.add_task(_install_dependencies_task, script_id)
        
        return {
            "message": "Dependency installation started",
            "status": "pending"
        }
        
    except Exception as e:
        logger.exception(f"Error initiating dependency installation for script {script_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start dependency installation: {str(e)}"
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
        # Clean up temporary files only
        if manager:
            try:
                manager.cleanup(remove_environment=False)
            except:
                pass


@router.websocket("/executions/{execution_id}/output")
async def execution_output(websocket: WebSocket, execution_id: int):
    """Stream execution output via WebSocket."""
    await websocket.accept()
    
    try:
        # Get initial execution status
        async with get_session_context() as session:
            execution = await session.get(Execution, execution_id)
            if not execution:
                await websocket.close(code=4004, reason="Execution not found")
                return
            
            script = await session.get(Script, execution.script_id)
            if not script:
                await websocket.close(code=4004, reason="Script not found")
                return
            
            # Initialize script manager
            manager = ScriptManager(script.id)
            
            # Stream output
            try:
                async for line in manager.read_output(execution_id):
                    # Get fresh execution status
                    async with get_session_context() as status_session:
                        current_execution = await status_session.get(Execution, execution_id)
                        if current_execution and current_execution.status == ExecutionStatus.FAILURE:
                            # If execution failed, send error message
                            error_msg = current_execution.error_message or "Unknown error occurred"
                            await websocket.send_text(f"STATUS: {current_execution.status}\nError: {error_msg}")
                            break
                        elif current_execution and current_execution.status == ExecutionStatus.SUCCESS:
                            # If execution succeeded, send success message
                            await websocket.send_text(f"STATUS: {current_execution.status}")
                            break
                        
                    # Send output line
                    if line:
                        await websocket.send_text(line)
                        
            except Exception as e:
                logger.error(f"Error reading output: {e}")
                await websocket.send_text(f"Error: {str(e)}")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for execution {execution_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")
        try:
            await websocket.close(code=4000, reason=str(e))
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass