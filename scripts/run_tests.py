#!/usr/bin/env python3
"""
Test runner script for the admin-assistant project.
Provides various test execution options with proper environment setup.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_test_environment():
    """Setup test environment variables."""
    os.environ['APP_ENV'] = 'testing'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['LOG_LEVEL'] = 'INFO'
    
    # Disable OpenTelemetry for tests unless explicitly enabled
    if 'ENABLE_OTEL_IN_TESTS' not in os.environ:
        os.environ['OTEL_SDK_DISABLED'] = 'true'

def run_unit_tests(verbose=False, coverage=False):
    """Run unit tests."""
    cmd = ['python', '-m', 'pytest', 'tests/unit/']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=core', '--cov=web', '--cov-report=term-missing'])
    
    cmd.extend(['-m', 'unit'])
    
    print("Running unit tests...")
    return subprocess.run(cmd, cwd=project_root).returncode

def run_integration_tests(verbose=False):
    """Run integration tests."""
    cmd = ['python', '-m', 'pytest', 'tests/integration/']
    
    if verbose:
        cmd.append('-v')
    
    cmd.extend(['-m', 'integration'])
    
    print("Running integration tests...")
    return subprocess.run(cmd, cwd=project_root).returncode

def run_all_tests(verbose=False, coverage=False):
    """Run all tests."""
    cmd = ['python', '-m', 'pytest', 'tests/']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=core', '--cov=web', '--cov-report=term-missing', '--cov-report=html'])
    
    print("Running all tests...")
    return subprocess.run(cmd, cwd=project_root).returncode

def run_specific_test(test_path, verbose=False):
    """Run a specific test file or test function."""
    cmd = ['python', '-m', 'pytest', test_path]
    
    if verbose:
        cmd.append('-v')
    
    print(f"Running specific test: {test_path}")
    return subprocess.run(cmd, cwd=project_root).returncode

def run_tests_by_marker(marker, verbose=False):
    """Run tests with a specific marker."""
    cmd = ['python', '-m', 'pytest', '-m', marker]
    
    if verbose:
        cmd.append('-v')
    
    print(f"Running tests with marker: {marker}")
    return subprocess.run(cmd, cwd=project_root).returncode

def run_archiving_tests(verbose=False, coverage=False):
    """Run tests specifically for archiving functionality."""
    test_files = [
        'tests/unit/services/test_calendar_archive_service_enhanced.py',
        'tests/unit/orchestrators/test_calendar_archive_orchestrator_enhanced.py',
        'tests/integration/test_archiving_flow_integration.py',
        'tests/unit/repositories/test_archive_configuration_repository.py',
        'tests/unit/repositories/test_action_log_repository.py'
    ]
    
    cmd = ['python', '-m', 'pytest'] + test_files
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=core.services.calendar_archive_service', 
                   '--cov=core.orchestrators.calendar_archive_orchestrator',
                   '--cov-report=term-missing'])
    
    print("Running archiving-specific tests...")
    return subprocess.run(cmd, cwd=project_root).returncode

def run_observability_tests(verbose=False):
    """Run tests that verify OpenTelemetry integration."""
    # Enable OpenTelemetry for these tests
    os.environ['ENABLE_OTEL_IN_TESTS'] = 'true'
    os.environ.pop('OTEL_SDK_DISABLED', None)
    
    cmd = ['python', '-m', 'pytest', '-k', 'otel or telemetry or tracing or metrics']
    
    if verbose:
        cmd.append('-v')
    
    print("Running observability tests...")
    return subprocess.run(cmd, cwd=project_root).returncode

def check_test_coverage():
    """Generate and display test coverage report."""
    cmd = ['python', '-m', 'pytest', '--cov=core', '--cov=web', 
           '--cov-report=html', '--cov-report=term-missing', 
           '--cov-fail-under=80', 'tests/']
    
    print("Generating coverage report...")
    result = subprocess.run(cmd, cwd=project_root)
    
    if result.returncode == 0:
        print("\nCoverage report generated successfully!")
        print("HTML report available at: htmlcov/index.html")
    else:
        print("\nCoverage check failed - coverage below 80%")
    
    return result.returncode

def lint_tests():
    """Run linting on test files."""
    try:
        # Check if flake8 is available
        subprocess.run(['flake8', '--version'], capture_output=True, check=True)
        
        cmd = ['flake8', 'tests/', '--max-line-length=120', '--ignore=E501,W503']
        print("Running linting on test files...")
        return subprocess.run(cmd, cwd=project_root).returncode
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("flake8 not available, skipping linting")
        return 0

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description='Run tests for admin-assistant project')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--archiving', action='store_true', help='Run archiving-specific tests')
    parser.add_argument('--observability', action='store_true', help='Run observability tests')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--lint', action='store_true', help='Run linting on test files')
    parser.add_argument('--marker', type=str, help='Run tests with specific marker')
    parser.add_argument('--test', type=str, help='Run specific test file or function')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--all', action='store_true', help='Run all tests (default)')
    
    args = parser.parse_args()
    
    # Setup test environment
    setup_test_environment()
    
    exit_code = 0
    
    try:
        if args.lint:
            exit_code = lint_tests()
        elif args.unit:
            exit_code = run_unit_tests(args.verbose, args.coverage)
        elif args.integration:
            exit_code = run_integration_tests(args.verbose)
        elif args.archiving:
            exit_code = run_archiving_tests(args.verbose, args.coverage)
        elif args.observability:
            exit_code = run_observability_tests(args.verbose)
        elif args.coverage:
            exit_code = check_test_coverage()
        elif args.marker:
            exit_code = run_tests_by_marker(args.marker, args.verbose)
        elif args.test:
            exit_code = run_specific_test(args.test, args.verbose)
        else:
            # Default: run all tests
            exit_code = run_all_tests(args.verbose, args.coverage)
    
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        exit_code = 130
    except Exception as e:
        print(f"\nError running tests: {e}")
        exit_code = 1
    
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
