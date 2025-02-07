# PyTask Manager

A modern web application for managing, scheduling, and executing Python scripts with dependency management and real-time execution monitoring.

## Features

- 🐍 Python Script Management
  - Write and edit Python scripts directly in the browser with Monaco Editor
  - Advanced syntax highlighting and code completion
  - Real-time script execution with live output streaming
  - Comprehensive execution history and detailed logs
  - Script state management (active/inactive)

- 📦 Dependency Management
  - Specify Python package dependencies for each script
  - Real-time dependency installation progress monitoring
  - Automatic virtual environment creation and management
  - Version specification support (e.g., requests>=2.25.1)
  - Dependency status tracking and updates

- ⏰ Task Scheduling
  - Schedule scripts using cron expressions with human-readable descriptions
  - Flexible scheduling management
  - View upcoming scheduled runs
  - Timezone-aware scheduling

- 🏷️ Organization
  - Tag-based script organization
  - Advanced search and filtering capabilities
  - Rich metadata support
  - Clean and modern UI

- 🔒 Security & Isolation
  - Isolated script execution environments
  - Secure dependency management
  - Resource usage controls
  - Error handling and logging

## Installation

### Prerequisites

- Docker

### Quick Start with Docker

1. Create necessary directories:
   ```bash
   mkdir -p data scripts logs
   ```

2. Create a docker-compose.yml file:
   ```yaml
   version: '3.8'
   
   services:
     pytask-manager:
       image: ghcr.io/ghotso/pytask-manager:latest
       container_name: PyTask-Manager
       ports:
         - "8479:8000"  # Adjust the port as needed
       volumes:
         - ./data:/app/data        # For database and other persistent data
         - ./scripts:/app/scripts  # For user scripts
         - ./logs:/app/logs        # For execution logs
       environment:
         - TZ=Europe/Vienna        # Adjust timezone as needed
       restart: unless-stopped
   ```

3. Start the application:
   ```bash
   docker-compose up -d
   ```

4. Access the application:
   - Open your browser and navigate to `http://localhost:8479`

### Alternative: Direct Docker Run

You can also run the container directly without docker-compose:

```bash
docker run -d \
  --name='PyTask-Manager' \
  -p '8479:8000/tcp' \
  -v '/path/to/data':'/app/data':'rw' \
  -v '/path/to/scripts':'/app/scripts':'rw' \
  -v '/path/to/logs':'/app/logs':'rw' \
  -e TZ="Europe/Vienna" \
  'ghcr.io/ghotso/pytask-manager'
```

### Directory Structure

- `./data/`: Contains the SQLite database and other persistent data
  - `pytask.db`: The main SQLite database file
- `./scripts/`: Contains user Python scripts and their virtual environments
- `./logs/`: Contains execution logs and output files

### Docker Image Tags

The Docker image is available on GitHub Container Registry (GHCR) with the following tags:

- `latest`: Always points to the latest stable version
- `vX.Y.Z`: Specific version releases (e.g., v1.0.0)

You can use a specific version by updating the image tag in your docker-compose.yml:

```yaml
services:
  pytask-manager:
    image: ghcr.io/ghotso/pytask-manager:v1.0.0  # Use specific version
    # or
    image: ghcr.io/ghotso/pytask-manager:latest  # Always use latest version
```

## Development Setup

### Backend Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the development server:
   ```bash
   python run.py --reload
   ```

### Frontend Setup

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

The development servers will be available at:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

## Environment Variables

All environment variables are optional and have sensible defaults:

- `PYTASK_DATABASE_URL`: SQLite database URL
  - Default: `sqlite+aiosqlite:///data/data.db`
  - Docker default: `sqlite:///app/data/pytask.db`

- `PYTASK_SCRIPTS_DIR`: Directory for storing Python scripts
  - Default: `./scripts`
  - Docker default: `/app/scripts`

- `PYTASK_LOGS_DIR`: Directory for storing execution logs
  - Default: `./logs`
  - Docker default: `/app/logs`

- `PYTASK_DEBUG`: Enable debug mode
  - Default: `true` (set to `false` in production)

- `PYTASK_LOG_LEVEL`: Logging level
  - Default: `INFO`
  - Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

- `PYTASK_MAX_EXECUTION_TIME`: Maximum script execution time in seconds
  - Default: `300` (5 minutes)

- `TZ`: Container timezone (important for correct scheduling)
  - Example: `TZ=Europe/Vienna`
  - Affects both backend scheduling and frontend timestamp display

## New Features & Improvements

### Real-time Dependency Installation

- Live progress monitoring during dependency installation
- Clear status updates and error reporting
- Automatic virtual environment management
- Version compatibility checking

### Enhanced Script Execution

- Improved real-time log streaming
- Better error handling and reporting
- Execution state management
- Resource usage monitoring

### Modern UI/UX

- Clean and responsive design using Mantine UI
- Dark mode support
- Improved code editor with Monaco
- Real-time updates and notifications

### Improved Security

- Script isolation using virtual environments
- Secure dependency management
- Resource usage limits
- Error handling and logging

## API Documentation

The API documentation is automatically generated and available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker Image Tags

The Docker image is available on GitHub Container Registry (GHCR) with the following tags:

- `latest`: Always points to the latest stable version (from main branch)
- `vX.Y.Z`: Specific version releases (e.g., v1.0.0)
- `vX.Y`: Minor version releases (e.g., v1.0)
- `vX`: Major version releases (e.g., v1)

You can use a specific version by updating the image tag in your docker-compose.yml:

```yaml
services:
  pytask-manager:
    image: ghcr.io/ghotso/pytask-manager:v1.0.0  # Use specific version
    # or
    image: ghcr.io/ghotso/pytask-manager:latest  # Always use latest version
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Security

- All script executions are isolated in their own virtual environments
- Dependencies are installed from PyPI using pip
- File system access is restricted to the script's directory
- API endpoints require authentication (if enabled)

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using port 8000
   sudo lsof -i :8000
   # Stop the existing process or change the port in docker-compose.yml
   ```

2. **Permission Issues**
   ```bash
   # Ensure correct permissions on directories
   chmod 755 data scripts logs
   ```

3. **Container Won't Start**
   ```bash
   # Check container logs
   docker-compose logs -f
   ```

### Getting Help

- Open an issue on GitHub
- Check the API documentation for endpoint details
- Review the logs in the `./logs` directory

## Acknowledgments

- Built with FastAPI and React
- Uses Mantine UI components
- Monaco Editor for code editing
- SQLAlchemy for database management 