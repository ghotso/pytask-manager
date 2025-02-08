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
        """Set up the script environment with virtual environment and dependencies."""
        logger.info(f"Setting up environment for script {self.script_id}")
        
        try:
            # Create script directory if it doesn't exist
            self.script_dir.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(str(self.script_dir), 0o777)  # Ensure directory is writable
            except Exception as e:
                logger.warning(f"Failed to set directory permissions: {e}")
            
            # Write script content
            logger.debug(f"Writing script content to {self.script_path}")
            self.script_path.write_text(script_content)
            try:
                os.chmod(str(self.script_path), 0o666)  # Make script readable/writable
            except Exception as e:
                logger.warning(f"Failed to set script file permissions: {e}")
            
            # Create virtual environment only if it doesn't exist
            if not self.venv_dir.exists() or not self.python_path.exists():
                logger.info(f"Creating virtual environment in {self.venv_dir}")
                try:
                    builder = venv.EnvBuilder(
                        system_site_packages=False,
                        clear=True,
                        with_pip=True,
                        upgrade_deps=True,
                        symlinks=False  # More compatible across systems
                    )
                    builder.create(self.venv_dir)
                    
                    # Make Python executable actually executable on Unix
                    if sys.platform != "win32":
                        try:
                            self.python_path.chmod(0o755)
                        except Exception as e:
                            logger.warning(f"Failed to set Python executable permissions: {e}")
                    
                    # Verify Python executable exists
                    if not self.python_path.exists():
                        raise RuntimeError(f"Failed to create Python executable at {self.python_path}")
                    
                    # Upgrade pip to latest version
                    await self._run_pip("install", "--upgrade", "pip", "setuptools", "wheel")
                    
                except Exception as e:
                    logger.error(f"Failed to create virtual environment: {e}")
                    raise RuntimeError(f"Failed to create virtual environment: {e}")
            
            # Install or update dependencies if any
            if dependencies:
                logger.info("Installing/updating dependencies")
                # Write requirements.txt with proper version specs
                requirements = []
                for dep in dependencies:
                    if not dep.version_spec or dep.version_spec in ['*', '']:
                        # For wildcard or empty version spec, just use the package name
                        # without any version specification to get the latest version
                        requirements.append(dep.package_name.strip())
                    elif dep.version_spec.startswith('=='):
                        # Exact version requirement
                        requirements.append(f"{dep.package_name.strip()}{dep.version_spec}")
                    elif dep.version_spec.startswith(('>=', '<=', '>', '<', '~=')):
                        # Standard version comparisons
                        requirements.append(f"{dep.package_name.strip()}{dep.version_spec}")
                    else:
                        # For any other format, treat it as an exact version if it's a valid version string
                        version = dep.version_spec.strip()
                        if version and not version.startswith(('*', '=')):
                            requirements.append(f"{dep.package_name.strip()}=={version}")
                        else:
                            # Default to latest version if version spec is invalid
                            requirements.append(dep.package_name.strip())
                
                logger.debug(f"Writing requirements: {requirements}")
                self.requirements_path.write_text("\n".join(requirements))
                
                try:
                    # Install/update requirements
                    await self._run_pip(
                        "install",
                        "-r", str(self.requirements_path),
                        "--no-cache-dir",  # Avoid caching issues
                        "--upgrade"  # Ensure packages are updated if needed
                    )
                    
                    # Update installed versions
                    installed_versions = await self.get_installed_versions()
                    for dep in dependencies:
                        if dep.package_name in installed_versions:
                            dep.installed_version = installed_versions[dep.package_name]
                            
                except Exception as e:
                    logger.error(f"Failed to install dependencies: {e}")
                    raise RuntimeError(f"Failed to install dependencies: {e}")
        
        except Exception as e:
            logger.error(f"Failed to set up environment: {e}")
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
        """Check if any dependencies are not installed."""
        if not self.venv_dir.exists() or not self.python_path.exists():
            return True
            
        installed_versions = await self.get_installed_versions()
        async with get_session_context() as session:
            script = await session.get(Script, self.script_id)
            if not script:
                return True
                
            for dep in script.dependencies:
                if not dep.installed_version or dep.package_name.lower() not in {k.lower() for k in installed_versions.keys()}:
                    return True
            
            return False

    async def execute(self, execution_id: int) -> AsyncGenerator[str, None]:
        """Execute the script and stream its output."""
        logger.info(f"Executing script {self.script_id}")
        
        # Check for uninstalled dependencies first
        if await self.has_uninstalled_dependencies():
            yield "Error: Cannot execute script with uninstalled dependencies\n"
            raise RuntimeError("Cannot execute script with uninstalled dependencies")
            
        # Create output file path
        output_file_path = self.script_dir / f"output_{execution_id}.txt"
        script_path = self.script_path
        process = None
        stdout_task = None
        stderr_task = None
        output_file = None
        binary_file = None
        
        try:
            # Ensure script exists
            if not script_path.exists():
                raise FileNotFoundError(f"Script file not found: {script_path}")
            
            # Create output file immediately to ensure it exists for WebSocket
            output_file_path.touch()
            
            # Open output file in binary mode first for better buffering
            binary_file = open(str(output_file_path), "wb", buffering=0)  # Unbuffered binary stream
            output_file = io.TextIOWrapper(
                binary_file,
                encoding='utf-8',
                write_through=True,  # Ensure writes go directly to the binary stream
                line_buffering=True  # Enable line buffering
            )
            
            # Write initial message to ensure file has content
            output_file.write("Starting script execution...\n")
            output_file.flush()
            
            # Create subprocess with timeout handling
            try:
                process = await asyncio.create_subprocess_exec(
                    str(self.python_path),
                    "-u",  # Unbuffered output
                    str(script_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=os.environ.copy(),
                    limit=8192  # Limit subprocess pipe buffer size
                )
                
                if process.stdout is None or process.stderr is None:
                    raise RuntimeError("Failed to create subprocess pipes")
                
                # Set up stream tasks with timeout
                try:
                    stdout_task = asyncio.create_task(
                        _stream_handler(process.stdout, output_file, False)
                    )
                    stderr_task = asyncio.create_task(
                        _stream_handler(process.stderr, output_file, True)
                    )
                    
                    # Wait for process with timeout
                    try:
                        await asyncio.wait_for(process.wait(), timeout=settings.max_execution_time)
                    except asyncio.TimeoutError:
                        logger.error("Script execution timed out")
                        yield "Error: Script execution timed out after {settings.max_execution_time} seconds\n"
                        raise RuntimeError(f"Script timed out after {settings.max_execution_time} seconds")
                    
                    # Wait for stream tasks to complete with timeout
                    try:
                        stdout_result, stderr_result = await asyncio.gather(
                            stdout_task,
                            stderr_task,
                            return_exceptions=True
                        )
                        
                        # Check for task exceptions
                        for result in [stdout_result, stderr_result]:
                            if isinstance(result, Exception):
                                logger.error(f"Stream task failed: {result}")
                                raise result
                        
                    except Exception as e:
                        logger.error(f"Error in stream tasks: {e}")
                        raise
                    
                    # Check process return code
                    if process.returncode != 0:
                        error_msg = f"Error: Script exited with return code {process.returncode}\n"
                        output_file.write(error_msg)
                        output_file.flush()
                        yield error_msg
                    
                    # Read and yield output
                    try:
                        with open(str(output_file_path), 'r') as f:
                            content = f.read()
                            if content:
                                yield content
                    except Exception as e:
                        logger.error(f"Error reading output file: {e}")
                        raise
                    
                except Exception as e:
                    logger.error(f"Error during execution: {e}")
                    raise
                
            except Exception as e:
                logger.error(f"Error in execute: {e}")
                raise
            
        except Exception as e:
            logger.error(f"Error in execute: {e}")
            raise
        
        finally:
            # Clean up resources in reverse order of creation
            if stdout_task and not stdout_task.done():
                stdout_task.cancel()
            if stderr_task and not stderr_task.done():
                stderr_task.cancel()
            
            # Close file handles
            if output_file:
                try:
                    output_file.flush()
                    output_file.close()
                except:
                    pass
            if binary_file:
                try:
                    binary_file.close()
                except:
                    pass
            
            # Terminate process if still running
            if process and process.returncode is None:
                try:
                    process.terminate()
                    try:
                        # Wait for process to terminate
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        # Force kill if terminate doesn't work
                        process.kill()
                        await process.wait()
                except Exception as e:
                    logger.error(f"Error terminating process: {e}")
                    # Try force kill as last resort
                    try:
                        process.kill()
                        await process.wait()
                    except:
                        pass

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