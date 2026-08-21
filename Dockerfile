# Multi-stage build for Clipper
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: Python backend with FFmpeg
FROM python:3.11-slim AS backend

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY api/pyproject.toml api/ruff.toml ./
RUN pip install --no-cache-dir -e ".[ai]"

# Copy backend source
COPY api/app ./app

# Copy built frontend
COPY --from=frontend-builder /app/web/dist ./web/dist

# Create non-root user
RUN useradd -m -u 1000 clipper && \
    mkdir -p /app/storage /app/web/dist && \
    chown -R clipper:clipper /app
USER clipper

# Environment
ENV PYTHONPATH=/app
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV CORS_ORIGINS=["http://localhost:5173","http://localhost:8000"]

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health', timeout=3).raise_for_status()" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]