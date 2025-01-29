# PyTask-Manager

A self-hosted web application for creating, managing, and executing Python scripts in isolated environments. Features include dependency management, scheduled execution, and real-time logging.

## Features

- 🐍 Create and edit Python scripts with syntax highlighting
- 📦 Per-script dependency management with isolated virtual environments
- ⏰ Schedule script execution using cron expressions
- 📊 Real-time execution logs and history
- 🔒 Secure script execution in isolated environments
- 🎨 Modern, responsive web interface
- 🔄 WebSocket-based real-time script execution feedback

## Technology Stack

### Frontend
- React with TypeScript
- Mantine UI components
- Monaco Editor for code editing
- WebSocket for real-time updates

### Backend
- FastAPI (Python)
- SQLAlchemy for database management
- APScheduler for task scheduling
- Virtual environments for script isolation

## Quick Start with Docker

```bash
# Pull the latest image
docker pull ghcr.io/yourusername/pytask-manager:latest

# Run the container
docker run -d \
  -p 8000:8000 \
  -v /path/to/scripts:/app/scripts \
  ghcr.io/yourusername/pytask-manager:latest
```

## Development Setup

### Prerequisites
- Python 3.12+
- Node.js 20+
- npm or yarn
- Git

### Backend Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload
```

### Frontend Setup
```bash
# Install dependencies
cd frontend
npm install

# Run development server
npm run dev
```

## Project Structure

```
.
├── backend/
│   ├── api/              # API routes and models
│   ├── database/         # Database models and configuration
│   ├── script_manager/   # Script execution and venv management
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/       # Page components
│   │   └── api/         # API client
│   └── package.json     # Node.js dependencies
├── scripts/             # Directory for user scripts
├── Dockerfile          # Multi-stage build for production
└── docker-compose.yml  # Development environment setup
```

## Configuration

### Environment Variables

- `SCRIPTS_DIR`: Directory for script storage (default: `/app/scripts`)
- `DATABASE_URL`: SQLite database location (default: `sqlite:///./data/app.db`)
- `FRONTEND_DIR`: Location of frontend static files (default: `/app/frontend/dist`)

## Deployment

### GitHub Actions

The project uses GitHub Actions for CI/CD. On every push to main or tag creation:
1. Builds the Docker image
2. Runs tests
3. Pushes to GitHub Container Registry (GHCR)

Required secrets:
- `GHCR_TOKEN`: GitHub token with package write permissions

### Manual Deployment

1. Build the image:
```bash
docker build -t pytask-manager .
```

2. Run the container:
```bash
docker run -d \
  -p 8000:8000 \
  -v /path/to/scripts:/app/scripts \
  pytask-manager
```

## Security Considerations

- Scripts run in isolated virtual environments
- Dependencies are installed from PyPI only
- No network access from script environments by default
- Regular security updates via Dependabot

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details 