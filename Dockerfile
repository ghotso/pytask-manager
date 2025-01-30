# Build frontend
FROM node:20-slim as frontend-builder
WORKDIR /app/frontend

# Copy package files for better layer caching
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies with clean install
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build

# Build backend and final image
FROM python:3.11-slim

# Add metadata labels
LABEL org.opencontainers.image.title="PyTask Manager"
LABEL org.opencontainers.image.description="A modern web application for managing, scheduling, and executing Python scripts"
LABEL org.opencontainers.image.source="https://github.com/yourusername/pytask-manager"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with nobody's UID (99) and use existing users group (100)
RUN useradd -u 99 -g 100 -m -r -s /bin/bash pytask

# Create necessary directories with proper ownership and permissions
RUN mkdir -p /app/data /app/scripts /app/logs && \
    chown -R pytask:users /app && \
    chmod -R 755 /app && \
    chmod 777 /app/data /app/scripts /app/logs

# Configure logging to stdout/stderr
RUN ln -sf /dev/stdout /app/logs/app.log && \
    ln -sf /dev/stderr /app/logs/error.log

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY run.py ./

# Copy frontend build
COPY --from=frontend-builder /app/frontend/dist ./static

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PYTASK_DATABASE_URL=sqlite+aiosqlite:////app/data/data.db
ENV PYTASK_SCRIPTS_DIR=/app/scripts
ENV PYTASK_LOGS_DIR=/app/logs
ENV PYTASK_DEBUG=true
ENV PYTASK_LOG_LEVEL=INFO

# Expose port
EXPOSE 8000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Final permission check and fix
RUN mkdir -p /app/data && \
    touch /app/data/data.db && \
    chown -R pytask:users /app && \
    chmod -R 755 /app && \
    chmod 777 /app/data /app/scripts /app/logs && \
    chmod 666 /app/data/data.db && \
    ls -la /app/data && \
    ls -la /app/scripts && \
    ls -la /app/logs && \
    id pytask

# Switch to non-root user
USER pytask

# Run the application
CMD ["python", "run.py"] 