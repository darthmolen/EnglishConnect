#!/bin/bash
# Start STT service with optimal settings

cd "$(dirname "$0")"
source .venv/bin/activate

# Load .env if exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Ensure CUDA libraries are available
export LD_LIBRARY_PATH=/usr/local/cuda-12.8/lib64:$LD_LIBRARY_PATH

echo "Starting STT service..."
echo "  Model: ${WHISPER_MODEL_SIZE:-medium}"
echo "  Device: ${WHISPER_DEVICE:-cuda}"
echo "  Compute: ${WHISPER_COMPUTE_TYPE:-float16}"

uvicorn server:app --host 0.0.0.0 --port 8001
