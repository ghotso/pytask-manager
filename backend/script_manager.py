import asyncio
import logging
import os
import shutil
import sys
import venv
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Dict
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_session_context
from .models import Dependency, Execution, ExecutionStatus, Script

logger = logging.getLogger(__name__)


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
        
        # Clean up any existing environment first
        self.cleanup()
        
        try:
            # Create script directory with proper permissions
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
            
            # Create virtual environment
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
            
            # Install dependencies if any
            if dependencies:
                logger.info("Installing dependencies")
                # Write requirements.txt with proper version specs
                requirements = []
                for dep in dependencies:
                    if not dep.version_spec or dep.version_spec in ['*', '']:
                        # For wildcard or empty version spec, just use the package name
                        requirements.append(dep.package_name)
                    elif dep.version_spec.startswith('=='):
                        # Exact version requirement
                        requirements.append(f"{dep.package_name}{dep.version_spec}")
                    elif dep.version_spec.startswith(('>=', '<=', '>', '<', '~=')):
                        # Standard version comparisons
                        requirements.append(f"{dep.package_name}{dep.version_spec}")
                    else:
                        # For any other format, default to latest version
                        requirements.append(dep.package_name)
                
                self.requirements_path.write_text("\n".join(requirements))
                
                try:
                    # Install requirements
                    await self._run_pip(
                        "install",
                        "-r", str(self.requirements_path),
                        "--no-cache-dir"  # Avoid caching issues
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
            # Clean up on failure
            self.cleanup()
            raise

    async def _run_pip(self, *args: str) -> None:
        """Run pip command in the virtual environment."""
        if not self.python_path.exists():
            raise RuntimeError(f"Python executable not found at {self.python_path}")
            
        cmd = [
            str(self.python_path),
            "-m",
            "pip",
            *args
        ]
        
        logger.debug(f"Running pip command: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.script_dir),
        )
        
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"Pip command failed: {error_msg}")
            raise RuntimeError(f"Failed to run pip: {error_msg}")
        
        if stdout:
            logger.debug(f"Pip output: {stdout.decode()}")

    async def _collect_stream(self, stream: asyncio.StreamReader) -> List[str]:
        """Collect all lines from a stream with timeout per line."""
        lines = []
        while True:
            try:
                # Read each line with a timeout
                try:
                    line = await asyncio.wait_for(stream.readline(), timeout=10)  # 10 seconds per line
                except asyncio.TimeoutError:
                    logger.warning("Timeout reading stream line")
                    break
                
                if not line:
                    break
                
                text = line.decode().rstrip('\n')
                logger.debug(f"Collected line: {text!r}")
                lines.append(text + '\n')
            
            except Exception as e:
                logger.error(f"Error reading stream: {e}")
                break
            
        return lines

    async def execute(self, execution_id: int) -> AsyncGenerator[str, None]:
        """Execute the script and stream its output."""
        logger.info(f"Executing script {self.script_id}")
        process = None
        output_file = self.script_dir / f"output_{execution_id}.txt"
        
        try:
            # Ensure script file exists
            script_file = self.script_dir / "script.py"
            if not script_file.exists():
                logger.error(f"Script file not found: {script_file}")
                raise FileNotFoundError(f"Script file not found: {script_file}")
            
            # Create process with line buffering
            cmd = [str(self.python_path), "-u", str(script_file)]  # Add -u for unbuffered output
            logger.debug(f"Running command: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.script_dir)
            )
            
            # Stream output with timeout
            assert process.stdout is not None
            assert process.stderr is not None

            # Process stdout and stderr concurrently
            while True:
                # Read from stdout and stderr
                stdout_line = await process.stdout.readline()
                stderr_line = await process.stderr.readline()
                
                # Process stdout
                if stdout_line:
                    decoded_line = stdout_line.decode().rstrip('\n')
                    output_line = f"{decoded_line}\n"
                    logger.debug(f"Stdout: {output_line!r}")
                    # Write and flush immediately
                    with open(output_file, "a") as f:
                        f.write(output_line)
                        f.flush()
                        os.fsync(f.fileno())  # Force write to disk
                    yield output_line
                
                # Process stderr
                if stderr_line:
                    decoded_line = stderr_line.decode().rstrip('\n')
                    error_line = f"ERROR: {decoded_line}\n"
                    logger.debug(f"Stderr: {error_line!r}")
                    # Write and flush immediately
                    with open(output_file, "a") as f:
                        f.write(error_line)
                        f.flush()
                        os.fsync(f.fileno())  # Force write to disk
                    yield error_line
                
                # Check if process has ended and both streams are empty
                if not stdout_line and not stderr_line:
                    if process.returncode is not None:
                        break
                    await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
                
                # Check if process has ended
                if process.returncode is not None and process.stdout.at_eof() and process.stderr.at_eof():
                    break
            
            # Wait for completion with timeout
            try:
                await asyncio.wait_for(process.wait(), timeout=300)  # 5 minutes timeout
            except asyncio.TimeoutError:
                logger.error("Script execution timed out after 5 minutes")
                if process.returncode is None:
                    process.terminate()
                    await asyncio.sleep(1)
                    if process.returncode is None:
                        process.kill()
                raise RuntimeError("Script execution timed out after 5 minutes")
            
            logger.debug(f"Process exited with return code {process.returncode}")
            if process.returncode != 0:
                error_msg = f"Error: Script exited with return code {process.returncode}\n"
                logger.error(f"Script execution failed with return code {process.returncode}")
                with open(output_file, "a") as f:
                    f.write(error_msg)
                    f.flush()
                    os.fsync(f.fileno())
                yield error_msg

        except Exception as e:
            error_msg = f"Error: {str(e)}\n"
            logger.exception("Error during script execution")
            with open(output_file, "a") as f:
                f.write(error_msg)
                f.flush()
                os.fsync(f.fileno())
            yield error_msg
            raise  # Re-raise to ensure proper cleanup

        finally:
            # Ensure process is terminated
            if process is not None and process.returncode is None:
                try:
                    process.terminate()
                    await asyncio.sleep(1)  # Give it a second to terminate
                    if process.returncode is None:
                        process.kill()  # Force kill if still running
                except Exception as e:
                    logger.error(f"Error cleaning up process: {e}")
            
            # Clean up output file
            try:
                if output_file.exists():
                    output_file.unlink()
            except Exception as e:
                logger.error(f"Error cleaning up output file: {e}")

    def cleanup(self) -> None:
        """Clean up script environment."""
        if not self.script_dir.exists():
            return

        logger.info(f"Cleaning up script {self.script_id}")
        
        # Clean up output files
        try:
            for file in self.script_dir.glob("output_*.txt"):
                try:
                    file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove output file {file}: {e}")
        except Exception as e:
            logger.warning(f"Error cleaning up output files: {e}")
        
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
                            # If we can't remove venv, we'll still try to remove the script dir
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
                                    # Update position for next read
                                    position = f.tell()
                                    
                                    # Process the content
                                    if last_incomplete_line:
                                        new_content = last_incomplete_line + new_content
                                        last_incomplete_line = ""
                                    
                                    # Split into lines, preserving line endings
                                    lines = new_content.splitlines(True)
                                    
                                    # Process all complete lines
                                    for line in lines:
                                        if line.endswith('\n'):
                                            logger.debug(f"Yielding line: {line!r}")
                                            yield line
                                        else:
                                            # Save incomplete line for next iteration
                                            last_incomplete_line = line
                                            logger.debug(f"Saving incomplete line: {line!r}")
                        except Exception as e:
                            logger.error(f"Error reading output file: {e}")
                            # Don't break, try again next iteration
                    
                    # If execution is finished and we've read all content, break
                    if is_finished:
                        # One final read attempt for any remaining content
                        if output_file.exists():
                            try:
                                with open(output_file, "r") as f:
                                    f.seek(position)
                                    remaining = f.read()
                                    if remaining:
                                        if last_incomplete_line:
                                            remaining = last_incomplete_line + remaining
                                        logger.debug(f"Yielding final content: {remaining!r}")
                                        yield remaining
                            except Exception as e:
                                logger.error(f"Error reading final output: {e}")
                        break
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error reading output: {e}")
                break 