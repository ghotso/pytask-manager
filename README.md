# PyTask Manager

A modern web application for managing, scheduling, and executing Python scripts with dependency management and real-time execution monitoring.

## Features

- 🐍 Python Script Management
  - Write and edit Python scripts directly in the browser
  - Syntax highlighting and code completion
  - Real-time script execution with live output
  - View execution history and logs

- 📦 Dependency Management
  - Specify Python package dependencies for each script
  - Automatic dependency installation and version management
  - Virtual environment isolation for each script

- ⏰ Task Scheduling
  - Schedule scripts using cron expressions
  - Enable/disable scheduled executions
  - View upcoming scheduled runs

- 🏷️ Organization
  - Tag scripts for better organization
  - Search and filter scripts by tags
  - Add descriptions and metadata

## Installation

### Prerequisites

- Docker
- Docker Compose
- Git

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/pytask-manager.git
   cd pytask-manager
   ```

2. Create necessary directories:
   ```bash
   mkdir -p data scripts logs
   ```

3. Create a docker-compose.yml file:
   ```yaml
   version: '3.8'
   
   services:
     pytask-manager:
       image: ghcr.io/yourusername/pytask-manager:latest
       ports:
         - "8000:8000"  # Backend + WebSocket + Static Files
       volumes:
         - ./data:/app/data        # For database and other persistent data
         - ./scripts:/app/scripts  # For user scripts
         - ./logs:/app/logs        # For execution logs
       environment:
         - DATABASE_URL=sqlite:///app/data/pytask.db
         - SCRIPTS_DIR=/app/scripts
         - LOGS_DIR=/app/logs
       restart: unless-stopped
   ```

4. Start the application:
   ```bash
   docker-compose up -d
   ```

5. Access the application:
   - Open your browser and navigate to `http://localhost:8000`
   - The API documentation is available at `http://localhost:8000/docs`

### Directory Structure

- `./data/`: Contains the SQLite database and other persistent data
  - `pytask.db`: The main SQLite database file
- `./scripts/`: Contains user Python scripts and their virtual environments
- `./logs/`: Contains execution logs and output files

## Development Setup

If you want to run the application in development mode:

1. Start the backend:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```

2. Start the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

The development server will be available at:
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

## Environment Variables

- `DATABASE_URL`: SQLite database URL (default: `sqlite:///app/data/pytask.db`)
- `SCRIPTS_DIR`: Directory for storing Python scripts (default: `/app/scripts`)
- `LOGS_DIR`: Directory for storing execution logs (default: `/app/logs`)

## API Documentation

The API documentation is automatically generated and available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

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