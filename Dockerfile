# Dockerfile for PawConnect Dialogflow Webhook
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy application code and setup files
COPY pawconnect_ai/ ./pawconnect_ai/
COPY setup.py .
COPY README.md .

# Install package with base dependencies only (no ML libraries)
RUN pip install --no-cache-dir -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run the webhook server
# Use shell form to allow environment variable substitution
CMD uvicorn pawconnect_ai.dialogflow_webhook:app --host 0.0.0.0 --port ${PORT}
