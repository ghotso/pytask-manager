import asyncio
import logging
import os
import shutil
import sys
import venv
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
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
        
        try:
            # Create script directory with proper permissions
            self.script_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(str(self.script_dir), 0o777)  # Ensure directory is writable
            
            # Write script content
            logger.debug(f"Writing script content to {self.script_path}")
            self.script_path.write_text(script_content)
            os.chmod(str(self.script_path), 0o666)  # Make script readable/writable
            
            # Remove existing venv if it's broken
            if self.venv_dir.exists() and not self.python_path.exists():
                logger.warning("Found broken virtual environment, removing it")
                shutil.rmtree(self.venv_dir)
            
            # Create virtual environment if it doesn't exist
            if not self.venv_dir.exists():
                logger.info(f"Creating virtual environment in {self.venv_dir}")
                builder = venv.EnvBuilder(
                    system_site_packages=False,
                    clear=True,
                    with_pip=True,
                    upgrade_deps=True,
                    symlinks=False  # More compatible across systems
                )
                builder.create(self.venv_dir)
                
                # Verify Python executable exists
                if not self.python_path.exists():
                    raise RuntimeError(f"Failed to create Python executable at {self.python_path}")
                
                # Make Python executable actually executable on Unix
                if sys.platform != "win32":
                    self.python_path.chmod(0o755)
                
                # Upgrade pip to latest version
                await self._run_pip("install", "--upgrade", "pip", "setuptools", "wheel")
            
            # Install dependencies if any
            if dependencies:
                logger.info("Installing dependencies")
                # Write requirements.txt
                requirements = [
                    f"{dep.package_name}{dep.version_spec if dep.version_spec not in ['*', ''] else ''}"
                    for dep in dependencies
                ]
                self.requirements_path.write_text("\n".join(requirements))
                
                # Install requirements
                await self._run_pip(
                    "install",
                    "-r", str(self.requirements_path),
                    "--log", str(self.pip_log_path)
                )
                
        except Exception as e:
            logger.error(f"Failed to set up environment: {str(e)}", exc_info=True)
            # Clean up on failure
            if self.venv_dir.exists():
                shutil.rmtree(self.venv_dir)
            raise RuntimeError(f"Failed to set up script environment: {str(e)}")

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
        """Collect all lines from a stream."""
        lines = []
        while True:
            try:
                line = await stream.readline()
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
        
        # Ensure script file exists
        script_file = self.script_dir / "script.py"
        if not script_file.exists():
            logger.error(f"Script file not found: {script_file}")
            raise FileNotFoundError(f"Script file not found: {script_file}")
        
        # Create process
        cmd = [str(self.python_path), str(script_file)]
        logger.debug(f"Running command: {' '.join(cmd)}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.script_dir)
        )
        
        # Stream output
        assert process.stdout is not None
        assert process.stderr is not None

        try:
            # Process stdout and stderr concurrently
            stdout_task = asyncio.create_task(self._collect_stream(process.stdout))
            stderr_task = asyncio.create_task(self._collect_stream(process.stderr))
            
            # Wait for both streams to complete
            stdout_lines, stderr_lines = await asyncio.gather(stdout_task, stderr_task)
            
            # Yield stdout lines
            for line in stdout_lines:
                logger.debug(f"Yielding stdout line: {line!r}")
                yield line
            
            # Yield stderr lines
            for line in stderr_lines:
                logger.debug(f"Yielding stderr line: {line!r}")
                yield f"ERROR: {line}"
            
            # Wait for completion and check return code
            await process.wait()
            logger.debug(f"Process exited with return code {process.returncode}")
            if process.returncode != 0:
                error_msg = f"Error: Script exited with return code {process.returncode}\n"
                logger.error(f"Script execution failed with return code {process.returncode}")
                yield error_msg

        except Exception as e:
            error_msg = f"Error: {str(e)}\n"
            logger.exception("Error during script execution")
            yield error_msg

    def cleanup(self) -> None:
        """Clean up script environment."""
        if self.script_dir.exists():
            logger.info(f"Cleaning up script {self.script_id}")
            shutil.rmtree(self.script_dir)
            
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