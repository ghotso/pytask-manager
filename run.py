"""Development server runner."""
import os
import sys
from pathlib import Path

if __name__ == "__main__":
    # Get the directory containing this script
    root_dir = Path(__file__).parent.absolute()
    
    # Add the root directory to Python path
    sys.path.insert(0, str(root_dir))
    
    import uvicorn
    
    # Set environment variable for reloader process detection
    # The WatchFiles reloader sets this environment variable
    if os.environ.get("WATCHFILES_FORCE_POLLING") or os.environ.get("WATCHFILES_FORCE_NOTIFY"):
        os.environ["PYTASK_RELOADER_PROCESS"] = "1"
    
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload="--reload" in sys.argv,
        reload_excludes=["scripts/**/*", "scripts/*", "data/*"],
    ) 