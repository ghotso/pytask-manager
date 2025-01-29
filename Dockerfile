# Build frontend
FROM node:20-slim as frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Build backend and final image
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/data /app/scripts /app/logs \
    && chmod 755 /app/data /app/scripts /app/logs

# Copy backend code
COPY backend/ .

# Copy frontend build
COPY --from=frontend-builder /app/dist /app/static

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite:///app/data/pytask.db
ENV SCRIPTS_DIR=/app/scripts
ENV LOGS_DIR=/app/logs

# Expose only the backend port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 