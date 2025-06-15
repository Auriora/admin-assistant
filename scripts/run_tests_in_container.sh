#!/bin/bash
# Container-based test execution with memory limits for diagnosing SIGKILL issues
# 
# This script builds a test container using the existing Dockerfile and runs tests
# with specified memory limits to help diagnose memory-related test failures.
#
# Usage:
#   ./scripts/run_tests_in_container.sh [MEMORY_LIMIT] [TEST_ARGS...]
#
# Examples:
#   ./scripts/run_tests_in_container.sh 2g
#   ./scripts/run_tests_in_container.sh 1g tests/unit/
#   ./scripts/run_tests_in_container.sh 512m --verbose tests/integration/

set -e  # Exit on any error

# Configuration
DEFAULT_MEMORY_LIMIT="2g"
DOCKERFILE_PATH=".devcontainer/Dockerfile"
IMAGE_NAME="admin-assistant-test"
CONTAINER_NAME="admin-assistant-test-run"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

show_usage() {
    cat << EOF
Container Test Runner with Memory Limits

Usage: $0 [MEMORY_LIMIT] [TEST_ARGS...]

Arguments:
  MEMORY_LIMIT    Memory limit for container (default: ${DEFAULT_MEMORY_LIMIT})
                  Examples: 512m, 1g, 2g, 1024m
  TEST_ARGS       Additional arguments to pass to pytest

Examples:
  $0                           # Run all tests with ${DEFAULT_MEMORY_LIMIT} memory limit
  $0 1g                        # Run all tests with 1GB memory limit
  $0 512m tests/unit/          # Run unit tests with 512MB memory limit
  $0 2g --verbose              # Run all tests with 2GB limit and verbose output
  $0 1g tests/unit/ --maxfail=1  # Run unit tests with early exit on failure

Environment Variables:
  DOCKER_BUILDKIT=1           Enable Docker BuildKit for faster builds
  NO_CACHE=1                  Force rebuild without cache

EOF
}

# Check if help was requested first
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_usage
    exit 0
fi

# Parse arguments
MEMORY_LIMIT="${1:-$DEFAULT_MEMORY_LIMIT}"
shift 2>/dev/null || true  # Remove first argument if it exists
TEST_ARGS="$@"

# Validate memory limit format
if ! [[ "$MEMORY_LIMIT" =~ ^[0-9]+[kmgKMG]?$ ]]; then
    log_error "Invalid memory limit format: $MEMORY_LIMIT"
    log_info "Valid formats: 512m, 1g, 2g, 1024m, etc."
    exit 1
fi

# Check prerequisites
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

if [ ! -f "$DOCKERFILE_PATH" ]; then
    log_error "Dockerfile not found at $DOCKERFILE_PATH"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    log_error "Docker daemon is not running"
    exit 1
fi

log_info "Container Test Runner Configuration"
echo "  Memory Limit: $MEMORY_LIMIT"
echo "  Test Arguments: ${TEST_ARGS:-'(none)'}"
echo "  Dockerfile: $DOCKERFILE_PATH"
echo "  Image Name: $IMAGE_NAME"
echo ""

# Clean up any existing container
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_info "Removing existing container: $CONTAINER_NAME"
    docker rm -f "$CONTAINER_NAME" &> /dev/null || true
fi

# Build the test image
log_info "Building test container image..."
BUILD_ARGS=""
if [ "${NO_CACHE:-0}" = "1" ]; then
    BUILD_ARGS="--no-cache"
    log_warning "Building without cache (NO_CACHE=1)"
fi

if ! docker build $BUILD_ARGS -t "$IMAGE_NAME" -f "$DOCKERFILE_PATH" .; then
    log_error "Failed to build Docker image"
    exit 1
fi

log_success "Container image built successfully"

# Prepare test command
TEST_CMD="cd /workspace && pip install -e .[dev] && python scripts/dev_cli.py test memory-profile $TEST_ARGS"

log_info "Running tests in container with memory limit: $MEMORY_LIMIT"
echo "Test command: $TEST_CMD"
echo ""

# Run the container with memory limits
DOCKER_RUN_ARGS=(
    --rm
    --name "$CONTAINER_NAME"
    --memory "$MEMORY_LIMIT"
    --memory-swap "$MEMORY_LIMIT"  # Disable swap to enforce hard memory limit
    --oom-kill-disable=false       # Allow OOM killer (default behavior)
    -v "$(pwd):/workspace"
    -w /workspace
    "$IMAGE_NAME"
    bash -c "$TEST_CMD"
)

# Execute the container
START_TIME=$(date +%s)
EXIT_CODE=0

if ! docker run "${DOCKER_RUN_ARGS[@]}"; then
    EXIT_CODE=$?
fi

END_TIME=$(date +%s)
EXECUTION_TIME=$((END_TIME - START_TIME))

echo ""
log_info "Container execution completed"
echo "  Exit Code: $EXIT_CODE"
echo "  Execution Time: ${EXECUTION_TIME}s"
echo "  Memory Limit: $MEMORY_LIMIT"

# Analyze results
case $EXIT_CODE in
    0)
        log_success "Tests completed successfully within memory limit"
        ;;
    137)
        log_error "Container killed with SIGKILL (exit code 137)"
        echo ""
        echo "This typically indicates one of the following:"
        echo "  • Process exceeded the memory limit ($MEMORY_LIMIT)"
        echo "  • Out-of-memory (OOM) killer terminated the process"
        echo "  • System resource exhaustion"
        echo ""
        echo "Troubleshooting suggestions:"
        echo "  • Try increasing the memory limit (e.g., $(echo $MEMORY_LIMIT | sed 's/[0-9]*/&2/'))"
        echo "  • Run tests in smaller batches"
        echo "  • Use 'docker stats' in another terminal to monitor resource usage"
        echo "  • Check Docker daemon logs: 'docker logs $CONTAINER_NAME'"
        ;;
    130)
        log_warning "Tests interrupted by user (Ctrl+C)"
        ;;
    *)
        log_error "Tests failed with exit code: $EXIT_CODE"
        if [ $EXIT_CODE -gt 128 ]; then
            SIGNAL=$((EXIT_CODE - 128))
            log_warning "Process terminated by signal: $SIGNAL"
        fi
        ;;
esac

# Cleanup
log_info "Cleaning up..."
docker rmi "$IMAGE_NAME" &> /dev/null || log_warning "Could not remove image $IMAGE_NAME"

exit $EXIT_CODE
