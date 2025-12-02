# PawConnect AI - Production Dockerfile
# Multi-stage build for optimized image size

# Stage 1: Builder
FROM python:3.11.3-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file (excludes dev dependencies)
COPY requirements.txt .

# Install Python dependencies (use --no-cache-dir to keep image small)
# Note: BuildKit will cache this layer based on requirements.txt content
# Development dependencies (testing, linting) are optional and not installed here
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11.3-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Create non-root user
RUN useradd -m -u 1000 pawconnect && \
    mkdir -p /app && \
    chown -R pawconnect:pawconnect /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder to a location accessible by all users
COPY --from=builder --chown=pawconnect:pawconnect /root/.local /home/pawconnect/.local

# Add local bin to PATH for pawconnect user
ENV PATH=/home/pawconnect/.local/bin:$PATH

# Copy application code
COPY --chown=pawconnect:pawconnect pawconnect_ai/ ./pawconnect_ai/

# Switch to non-root user
USER pawconnect

# Add app directory to PYTHONPATH so imports work
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os, requests; requests.get(f'http://localhost:{os.environ.get(\"PORT\", \"8080\")}/health', timeout=5)"

# Run the application (Dialogflow webhook)
# Use shell form to allow environment variable substitution
CMD python -m uvicorn pawconnect_ai.dialogflow_webhook:app --host 0.0.0.0 --port ${PORT:-8080}
