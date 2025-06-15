#!/usr/bin/env python
"""
Memory-aware test runner for the admin-assistant project.

This script runs pytest with memory monitoring and provides detailed reports
on memory usage during test execution to help identify memory leaks.
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime

# Try to import psutil for memory monitoring
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("Warning: psutil not installed. Memory monitoring will be limited.")
    print("Install with: pip install psutil")


def get_memory_usage():
    """Get current memory usage in MB."""
    if HAS_PSUTIL:
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    return 0


def format_memory(mb):
    """Format memory size for display."""
    if mb > 1024:
        return f"{mb/1024:.2f} GB"
    return f"{mb:.2f} MB"


def run_tests_with_memory_monitoring(args):
    """Run tests with memory monitoring."""
    # Prepare pytest command
    pytest_args = [
        "pytest",
        "-v",
        "--no-header",
    ]
    
    # Add user-provided arguments
    if args.test_path:
        pytest_args.append(args.test_path)
    
    if args.markers:
        pytest_args.extend(["-m", args.markers])
        
    if args.keywords:
        pytest_args.extend(["-k", args.keywords])
    
    # Add memory monitoring options
    if args.gc_debug:
        os.environ["PYTHONMALLOC"] = "debug"
        os.environ["PYTHONTRACEMALLOC"] = "5"
    
    # Print command
    print(f"Running: {' '.join(pytest_args)}")
    print(f"Memory monitoring: {'Enabled' if HAS_PSUTIL else 'Limited'}")
    print("-" * 80)
    
    # Initialize memory tracking
    start_time = time.time()
    start_memory = get_memory_usage()
    peak_memory = start_memory
    memory_samples = []
    
    # Run the tests with real-time monitoring
    process = subprocess.Popen(
        pytest_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # Line buffered
    )
    
    # Monitor memory while tests are running
    try:
        for line in process.stdout:
            # Print test output
            print(line, end="")
            
            # Sample memory periodically
            if HAS_PSUTIL and (time.time() - start_time) % args.sample_interval < 0.1:
                current_memory = get_memory_usage()
                peak_memory = max(peak_memory, current_memory)
                memory_samples.append((time.time() - start_time, current_memory))
    except KeyboardInterrupt:
        print("\nTest run interrupted by user.")
        process.terminate()
        process.wait()
    
    # Wait for process to complete
    return_code = process.wait()
    
    # Final memory measurement
    end_memory = get_memory_usage()
    end_time = time.time()
    duration = end_time - start_time
    
    # Print memory report
    print("\n" + "=" * 80)
    print(f"MEMORY USAGE REPORT ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print("=" * 80)
    print(f"Test duration: {duration:.2f} seconds")
    print(f"Initial memory: {format_memory(start_memory)}")
    print(f"Final memory: {format_memory(end_memory)}")
    print(f"Peak memory: {format_memory(peak_memory)}")
    print(f"Memory change: {format_memory(end_memory - start_memory)} " +
          f"({((end_memory - start_memory) / start_memory * 100):.1f}%)")
    
    # Memory growth rate
    if duration > 0:
        growth_rate = (end_memory - start_memory) / duration
        print(f"Memory growth rate: {format_memory(growth_rate)}/second")
    
    # Memory leak warning
    if end_memory > start_memory * 1.5 and (end_memory - start_memory) > 100:
        print("\n⚠️ WARNING: Significant memory increase detected!")
        print("This may indicate a memory leak in the tests.")
        print("Consider running with --gc-debug for more detailed memory tracking.")
    
    # Return the pytest return code
    return return_code


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Memory-aware test runner")
    parser.add_argument("test_path", nargs="?", help="Path to test file or directory")
    parser.add_argument("-m", "--markers", help="Only run tests matching given mark expression")
    parser.add_argument("-k", "--keywords", help="Only run tests which match the given substring expression")
    parser.add_argument("--gc-debug", action="store_true", help="Enable Python memory debugging")
    parser.add_argument("--sample-interval", type=float, default=0.5, help="Memory sampling interval in seconds")
    
    args = parser.parse_args()
    
    return run_tests_with_memory_monitoring(args)


if __name__ == "__main__":
    sys.exit(main())