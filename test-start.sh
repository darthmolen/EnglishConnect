#!/bin/bash
# EnglishConnect Test Runner
#
# Usage:
#   ./test-start.sh              # Run all tests
#   ./test-start.sh unit         # Run unit tests only (no database)
#   ./test-start.sh integration  # Run integration tests (requires infra)
#   ./test-start.sh coverage     # Run all tests with coverage report

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

# Set up test virtual environment
setup_test_venv() {
    if [ ! -d ".venv-test" ]; then
        log_info "Creating test virtual environment..."
        python3 -m venv .venv-test
        .venv-test/bin/pip install --upgrade pip
        .venv-test/bin/pip install -r requirements-test.txt
    fi
}

# Run unit tests (no database required)
run_unit_tests() {
    log_info "Running unit tests..."
    .venv-test/bin/pytest tests/unit -v "$@"
}

# Run integration tests (requires database)
run_integration_tests() {
    log_info "Running integration tests..."
    log_info "Note: Make sure infrastructure is running (./start.sh infra)"
    .venv-test/bin/pytest tests/integration -v "$@"
}

# Run all tests with coverage
run_all_tests() {
    log_info "Running all tests..."
    .venv-test/bin/pytest tests -v "$@"
}

# Run all tests with coverage report
run_coverage() {
    log_info "Running all tests with coverage..."
    .venv-test/bin/pytest tests -v --cov=src/backend/app --cov=src/services --cov-report=term-missing --cov-report=html "$@"
    log_info "Coverage report generated at htmlcov/index.html"
}

# Main command handling
case "${1:-all}" in
    unit)
        setup_test_venv
        run_unit_tests "${@:2}"
        ;;
    integration)
        setup_test_venv
        run_integration_tests "${@:2}"
        ;;
    coverage)
        setup_test_venv
        run_coverage "${@:2}"
        ;;
    all|"")
        setup_test_venv
        run_all_tests "${@:2}"
        ;;
    *)
        echo "Usage: $0 [unit|integration|coverage|all]"
        echo ""
        echo "Commands:"
        echo "  unit        - Run unit tests only (no database needed)"
        echo "  integration - Run integration tests (requires ./start.sh infra)"
        echo "  coverage    - Run all tests with coverage report"
        echo "  all         - Run all tests (default)"
        exit 1
        ;;
esac
