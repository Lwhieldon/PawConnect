# Dockerfile for PawConnect Dialogflow Webhook
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY pawconnect_ai/ ./pawconnect_ai/
COPY setup.py .
RUN pip install -e .

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run the webhook server
CMD ["uvicorn", "pawconnect_ai.dialogflow_webhook:app", "--host", "0.0.0.0", "--port", "8080"]
