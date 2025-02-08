"""Script scheduling service."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .config import settings
from .database import get_session_context
from .models import Schedule, Script, Execution, ExecutionStatus
from .script_manager import ScriptManager

logger = logging.getLogger(__name__)

class SchedulerService:
    """Service for managing script schedules."""
    
    def __init__(self):
        """Initialize scheduler service."""
        self.scheduler = AsyncIOScheduler()
        self._active_executions: Dict[int, asyncio.Task] = {}
        
    async def start(self):
        """Start the scheduler service."""
        logger.info("Starting scheduler service")
        
        # Clean up any stale executions from previous runs
        async with get_session_context() as session:
            stale_executions = await session.execute(
                select(Execution)
                .where(Execution.status.in_([ExecutionStatus.RUNNING, ExecutionStatus.PENDING]))
            )
            for execution in stale_executions.scalars():
                logger.warning(f"Found stale execution {execution.id}, marking as failed")
                execution.status = ExecutionStatus.FAILURE
                execution.completed_at = datetime.now(timezone.utc)
                execution.error_message = "Execution interrupted by server restart"
            await session.commit()
        
        # Load all schedules from active scripts
        async with get_session_context() as session:
            result = await session.execute(
                select(Schedule)
                .options(selectinload(Schedule.script))
                .join(Script)
                .where(Script.is_active == True)
            )
            schedules = result.scalars().all()
            
            for schedule in schedules:
                if schedule.script and schedule.script.is_active:
                    logger.info(f"Adding job for schedule {schedule.id} with cron: {schedule.cron_expression}")
                    self.scheduler.add_job(
                        self._execute_script,
                        CronTrigger.from_crontab(schedule.cron_expression),
                        id=f"script_{schedule.script_id}_schedule_{schedule.id}",
                        kwargs={
                            'script_id': schedule.script_id,
                            'schedule_id': schedule.id
                        },
                        replace_existing=True
                    )
        
        self.scheduler.start()
        
    async def stop(self):
        """Stop the scheduler service."""
        logger.info("Stopping scheduler service")
        
        # Wait for active executions to finish with a timeout
        if self._active_executions:
            logger.info(f"Waiting for {len(self._active_executions)} active executions to finish")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_executions.values(), return_exceptions=True),
                    timeout=10.0  # 10 second timeout
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for executions to finish")
        
        # Mark any remaining running executions as failed
        async with get_session_context() as session:
            running_executions = await session.execute(
                select(Execution)
                .where(Execution.status.in_([ExecutionStatus.RUNNING, ExecutionStatus.PENDING]))
            )
            for execution in running_executions.scalars():
                logger.warning(f"Marking execution {execution.id} as failed due to shutdown")
                execution.status = ExecutionStatus.FAILURE
                execution.completed_at = datetime.now(timezone.utc)
                execution.error_message = "Execution interrupted by server shutdown"
            await session.commit()
        
        # Cancel any remaining executions
        for task in self._active_executions.values():
            if not task.done():
                task.cancel()
            
        self.scheduler.shutdown()
        
    async def shutdown(self):
        """Shutdown the scheduler service."""
        logger.info("Shutting down scheduler service")
        await self.stop()
        
    async def add_job(self, schedule: Schedule) -> None:
        """Add a job to the scheduler."""
        if not schedule.script or not schedule.script.is_active:
            return
            
        # Check for uninstalled dependencies
        manager = ScriptManager(schedule.script.id)
        if await manager.has_uninstalled_dependencies():
            logger.warning(f"Script {schedule.script.id} has uninstalled dependencies, not scheduling")
            return
            
        job_id = self._get_job_id(schedule)
        
        # Remove any existing job first
        await self.remove_job(schedule)
        
        try:
            self.scheduler.add_job(
                self._run_script,
                CronTrigger.from_crontab(schedule.cron_expression),
                id=job_id,
                args=[schedule.script.id, schedule.id],
                replace_existing=True
            )
            logger.info(f"Added job {job_id} with cron: {schedule.cron_expression}")
        except Exception as e:
            logger.error(f"Failed to add job {job_id}: {e}")
        
    async def remove_job(self, schedule: Schedule):
        """Remove a scheduled job."""
        if not schedule or not schedule.id:
            logger.warning("Cannot remove job for invalid schedule")
            return
            
        job_id = f"script_{schedule.script_id}_schedule_{schedule.id}"
        try:
            logger.info(f"Removing job {job_id}")
            self.scheduler.remove_job(job_id, jobstore='default')
        except Exception as e:
            logger.debug(f"Failed to remove job {job_id}: {str(e)}")
        
    async def _execute_script(self, script_id: int, schedule_id: int):
        """Execute a script as part of a scheduled job."""
        logger.info(f"Starting scheduled execution of script {script_id} from schedule {schedule_id}")
        execution_id = None
        output = []
        manager = None
        
        try:
            # First session for creating execution record
            async with get_session_context() as session:
                # Get script and create execution record
                result = await session.execute(
                    select(Script)
                    .options(selectinload(Script.dependencies))
                    .where(Script.id == script_id)
                )
                script = result.scalar_one_or_none()
                
                if not script or not script.is_active:
                    logger.warning(f"Script {script_id} not found or inactive")
                    return
                    
                execution = Execution(
                    script_id=script_id,
                    schedule_id=schedule_id,
                    status=ExecutionStatus.RUNNING,
                    started_at=datetime.now(timezone.utc)
                )
                session.add(execution)
                await session.commit()
                await session.refresh(execution)
                execution_id = execution.id
            
            # Create task for script execution
            manager = ScriptManager(script_id)
            task = asyncio.create_task(self._run_script_with_output(manager, script, execution_id))
            self._active_executions[execution_id] = task
            
            try:
                await task
            except asyncio.CancelledError:
                logger.warning(f"Execution {execution_id} was cancelled")
                async with get_session_context() as session:
                    execution = await session.get(Execution, execution_id)
                    if execution:
                        execution.status = ExecutionStatus.FAILURE
                        execution.completed_at = datetime.now(timezone.utc)
                        execution.error_message = "Execution cancelled"
                        await session.commit()
            except Exception as e:
                logger.exception(f"Error during script execution {execution_id}")
                async with get_session_context() as session:
                    execution = await session.get(Execution, execution_id)
                    if execution:
                        execution.status = ExecutionStatus.FAILURE
                        execution.completed_at = datetime.now(timezone.utc)
                        execution.error_message = str(e)
                        await session.commit()
            
        except Exception as e:
            logger.exception(f"Failed to handle script execution {script_id}")
            if execution_id:
                async with get_session_context() as session:
                    execution = await session.get(Execution, execution_id)
                    if execution:
                        execution.status = ExecutionStatus.FAILURE
                        execution.completed_at = datetime.now(timezone.utc)
                        execution.error_message = f"Execution handling failed: {str(e)}"
                        await session.commit()
        finally:
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]
            if manager:
                manager.cleanup(remove_environment=False)
    
    async def _run_script_with_output(
        self, 
        manager: ScriptManager, 
        script: Script, 
        execution_id: int
    ) -> None:
        """Run a script and collect its output."""
        output = []
        try:
            # Set up environment
            await manager.setup_environment(script.content, script.dependencies)
            
            # Execute and collect output
            async for line in manager.execute(execution_id):
                output.append(line)
                logger.debug(f"Script output: {line.strip()}")
            
            # Update execution record with success
            async with get_session_context() as session:
                execution = await session.get(Execution, execution_id)
                if execution:
                    execution.status = ExecutionStatus.SUCCESS
                    execution.completed_at = datetime.now(timezone.utc)
                    execution.log_output = "".join(output)
                    await session.commit()
                    
            logger.info(f"Script {script.id} executed successfully")
            
        except Exception as e:
            logger.exception(f"Script {script.id} execution failed")
            # Update execution record with error
            async with get_session_context() as session:
                execution = await session.get(Execution, execution_id)
                if execution:
                    execution.status = ExecutionStatus.FAILURE
                    execution.completed_at = datetime.now(timezone.utc)
                    execution.error_message = str(e)
                    execution.log_output = "".join(output)
                    await session.commit()

    def _get_job_id(self, schedule: Schedule) -> str:
        """Get the job ID for a schedule."""
        return f"script_{schedule.script_id}_schedule_{schedule.id}"

    async def _run_script(self, script_id: int, schedule_id: int) -> None:
        """Run a script as a scheduled job."""
        logger.info(f"Running scheduled script {script_id} (schedule {schedule_id})")
        
        try:
            async with get_session_context() as session:
                # Get script and schedule
                script = await session.get(Script, script_id)
                schedule = await session.get(Schedule, schedule_id)
                
                if not script or not schedule:
                    logger.error(f"Script {script_id} or schedule {schedule_id} not found")
                    return
                    
                # Check for uninstalled dependencies
                manager = ScriptManager(script_id)
                if await manager.has_uninstalled_dependencies():
                    logger.error(f"Script {script_id} has uninstalled dependencies, skipping scheduled execution")
                    
                    # Create failure execution record
                    execution = Execution(
                        script_id=script_id,
                        schedule_id=schedule_id,
                        status=ExecutionStatus.FAILURE,
                        started_at=datetime.now(timezone.utc),
                        completed_at=datetime.now(timezone.utc),
                        error_message="Cannot execute script with uninstalled dependencies"
                    )
                    session.add(execution)
                    await session.commit()
                    
                    # Remove the schedule
                    await self.remove_job(schedule)
                    return
                
                # Create execution record
                execution = Execution(
                    script_id=script_id,
                    schedule_id=schedule_id,
                    status=ExecutionStatus.PENDING,
                    started_at=datetime.now(timezone.utc),
                )
                session.add(execution)
                await session.commit()
                await session.refresh(execution)
                
                # Run script with output collection
                await self._run_script_with_output(manager, script, execution.id)
                
        except Exception as e:
            logger.exception(f"Error running scheduled script {script_id}")

scheduler_service = SchedulerService() 