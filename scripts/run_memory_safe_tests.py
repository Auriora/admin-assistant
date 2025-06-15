#!/usr/bin/env python3
"""
Memory-safe test runner that prevents memory accumulation during test execution.
"""
import os
import sys
import subprocess
import time
import gc
from pathlib import Path
from typing import List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

def setup_test_environment():
    """Setup environment for memory-safe testing."""
    os.environ['APP_ENV'] = 'testing'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['CORE_DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['LOG_LEVEL'] = 'WARNING'  # Reduce log noise
    os.environ['OTEL_SDK_DISABLED'] = 'true'  # Disable telemetry in tests
    
    # Python memory management settings
    os.environ['PYTHONHASHSEED'] = '0'  # Deterministic hashing
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'  # Don't create .pyc files


def run_tests_in_batches(test_paths: List[str], batch_size: int = 10) -> bool:
    """
    Run tests in small batches to prevent memory accumulation.
    
    Args:
        test_paths: List of test file paths
        batch_size: Number of tests to run in each batch
        
    Returns:
        True if all tests passed, False otherwise
    """
    setup_test_environment()
    
    total_tests = len(test_paths)
    failed_tests = []
    
    print(f"Running {total_tests} test files in batches of {batch_size}")
    
    for i in range(0, total_tests, batch_size):
        batch = test_paths[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_tests + batch_size - 1) // batch_size
        
        print(f"\n--- Batch {batch_num}/{total_batches} ---")
        print(f"Running: {', '.join([Path(p).name for p in batch])}")
        
        # Run batch
        cmd = [
            sys.executable, "-m", "pytest",
            "--tb=short",
            "--maxfail=1",  # Stop on first failure in batch
            "-v"
        ] + batch
        
        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per batch
            )
            
            if result.returncode != 0:
                print(f"❌ Batch {batch_num} failed")
                print("STDOUT:", result.stdout[-500:])  # Last 500 chars
                print("STDERR:", result.stderr[-500:])
                failed_tests.extend(batch)
            else:
                print(f"✅ Batch {batch_num} passed")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Batch {batch_num} timed out")
            failed_tests.extend(batch)
        except Exception as e:
            print(f"💥 Batch {batch_num} error: {e}")
            failed_tests.extend(batch)
        
        # Force cleanup between batches
        gc.collect()
        time.sleep(0.5)  # Brief pause to allow cleanup
    
    # Summary
    print(f"\n{'='*60}")
    if failed_tests:
        print(f"❌ {len(failed_tests)} test files failed:")
        for test in failed_tests:
            print(f"  - {test}")
        return False
    else:
        print("✅ All tests passed!")
        return True


def get_all_test_files() -> List[str]:
    """Get all test files in the project."""
    test_files = []
    
    for test_dir in ["tests/unit", "tests/integration"]:
        test_path = PROJECT_ROOT / test_dir
        if test_path.exists():
            for test_file in test_path.rglob("test_*.py"):
                test_files.append(str(test_file))
    
    return sorted(test_files)


def run_specific_tests(test_pattern: str) -> bool:
    """Run tests matching a specific pattern."""
    setup_test_environment()
    
    cmd = [
        sys.executable, "-m", "pytest",
        "--tb=short",
        "-v",
        test_pattern
    ]
    
    print(f"Running tests matching: {test_pattern}")
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running tests: {e}")
        return False


def run_memory_intensive_tests() -> bool:
    """Run only memory-intensive tests with special handling."""
    setup_test_environment()
    
    cmd = [
        sys.executable, "-m", "pytest",
        "-m", "memory_intensive",
        "--tb=short",
        "-v",
        "--maxfail=3"
    ]
    
    print("Running memory-intensive tests...")
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running memory-intensive tests: {e}")
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Memory-safe test runner")
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=10,
        help="Number of test files per batch"
    )
    parser.add_argument(
        "--pattern",
        help="Run tests matching this pattern"
    )
    parser.add_argument(
        "--memory-intensive",
        action="store_true",
        help="Run only memory-intensive tests"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests in batches"
    )
    
    args = parser.parse_args()
    
    if args.memory_intensive:
        success = run_memory_intensive_tests()
    elif args.pattern:
        success = run_specific_tests(args.pattern)
    elif args.all:
        test_files = get_all_test_files()
        success = run_tests_in_batches(test_files, args.batch_size)
    else:
        # Default: run async runner tests as example
        success = run_specific_tests("tests/unit/utilities/test_async_runner.py")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
