# TTS MCP Service Dockerfile
# Requires NVIDIA GPU for VibeVoice

FROM nvidia/cuda:12.1-runtime-ubuntu22.04

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Clone and install VibeVoice (when available)
# RUN git clone https://github.com/microsoft/VibeVoice.git /tmp/vibevoice && \
#     pip install /tmp/vibevoice && \
#     rm -rf /tmp/vibevoice

# Copy application code
COPY server.py .

# Create output directory
RUN mkdir -p /tmp/tts_output

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app /tmp/tts_output
USER appuser

# Environment variables
ENV TTS_DEVICE=cuda
ENV TTS_OUTPUT_DIR=/tmp/tts_output
ENV VIBEVOICE_MODEL_PATH=microsoft/VibeVoice-Realtime-0.5B

# Run as MCP server
CMD ["python", "server.py"]
