#!/bin/bash
# vLLM Local LLM Server for Memori
#
# Starts vLLM with OpenAI-compatible API on port 8003
# Uses Qwen2.5-14B-Instruct for memory extraction
#
# Requirements:
# - CUDA 12.8+
# - RTX 5090 (32GB VRAM) or similar
#
# Usage:
#   ./start.sh              # Start with default settings
#   ./start.sh --quantized  # Use AWQ quantized model (faster, less VRAM)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[vLLM]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[vLLM]${NC} $1"; }

# Default settings
# Use local model path if available, otherwise download from HuggingFace
# Default to 7B model (fits in 32GB with room for KV cache)
LOCAL_MODEL_PATH_7B="$SCRIPT_DIR/models/Qwen2.5-7B-Instruct"
LOCAL_MODEL_PATH_14B="$SCRIPT_DIR/models/Qwen2.5-14B-Instruct"
if [ -d "$LOCAL_MODEL_PATH_7B" ]; then
    MODEL="${MEMORI_LLM_MODEL:-$LOCAL_MODEL_PATH_7B}"
elif [ -d "$LOCAL_MODEL_PATH_14B" ]; then
    MODEL="${MEMORI_LLM_MODEL:-$LOCAL_MODEL_PATH_14B}"
else
    MODEL="${MEMORI_LLM_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
fi
PORT="${MEMORI_LLM_PORT:-8004}"
MAX_MODEL_LEN="${MEMORI_LLM_MAX_LEN:-32768}"
GPU_MEMORY_UTILIZATION="${MEMORI_LLM_GPU_MEM:-0.9}"

# Check for quantized flag
if [[ "$1" == "--quantized" ]]; then
    MODEL="Qwen/Qwen2.5-14B-Instruct-AWQ"
    log_info "Using quantized model: $MODEL"
fi

# Set CUDA 12.8 paths
export PATH=/usr/local/cuda-12.8/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.8/lib64:$LD_LIBRARY_PATH

# Activate venv
source .venv/bin/activate

log_info "Starting vLLM server..."
log_info "  Model: $MODEL"
log_info "  Port: $PORT"
log_info "  Max context: $MAX_MODEL_LEN tokens"
log_info "  GPU memory utilization: $GPU_MEMORY_UTILIZATION"

# For Blackwell (SM120), may need FA2 fallback
# Uncomment if you see Flash Attention errors:
# export VLLM_FLASH_ATTN_VERSION=2

exec python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --max-model-len "$MAX_MODEL_LEN" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    --trust-remote-code
