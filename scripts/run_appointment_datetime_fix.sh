#!/bin/bash

# Fix Appointment Dates and Times Script
# This script fixes the incorrect dates and times in restored appointments
# by extracting actual data from audit logs.

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Fix appointment dates and times by extracting actual data from audit logs."
    echo ""
    echo "Options:"
    echo "  --user-id ID        User ID to fix appointments for (default: 1)"
    echo "  --dry-run          Show what would be fixed without making changes"
    echo "  --analysis-only    Only analyze audit logs and show available data"
    echo "  --no-export        Skip generating corrected export files"
    echo "  --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Fix appointments and generate exports"
    echo "  $0 --dry-run                 # See what would be fixed"
    echo "  $0 --analysis-only           # Analyze audit logs only"
    echo "  $0 --user-id 2 --no-export   # Fix for user 2, no exports"
}

# Parse command line arguments
USER_ID=1
DRY_RUN=false
ANALYSIS_ONLY=false
NO_EXPORT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --user-id)
            USER_ID="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --analysis-only)
            ANALYSIS_ONLY=true
            shift
            ;;
        --no-export)
            NO_EXPORT=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_error "Virtual environment not found. Please create one first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Check if the fix script exists
FIX_SCRIPT="scripts/fix_appointment_dates_and_times.py"
if [ ! -f "$FIX_SCRIPT" ]; then
    print_error "Fix script not found: $FIX_SCRIPT"
    exit 1
fi

# Build command arguments
ARGS="--user-id $USER_ID"

if [ "$DRY_RUN" = true ]; then
    ARGS="$ARGS --dry-run"
    print_warning "DRY RUN MODE - No changes will be made"
fi

if [ "$ANALYSIS_ONLY" = true ]; then
    ARGS="$ARGS --analysis-only"
    print_status "ANALYSIS ONLY MODE"
fi

if [ "$NO_EXPORT" = true ]; then
    ARGS="$ARGS --no-export"
fi

# Show what we're about to do
print_status "Starting appointment date/time fix..."
print_status "User ID: $USER_ID"
if [ "$DRY_RUN" = true ]; then
    print_status "Mode: Dry run (no changes)"
elif [ "$ANALYSIS_ONLY" = true ]; then
    print_status "Mode: Analysis only"
else
    print_status "Mode: Full fix with export generation"
fi

echo ""
print_status "Running fix script..."

# Run the Python script
if python3 "$FIX_SCRIPT" $ARGS; then
    if [ "$DRY_RUN" = false ] && [ "$ANALYSIS_ONLY" = false ]; then
        print_success "Appointment date/time fix completed successfully!"
        echo ""
        print_status "Next steps:"
        echo "1. Check the corrected export files in the exports/ directory"
        echo "2. Import the corrected CSV file into Microsoft 365"
        echo "3. Verify the appointments have the correct dates and times"
    else
        print_success "Analysis completed successfully!"
    fi
else
    print_error "Fix script failed. Check the output above for details."
    exit 1
fi
