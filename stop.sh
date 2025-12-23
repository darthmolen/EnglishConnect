#!/bin/bash
# EnglishConnect Stop Script
#
# Stops all running services and infrastructure.
#
# Usage:
#   ./stop.sh           # Stop everything
#   ./stop.sh services  # Stop only local services (keep infra running)
#   ./stop.sh infra     # Stop only infrastructure

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

# Stop local services
stop_services() {
    log_info "Stopping local services..."

    if [ -d ".pids" ]; then
        for pidfile in .pids/*.pid; do
            if [ -f "$pidfile" ]; then
                pid=$(cat "$pidfile")
                service_name=$(basename "$pidfile" .pid)
                if kill -0 "$pid" 2>/dev/null; then
                    log_info "Stopping $service_name (PID: $pid)..."
                    kill "$pid" 2>/dev/null || true
                fi
                rm "$pidfile"
            fi
        done
        rmdir .pids 2>/dev/null || true
    fi

    # Also kill any remaining processes for this project
    pkill -f "src/services/content-mcp/server.py" 2>/dev/null || true
    pkill -f "src/services/stt/server" 2>/dev/null || true

    log_info "Local services stopped."
}

# Stop infrastructure (PostgreSQL, Redis)
stop_infra() {
    log_info "Stopping infrastructure (PostgreSQL, Redis)..."
    docker compose down
    log_info "Infrastructure stopped."
}

# Main command handling
case "${1:-all}" in
    services)
        stop_services
        ;;
    infra)
        stop_infra
        ;;
    all|"")
        stop_services
        stop_infra
        ;;
    *)
        echo "Usage: $0 [services|infra|all]"
        echo ""
        echo "Commands:"
        echo "  services - Stop only local services (keep infra running)"
        echo "  infra    - Stop only infrastructure (PostgreSQL, Redis)"
        echo "  all      - Stop everything (default)"
        exit 1
        ;;
esac
