import asyncio
import logging
import os
import shutil
import sys
import venv
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Dict, Any, Coroutine
import time
from typing import IO as TextIO
import io
import aiofiles

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .config import settings
from .database import get_session_context
from .models import Dependency, Execution, ExecutionStatus, Script

logger = logging.getLogger(__name__)


async def _stream_generator(stream: asyncio.StreamReader, file: TextIO, is_stderr: bool) -> AsyncGenerator[str, None]:
    """Read from a stream and write to file."""
    logger = logging.getLogger(__name__)
    
    try:
        while True:
            try:
                line = await asyncio.wait_for(stream.readline(), timeout=1.0)
                if not line:
                    break
                    
                decoded_line = line.decode().rstrip('\n')
                
                # For file writing, add ERROR: prefix for stderr
                file_output_line = f"ERROR: {decoded_line}\n" if is_stderr else f"{decoded_line}\n"
                
                # Write to file with prefix for stderr
                try:
                    file.write(file_output_line)
                    await asyncio.to_thread(file.flush)  # Flush in thread to avoid blocking
                    os.fsync(file.fileno())  # Ensure data is written to disk
                    yield decoded_line  # Yield without ERROR: prefix for real-time output
                except IOError as e:
                    logger.error(f"Error writing to file: {e}")
                    yield decoded_line  # Still yield without ERROR: prefix
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing line: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error in stream generator: {e}")
        raise

async def _stream_handler(stream: asyncio.StreamReader, file: TextIO, is_stderr: bool) -> List[str]:
    """Handle a single stream (stdout or stderr) and write to file."""
    logger = logging.getLogger(__name__)
    output_lines = []
    
    try:
        async for line in _stream_generator(stream, file, is_stderr):
            output_lines.append(line)
    except Exception as e:
        logger.error(f"Error in stream handler: {e}")
        raise
    finally:
        # Ensure stream is properly closed
        try:
            stream.feed_eof()  # Signal EOF to the stream
            # Drain any remaining data
            while not stream.at_eof():
                await stream.read()
        except Exception as e:
            logger.error(f"Error closing stream: {e}")
    
    return output_lines

class ScriptManager:
    """Manages script execution in isolated environments."""
    
    def __init__(self, script_id: int, base_dir: str | Path | None = None):
        """Initialize script manager."""
        self.script_id = script_id
        self.base_dir = Path(base_dir if base_dir is not None else settings.scripts_dir).resolve()
        self.script_dir = self.base_dir / str(script_id)
        self.venv_dir = self.script_dir / "venv"
        self.script_path = self.script_dir / "script.py"
        self.requirements_path = self.script_dir / "requirements.txt"
        self.pip_log_path = self.script_dir / "pip.log"
    
    @property
    def python_path(self) -> Path:
        """Get the path to the virtual environment's Python interpreter."""
        if sys.platform == "win32":
            return self.venv_dir / "Scripts" / "python.exe"
        return self.venv_dir / "bin" / "python"
    
    async def setup_environment(self, script_content: str, dependencies: List[Dependency]) -> None:
        """Set up the script environment."""
        logger.info(f"Setting up environment for script {self.script_id}")
        
        try:
            # Create script directory if it doesn't exist
            self.script_dir.mkdir(parents=True, exist_ok=True)
            
            # Write script content
            script_path = self.script_dir / "script.py"
            script_path.write_text(script_content)
            
            # Write requirements.txt (but don't install)
            requirements = []
            for dep in dependencies:
                if not dep.version_spec or dep.version_spec in ['*', '']:
                    requirements.append(dep.package_name)
                elif dep.version_spec.startswith('=='):
                    requirements.append(f"{dep.package_name}{dep.version_spec}")
                elif dep.version_spec.startswith(('>=', '<=', '>', '<', '~=')):
                    requirements.append(f"{dep.package_name}{dep.version_spec}")
                else:
                    requirements.append(dep.package_name)
            
            self.requirements_path.write_text("\n".join(requirements))
            
        except Exception as e:
            logger.error(f"Error setting up environment: {e}")
            raise

    async def _run_pip(self, *args: str) -> None:
        """Run pip command in the virtual environment."""
        logger = logging.getLogger(__name__)
        logger.info(f"Running pip command: {' '.join(args)}")
        
        # Ensure script directory exists
        os.makedirs(str(self.script_dir), exist_ok=True)
        
        # Set up output file
        output_file = self.script_dir / "pip_output.txt"
        if output_file.exists():
            output_file.unlink()
        
        # Create process with output redirection
        process = await asyncio.create_subprocess_exec(
            str(self.python_path),
            "-m",
            "pip",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.script_dir)
        )
        
        if process.stdout is None or process.stderr is None:
            raise RuntimeError("Failed to create pip process streams")
        
        try:
            # Process output in real-time
            async def write_output(stream: asyncio.StreamReader, is_stderr: bool = False) -> None:
                try:
                    while True:
                        line = await stream.readline()
                        if not line:
                            break
                        try:
                            # Write to file
                            async with aiofiles.open(output_file, mode='ab') as f:
                                await f.write(line)
                                await f.flush()
                                os.fsync(f.fileno())
                        except Exception as e:
                            logger.error(f"Error writing to pip output file: {e}")
                
                except Exception as e:
                    logger.error(f"Error processing pip {'stderr' if is_stderr else 'stdout'}: {e}")
            
            # Create tasks for both streams
            stdout_task = asyncio.create_task(write_output(process.stdout))
            stderr_task = asyncio.create_task(write_output(process.stderr, True))
            
            # Wait for process to complete and streams to be fully processed
            exit_code = await process.wait()
            await stdout_task
            await stderr_task
            
            if exit_code != 0:
                error_msg = f"pip command failed with exit code {exit_code}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
        except Exception as e:
            logger.error(f"Error running pip command: {e}")
            raise
        
        finally:
            # Ensure process is terminated
            if process.returncode is None:
                try:
                    process.terminate()
                    await process.wait()
                except Exception as e:
                    logger.error(f"Error terminating pip process: {e}")

    async def has_uninstalled_dependencies(self) -> bool:
        """Check if script has any uninstalled dependencies."""
        try:
            # First check if virtual environment exists
            if not self.venv_dir.exists() or not self.python_path.exists():
                logger.warning(f"Virtual environment not found for script {self.script_id}")
                return True
                
            async with get_session_context() as session:
                # Get a fresh copy of the script with dependencies
                result = await session.execute(
                    select(Script)
                    .options(selectinload(Script.dependencies))
                    .where(Script.id == self.script_id)
                )
                script = result.scalar_one_or_none()
                
                if not script:
                    logger.error(f"Script {self.script_id} not found")
                    return False
                
                # Get currently installed versions
                installed_versions = await self.get_installed_versions()
                
                # Convert installed package names to lowercase for case-insensitive comparison
                installed_packages = {name.lower(): version for name, version in installed_versions.items()}
                
                # Check each dependency
                for dep in script.dependencies:
                    package_name_lower = dep.package_name.lower()
                    if package_name_lower not in installed_packages:
                        logger.warning(f"Package {dep.package_name} not found in installed packages")
                        return True
                        
                    installed_version = installed_packages[package_name_lower]
                    if not installed_version:
                        logger.warning(f"Package {dep.package_name} has no version installed")
                        return True
                        
                    # Find the actual package name with correct case
                    actual_name = next(
                        name for name in installed_versions.keys()
                        if name.lower() == package_name_lower
                    )
                    
                    # Update installed version in database if changed
                    if installed_version != dep.installed_version:
                        dep.installed_version = installed_version
                        await session.commit()
                        logger.info(f"Updated installed version for {actual_name} to {installed_version}")
                
                return False
                
        except Exception as e:
            logger.error(f"Error checking dependencies: {e}")
            return False

    async def execute(self, execution_id: int) -> AsyncGenerator[str, None]:
        """Execute the script and stream its output."""
        logger.info(f"Executing script {self.script_id}")
        
        # Check for uninstalled dependencies first
        if await self.has_uninstalled_dependencies():
            logger.error(f"Script {self.script_id} has uninstalled dependencies")
            raise RuntimeError("Cannot execute script with uninstalled dependencies")
        
        # Set up output file
        output_file = self.script_dir / f"output_{execution_id}.txt"
        if output_file.exists():
            output_file.unlink()
        
        # Create process with output redirection
        process = await asyncio.create_subprocess_exec(
            str(self.python_path),
            str(self.script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.script_dir)
        )
        
        if process.stdout is None or process.stderr is None:
            raise RuntimeError("Failed to create process streams")
        
        # Open output file
        with open(output_file, 'w', encoding='utf-8', buffering=1) as f:
            # Process stdout and stderr concurrently
            stdout_task = asyncio.create_task(
                _stream_handler(process.stdout, f, False)
            )
            stderr_task = asyncio.create_task(
                _stream_handler(process.stderr, f, True)
            )
            
            try:
                # Wait for both streams to complete
                stdout_lines = await stdout_task
                stderr_lines = await stderr_task
                
                # Wait for process to complete
                return_code = await process.wait()
                
                # Yield all lines
                for line in stdout_lines + stderr_lines:
                    yield line
                
                # Yield return code if non-zero
                if return_code != 0:
                    yield f"Error: Script exited with return code {return_code}"
                    
            except Exception as e:
                logger.error(f"Error during execution: {e}")
                yield f"Error: {str(e)}"
                raise

    def cleanup(self, remove_environment: bool = False) -> None:
        """Clean up script environment.
        
        Args:
            remove_environment: If True, removes the entire script directory including venv.
                              If False, only removes temporary files (default).
        """
        if not self.script_dir.exists():
            return

        logger.info(f"Cleaning up script {self.script_id} (remove_environment={remove_environment})")
        
        # Clean up temporary files
        try:
            # Remove output files
            for file in self.script_dir.glob("output_*.txt"):
                try:
                    file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove output file {file}: {e}")
            
            # Remove pip output file
            if self.pip_log_path.exists():
                try:
                    self.pip_log_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove pip log file: {e}")
                
            # Remove pip status files
            for status_file in ["pip_finished", "pip_success"]:
                status_path = self.script_dir / status_file
                if status_path.exists():
                    try:
                        status_path.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to remove status file {status_file}: {e}")
        
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {e}")
        
        # If remove_environment is True, remove everything
        if remove_environment:
            try:
                # First try to remove the venv directory
                if self.venv_dir.exists():
                    try:
                        # On Windows, some files might be locked, so we need multiple attempts
                        max_attempts = 3
                        for attempt in range(max_attempts):
                            try:
                                shutil.rmtree(self.venv_dir, ignore_errors=False)
                                break
                            except OSError as e:
                                if attempt == max_attempts - 1:
                                    logger.error(f"Failed to remove venv directory after {max_attempts} attempts: {e}")
                                else:
                                    time.sleep(0.5)  # Wait before retry
                    except Exception as e:
                        logger.error(f"Error cleaning up venv directory: {e}")
                
                # Then try to remove the script directory
                try:
                    if self.script_dir.exists():
                        # Try to ensure no processes are using the directory
                        for root, dirs, files in os.walk(self.script_dir, topdown=False):
                            for name in files:
                                try:
                                    os.chmod(os.path.join(root, name), 0o777)
                                except:
                                    pass
                            for name in dirs:
                                try:
                                    os.chmod(os.path.join(root, name), 0o777)
                                except:
                                    pass
                        
                        # Attempt to remove the directory
                        max_attempts = 3
                        for attempt in range(max_attempts):
                            try:
                                shutil.rmtree(self.script_dir, ignore_errors=False)
                                break
                            except OSError as e:
                                if attempt == max_attempts - 1:
                                    logger.error(f"Failed to remove script directory after {max_attempts} attempts: {e}")
                                else:
                                    time.sleep(0.5)  # Wait before retry
                except Exception as e:
                    logger.error(f"Error cleaning up script directory: {e}")
                    # If we can't remove it normally, try force removal
                    try:
                        os.system(f"rm -rf {self.script_dir}")
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error removing environment: {e}")

    async def check_dependencies(self) -> List[str]:
        """Check for outdated dependencies."""
        if not self.venv_dir.exists() or not self.python_path.exists():
            return []
            
        logger.info(f"Checking dependencies for script {self.script_id}")
        cmd = [
            str(self.python_path),
            "-m",
            "pip",
            "list",
            "--outdated",
            "--format=json"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.script_dir),
        )
        
        stdout, _ = await process.communicate()
        if stdout:
            import json
            outdated = json.loads(stdout)
            return [
                f"{pkg['name']} ({pkg['version']} -> {pkg['latest_version']})"
                for pkg in outdated
            ]
        return []

    async def get_installed_versions(self) -> Dict[str, str]:
        """Get installed versions of all packages in the virtual environment."""
        if not self.venv_dir.exists() or not self.python_path.exists():
            return {}
        
        logger.info(f"Getting installed versions for script {self.script_id}")
        cmd = [
            str(self.python_path),
            "-m",
            "pip",
            "list",
            "--format=json"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.script_dir),
        )
        
        stdout, _ = await process.communicate()
        if stdout:
            import json
            packages = json.loads(stdout)
            return {
                pkg['name']: pkg['version']
                for pkg in packages
            }
        return {}

    async def uninstall_dependency(self, package_name: str) -> None:
        """Uninstall a package from the script's virtual environment."""
        logger.info(f"Uninstalling {package_name} from script {self.script_id}")
        
        if not self.venv_dir.exists():
            raise Exception(f"Virtual environment not found at {self.venv_dir}")
        
        pip_executable = self.venv_dir / "bin" / "pip"
        if not pip_executable.exists():
            pip_executable = self.venv_dir / "Scripts" / "pip.exe"  # Windows fallback
        
        if not pip_executable.exists():
            raise Exception("pip not found in virtual environment")
        
        try:
            process = await asyncio.create_subprocess_exec(
                str(pip_executable), "uninstall", "-y", package_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error during uninstallation"
                logger.error(f"Failed to uninstall {package_name}: {error_msg}")
                raise Exception(f"Failed to uninstall package: {error_msg}")
            
            logger.info(f"Successfully uninstalled {package_name}")
            
        except Exception as e:
            logger.error(f"Error during uninstallation of {package_name}: {str(e)}")
            raise Exception(f"Error uninstalling package: {str(e)}")
            
    def get_requirements_path(self) -> str:
        """Get the path to the requirements.txt file for this script."""
        return str(self.requirements_path)

    async def read_output(self, execution_id: int) -> AsyncGenerator[str, None]:
        """Read output from a running execution."""
        logger = logging.getLogger(__name__)
        output_file = self.script_dir / f"output_{execution_id}.txt"
        
        # Keep track of where we are in the file
        position = 0
        last_incomplete_line = ""
        
        while True:
            try:
                # Check if execution is still running
                async with get_session_context() as session:
                    execution = await session.get(Execution, execution_id)
                    if not execution:
                        logger.error(f"Execution {execution_id} not found")
                        break
                    
                    is_finished = execution.status not in [ExecutionStatus.RUNNING, ExecutionStatus.PENDING]
                    
                    # Read new content if file exists
                    if output_file.exists():
                        try:
                            with open(output_file, "r") as f:
                                # Seek to last position
                                f.seek(position)
                                
                                # Read any new content
                                new_content = f.read()
                                if new_content:
                                    logger.debug(f"Read new content from position {position}: {new_content!r}")
                                    
                                    # Update position for next read
                                    position = f.tell()
                                    
                                    # Process the content
                                    if last_incomplete_line:
                                        new_content = last_incomplete_line + new_content
                                        last_incomplete_line = ""
                                        logger.debug(f"Added incomplete line to content: {new_content!r}")
                                    
                                    # Split into lines, preserving line endings
                                    lines = new_content.splitlines(True)
                                    
                                    # Process all complete lines
                                    for line in lines:
                                        if line.endswith('\n'):
                                            logger.debug(f"Yielding complete line: {line!r}")
                                            yield line
                                        else:
                                            # Save incomplete line for next iteration
                                            last_incomplete_line = line
                                            logger.debug(f"Saving incomplete line: {line!r}")
                        except Exception as e:
                            logger.error(f"Error reading output file: {e}")
                            # Don't break, try again next iteration
                    
                    # If execution is finished and we've read all content
                    if is_finished:
                        # One final read attempt for any remaining content
                        if output_file.exists():
                            try:
                                with open(output_file, "r") as f:
                                    f.seek(position)
                                    remaining = f.read()
                                    if remaining:
                                        logger.debug(f"Reading final content: {remaining!r}")
                                        if last_incomplete_line:
                                            remaining = last_incomplete_line + remaining
                                            logger.debug(f"Added incomplete line to final content: {remaining!r}")
                                        yield remaining
                            except Exception as e:
                                logger.error(f"Error reading final output: {e}")
                        break
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error reading output: {e}")
                break 