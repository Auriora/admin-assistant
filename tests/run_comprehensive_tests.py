#!/usr/bin/env python3
"""
Comprehensive test runner for all new functionality.

This script runs all tests related to the new URI parsing, timesheet archiving,
account validation, and migration functionality.
"""
import sys
import subprocess
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and return the result"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print('='*60)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False


def main():
    """Run comprehensive tests for all new functionality"""
    print("🚀 Starting Comprehensive Test Suite for New Functionality")
    print("Testing URI parsing, timesheet archiving, account validation, and migrations")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Test categories and their commands
    test_categories = [
        {
            "name": "URI Utility Tests",
            "command": "python -m pytest tests/unit/utilities/test_uri_utility.py -v",
            "description": "URI parsing and construction with account context"
        },
        {
            "name": "Calendar Resolver Account Validation Tests",
            "command": "python -m pytest tests/unit/utilities/test_calendar_resolver_account_validation.py -v",
            "description": "Account validation in CalendarResolver"
        },
        {
            "name": "Timesheet Archive Service Tests",
            "command": "python -m pytest tests/unit/services/test_timesheet_archive_service.py -v",
            "description": "Timesheet filtering and overlap resolution"
        },
        {
            "name": "Calendar Archive Orchestrator Tests",
            "command": "python -m pytest tests/unit/orchestrators/test_calendar_archive_orchestrator.py::TestCalendarArchiveOrchestratorTimesheet -v",
            "description": "Timesheet archive orchestration"
        },
        {
            "name": "CLI Timesheet Commands Tests",
            "command": "python -m pytest tests/unit/cli/test_timesheet_commands.py -v",
            "description": "CLI timesheet command functionality"
        },
        {
            "name": "Migration Script Tests",
            "command": "python -m pytest tests/unit/migrations/test_account_context_migration.py -v",
            "description": "Database migration functionality"
        },
        {
            "name": "Timesheet Workflow Integration Tests",
            "command": "python -m pytest tests/integration/test_timesheet_workflow_integration.py -v",
            "description": "End-to-end timesheet workflow"
        },
    ]
    
    # Run individual test categories
    results = []
    for category in test_categories:
        success = run_command(category["command"], category["name"])
        results.append((category["name"], success))
    
    # Run comprehensive integration tests
    print(f"\n{'='*60}")
    print("Running Comprehensive Integration Tests")
    print('='*60)
    
    integration_success = run_command(
        "python -m pytest tests/integration/ -k timesheet -v",
        "All Timesheet Integration Tests"
    )
    results.append(("Integration Tests", integration_success))
    
    # Run performance tests
    print(f"\n{'='*60}")
    print("Running Performance Tests")
    print('='*60)
    
    performance_success = run_command(
        "python -m pytest tests/integration/test_timesheet_workflow_integration.py::TestTimesheetWorkflowIntegration::test_performance_integration -v",
        "Performance Tests"
    )
    results.append(("Performance Tests", performance_success))
    
    # Run backward compatibility tests
    print(f"\n{'='*60}")
    print("Running Backward Compatibility Tests")
    print('='*60)
    
    compatibility_success = run_command(
        "python -m pytest tests/unit/utilities/test_uri_utility.py::TestBackwardCompatibility -v",
        "Backward Compatibility Tests"
    )
    results.append(("Backward Compatibility", compatibility_success))
    
    # Summary
    print(f"\n{'='*80}")
    print("COMPREHENSIVE TEST RESULTS SUMMARY")
    print('='*80)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    failed_tests = total_tests - passed_tests
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<40} {status}")
    
    print(f"\n{'='*80}")
    print(f"TOTAL: {total_tests} test categories")
    print(f"PASSED: {passed_tests}")
    print(f"FAILED: {failed_tests}")
    
    if failed_tests == 0:
        print("🎉 ALL TESTS PASSED! 🎉")
        print("\nNew functionality is ready for deployment:")
        print("✅ URI parsing with account context")
        print("✅ Account validation in CalendarResolver")
        print("✅ Timesheet filtering and overlap resolution")
        print("✅ Archive simplification (allowing overlaps)")
        print("✅ CLI timesheet commands")
        print("✅ Migration script functionality")
        print("✅ End-to-end integration")
        return 0
    else:
        print(f"❌ {failed_tests} TEST CATEGORIES FAILED")
        print("\nPlease review the failed tests above and fix any issues.")
        return 1


def run_specific_test_category(category_name):
    """Run a specific test category"""
    test_categories = {
        "uri": "python -m pytest tests/unit/utilities/test_uri_utility.py -v",
        "resolver": "python -m pytest tests/unit/utilities/test_calendar_resolver_account_validation.py -v",
        "timesheet": "python -m pytest tests/unit/services/test_timesheet_archive_service.py -v",
        "orchestrator": "python -m pytest tests/unit/orchestrators/test_calendar_archive_orchestrator.py::TestCalendarArchiveOrchestratorTimesheet -v",
        "cli": "python -m pytest tests/unit/cli/test_timesheet_commands.py -v",
        "migration": "python -m pytest tests/unit/migrations/test_account_context_migration.py -v",
        "integration": "python -m pytest tests/integration/test_timesheet_workflow_integration.py -v",
    }
    
    if category_name not in test_categories:
        print(f"Unknown test category: {category_name}")
        print(f"Available categories: {', '.join(test_categories.keys())}")
        return 1
    
    command = test_categories[category_name]
    success = run_command(command, f"{category_name.title()} Tests")
    return 0 if success else 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test category
        category = sys.argv[1].lower()
        exit_code = run_specific_test_category(category)
    else:
        # Run all tests
        exit_code = main()
    
    sys.exit(exit_code)
