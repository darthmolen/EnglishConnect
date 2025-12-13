FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Environment variables
ENV DATABASE_URL=postgresql://englishconnect:devpassword@postgres:5432/englishconnect

# Run as MCP server
CMD ["python", "server.py"]
