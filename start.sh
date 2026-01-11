#!/bin/bash
# EnglishConnect Development Startup Script
#
# Starts infrastructure (Docker) and local services for development.
# Services run locally (not in Docker) for easier debugging in VS Code.
#
# Usage:
#   ./start.sh          # Start everything (infra + services)
#   ./start.sh infra    # Start only infrastructure (postgres, redis)
#   ./start.sh services # Start only local services (assumes infra is running)
#   ./start.sh ingest   # Run content ingestion
#   ./start.sh llm      # Start local LLM server (vLLM for Memori)
#
# See also:
#   ./stop.sh           # Stop everything
#   ./test-start.sh     # Run tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if .env exists, create from example if not
check_env() {
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            log_warn ".env not found, copying from .env.example"
            cp .env.example .env
            log_warn "Please edit .env with your API keys before running services"
        else
            log_error ".env.example not found!"
            exit 1
        fi
    fi
}

# Start infrastructure (PostgreSQL, Redis)
start_infra() {
    log_info "Starting infrastructure (PostgreSQL, Redis)..."
    docker compose up -d

    log_info "Waiting for PostgreSQL to be ready..."
    until docker compose exec -T postgres pg_isready -U englishconnect > /dev/null 2>&1; do
        sleep 1
    done
    log_info "PostgreSQL is ready!"

    log_info "Waiting for Redis to be ready..."
    until docker compose exec -T redis redis-cli ping > /dev/null 2>&1; do
        sleep 1
    done
    log_info "Redis is ready!"
}

# Create Python virtual environments if needed
setup_venvs() {
    # Backend venv
    if [ ! -d "src/backend/.venv" ]; then
        log_info "Creating backend virtual environment..."
        python3 -m venv src/backend/.venv
        src/backend/.venv/bin/pip install --upgrade pip
        src/backend/.venv/bin/pip install -r src/backend/requirements.txt
    fi

    # Content MCP venv
    if [ ! -d "src/services/content-mcp/.venv" ]; then
        log_info "Creating content-mcp virtual environment..."
        python3 -m venv src/services/content-mcp/.venv
        src/services/content-mcp/.venv/bin/pip install --upgrade pip
        src/services/content-mcp/.venv/bin/pip install -r src/services/content-mcp/requirements.txt
    fi

    # STT venv (needs CUDA) - DISABLED: Using Azure Realtime API instead
    # if [ ! -d "src/services/stt/.venv" ]; then
    #     log_info "Creating STT virtual environment..."
    #     python3 -m venv src/services/stt/.venv
    #     src/services/stt/.venv/bin/pip install --upgrade pip
    #     src/services/stt/.venv/bin/pip install -r src/services/stt/requirements.txt
    # fi

    # TTS MCP venv (needs CUDA) - DISABLED: Using Azure Realtime API instead
    # if [ ! -d "src/services/tts-mcp/.venv" ]; then
    #     log_info "Creating TTS MCP virtual environment..."
    #     python3 -m venv src/services/tts-mcp/.venv
    #     src/services/tts-mcp/.venv/bin/pip install --upgrade pip
    #     src/services/tts-mcp/.venv/bin/pip install -r src/services/tts-mcp/requirements.txt
    # fi
}

# Ingest content if database is empty
ingest_content() {
    log_info "Checking if content needs to be ingested..."

    # Check if lessons table has data
    LESSON_COUNT=$(docker compose exec -T postgres psql -U englishconnect -d englishconnect -tAc "SELECT COUNT(*) FROM lessons 2>/dev/null" 2>/dev/null || echo "0")

    if [ "$LESSON_COUNT" = "0" ] || [ -z "$LESSON_COUNT" ]; then
        log_info "Ingesting lesson content..."
        src/backend/.venv/bin/python src/tools/content_ingestion.py \
            --course ec1 \
            --lessons-dir content/refined/ec1/books/englishconnect_1_para_los_alumnos/lessons
    else
        log_info "Content already ingested ($LESSON_COUNT lessons found)"
    fi
}

# Start local services (for development)
start_services() {
    log_info "Starting local services..."

    # Create a directory for PIDs
    mkdir -p .pids

    # Start Content MCP Server
    log_info "Starting Content MCP Server..."
    cd src/services/content-mcp
    .venv/bin/python server.py &
    echo $! > ../../../.pids/content-mcp.pid
    cd ../../..

    # Start STT Service (uses local GPU for faster-whisper) - DISABLED: Using Azure Realtime API instead
    # log_info "Starting STT Service on port 8001..."
    # cd src/services/stt
    # export WHISPER_MODEL_SIZE=medium
    # export WHISPER_DEVICE=cuda
    # export WHISPER_COMPUTE_TYPE=float16
    # export LD_LIBRARY_PATH=/usr/local/cuda-12.8/lib64:$LD_LIBRARY_PATH
    # .venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 &
    # echo $! > ../../../.pids/stt.pid
    # cd ../../..

    log_info ""
    log_info "Services started!"
    log_info ""
    log_info "Running services:"
    log_info "  - PostgreSQL:      localhost:5432"
    log_info "  - Redis:           localhost:6379"
    log_info "  - Content MCP:     localhost:8003"
    log_info ""
    log_info "Voice handled by Azure Realtime API (USE_REALTIME_API=true)"
    log_info ""
    log_info "Start manually in VSCode debugger:"
    log_info "  - Backend API:     localhost:8000"
    log_info "  - LLM (vLLM):      localhost:8004 (run ./start.sh llm)"
    log_info ""
    log_info "Local STT/TTS disabled - uncomment in start.sh if needed"
    log_info ""
    log_info "To stop: ./stop.sh"
}

# Start local LLM server (vLLM for Memori)
start_llm() {
    log_info "Starting local LLM server (vLLM for Memori)..."

    if [ ! -d "src/services/llm-local/.venv" ]; then
        log_error "LLM venv not found. Run setup first or install manually."
        log_info "See src/services/llm-local/start.sh for setup instructions."
        exit 1
    fi

    cd src/services/llm-local
    ./start.sh "$@" &
    echo $! > ../../../.pids/llm.pid
    cd ../../..

    log_info "LLM server starting on port 8004..."
    log_info "Note: First startup downloads model (~28GB) and may take several minutes."
}

# Main command handling
case "${1:-all}" in
    infra)
        check_env
        start_infra
        ;;
    services)
        check_env
        setup_venvs
        start_services
        ;;
    ingest)
        check_env
        setup_venvs
        ingest_content
        ;;
    llm)
        check_env
        shift  # Remove 'llm' from args
        start_llm "$@"
        ;;
    all|"")
        check_env
        start_infra
        setup_venvs
        ingest_content
        start_services
        start_llm
        ;;
    *)
        echo "Usage: $0 [infra|services|ingest|llm|all]"
        echo ""
        echo "Commands:"
        echo "  infra     - Start only infrastructure (PostgreSQL, Redis)"
        echo "  services  - Start only local services (assumes infra is running)"
        echo "  ingest    - Run content ingestion"
        echo "  llm       - Start local LLM server (vLLM for Memori)"
        echo "  all       - Start everything (default)"
        echo ""
        echo "See also:"
        echo "  ./stop.sh       - Stop everything"
        echo "  ./test-start.sh - Run tests"
        exit 1
        ;;
esac
