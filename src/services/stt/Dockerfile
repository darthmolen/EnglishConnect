# STT Service Dockerfile
# Requires NVIDIA GPU for optimal performance

FROM nvidia/cuda:12.1-runtime-ubuntu22.04

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Environment variables
ENV WHISPER_MODEL_SIZE=large-v3
ENV WHISPER_DEVICE=cuda
ENV WHISPER_COMPUTE_TYPE=float16

# Expose port
EXPOSE 8001

# Run the application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
