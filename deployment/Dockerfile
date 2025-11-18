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

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11.3-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH \
    PORT=8080

# Create non-root user
RUN useradd -m -u 1000 pawconnect && \
    mkdir -p /app && \
    chown -R pawconnect:pawconnect /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --chown=pawconnect:pawconnect pawconnect_ai/ ./pawconnect_ai/
COPY --chown=pawconnect:pawconnect setup.py .
COPY --chown=pawconnect:pawconnect README.md .
COPY --chown=pawconnect:pawconnect LICENSE .

# Install the package
RUN pip install --no-cache-dir -e .

# Switch to non-root user
USER pawconnect

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run the application
CMD ["python", "-m", "uvicorn", "pawconnect_ai.api:app", "--host", "0.0.0.0", "--port", "8080"]
