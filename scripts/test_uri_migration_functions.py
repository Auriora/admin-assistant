#!/usr/bin/env python3
"""
Test script to demonstrate the URI transformation functions for the database migration.

This script shows examples of how the URI transformation functions work and validates
their behavior with various input scenarios.
"""

import sys
import os
from typing import List, Tuple

# Add the migration module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src/core/migrations/versions'))

try:
    import importlib.util
    migration_path = os.path.join(os.path.dirname(__file__), '../src/core/migrations/versions/20250610_add_account_context_to_uris.py')
    spec = importlib.util.spec_from_file_location("migration_module", migration_path)
    migration_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration_module)
    
    add_account_context_to_uri = migration_module.add_account_context_to_uri
    remove_account_context_from_uri = migration_module.remove_account_context_from_uri
    get_account_context_for_user = migration_module.get_account_context_for_user
except Exception as e:
    print(f"Error loading migration module: {e}")
    sys.exit(1)


def test_uri_transformations():
    """Test and demonstrate URI transformation functions."""
    
    print("🔧 URI Transformation Functions Test")
    print("=" * 50)
    
    # Test cases: (original_uri, account_context, expected_result)
    test_cases = [
        # Basic transformations
        ("msgraph://calendars/primary", "user@example.com", "msgraph://user@example.com/calendars/primary"),
        ("local://calendars/personal", "user@example.com", "local://user@example.com/calendars/personal"),
        
        # Complex identifiers
        ("msgraph://calendars/Activity Archive", "user@example.com", "msgraph://user@example.com/calendars/Activity Archive"),
        
        # Legacy formats
        ("", "user@example.com", "msgraph://user@example.com/calendars/primary"),
        ("calendar", "user@example.com", "msgraph://user@example.com/calendars/primary"),
        ("primary", "user@example.com", "msgraph://user@example.com/calendars/primary"),
        
        # Malformed URIs
        ("calendars/primary", "user@example.com", "msgraph://user@example.com/calendars/calendars/primary"),
        ("my-calendar", "user@example.com", "msgraph://user@example.com/calendars/my-calendar"),
        
        # Already has account context
        ("msgraph://user@example.com/calendars/primary", "different@example.com", "msgraph://user@example.com/calendars/primary"),
        ("msgraph://123/calendars/primary", "user@example.com", "msgraph://123/calendars/primary"),
        
        # Special characters
        ("msgraph://calendars/primary", "user+tag@example.com", "msgraph://user+tag@example.com/calendars/primary"),
        ("msgraph://calendars/日本語", "用户@example.com", "msgraph://用户@example.com/calendars/日本語"),
        
        # Numeric accounts
        ("msgraph://calendars/primary", "123", "msgraph://123/calendars/primary"),
    ]
    
    print("\n📝 Testing add_account_context_to_uri function:")
    print("-" * 50)
    
    all_passed = True
    for i, (original_uri, account, expected) in enumerate(test_cases, 1):
        result = add_account_context_to_uri(original_uri, account)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result != expected:
            all_passed = False
        
        print(f"{i:2d}. {status}")
        print(f"    Input:    '{original_uri}' + '{account}'")
        print(f"    Expected: '{expected}'")
        print(f"    Got:      '{result}'")
        print()
    
    print("\n📝 Testing remove_account_context_from_uri function:")
    print("-" * 50)
    
    # Test removal cases
    removal_test_cases = [
        ("msgraph://user@example.com/calendars/primary", "msgraph://calendars/primary"),
        ("msgraph://123/calendars/primary", "msgraph://calendars/primary"),
        ("local://user@example.com/calendars/personal", "local://calendars/personal"),
        ("msgraph://user@example.com/calendars/Activity Archive", "msgraph://calendars/Activity Archive"),
        ("msgraph://calendars/primary", "msgraph://calendars/primary"),  # No change
        ("", ""),  # Empty URI
        ("msgraph://user+tag@example.com/calendars/primary", "msgraph://calendars/primary"),
        ("msgraph://用户@example.com/calendars/日本語", "msgraph://calendars/日本語"),
    ]
    
    for i, (input_uri, expected) in enumerate(removal_test_cases, 1):
        result = remove_account_context_from_uri(input_uri)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result != expected:
            all_passed = False
        
        print(f"{i:2d}. {status}")
        print(f"    Input:    '{input_uri}'")
        print(f"    Expected: '{expected}'")
        print(f"    Got:      '{result}'")
        print()
    
    print("\n📝 Testing roundtrip transformations:")
    print("-" * 50)
    
    # Test roundtrip cases
    roundtrip_test_cases = [
        ("msgraph://calendars/primary", "user@example.com"),
        ("local://calendars/personal", "user@example.com"),
        ("msgraph://calendars/Activity Archive", "user@example.com"),
        ("exchange://calendars/shared", "123"),
        ("msgraph://calendars/日本語", "用户@example.com"),
    ]
    
    for i, (original_uri, account) in enumerate(roundtrip_test_cases, 1):
        # Add context then remove it
        with_context = add_account_context_to_uri(original_uri, account)
        back_to_original = remove_account_context_from_uri(with_context)
        
        status = "✅ PASS" if back_to_original == original_uri else "❌ FAIL"
        
        if back_to_original != original_uri:
            all_passed = False
        
        print(f"{i:2d}. {status}")
        print(f"    Original:     '{original_uri}'")
        print(f"    With context: '{with_context}'")
        print(f"    Back to orig: '{back_to_original}'")
        print()
    
    print("\n📊 Summary:")
    print("-" * 50)
    if all_passed:
        print("✅ All tests passed! URI transformation functions are working correctly.")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return all_passed


def demonstrate_edge_cases():
    """Demonstrate handling of edge cases."""
    
    print("\n🔍 Edge Case Demonstrations:")
    print("=" * 50)
    
    edge_cases = [
        # Empty/None account context
        ("msgraph://calendars/primary", ""),
        ("msgraph://calendars/primary", None),
        
        # Very long URIs and accounts
        ("msgraph://calendars/" + "a" * 100, "user@example.com"),
        ("msgraph://calendars/primary", "a" * 50 + "@example.com"),
        
        # URIs with query parameters and fragments
        ("msgraph://calendars/primary?param=value", "user@example.com"),
        ("msgraph://calendars/primary#section", "user@example.com"),
        
        # Multiple path segments
        ("msgraph://calendars/folder1/folder2/calendar", "user@example.com"),
        
        # Special characters in account
        ("msgraph://calendars/primary", "first.last@example.com"),
        ("msgraph://calendars/primary", "user+tag@example.com"),
    ]
    
    for i, (uri, account) in enumerate(edge_cases, 1):
        print(f"{i:2d}. Testing edge case:")
        print(f"    URI: '{uri}'")
        print(f"    Account: '{account}'")
        
        try:
            result = add_account_context_to_uri(uri, account)
            print(f"    Result: '{result}'")
            
            # Test removal if context was added
            if account and result != uri:
                removed = remove_account_context_from_uri(result)
                print(f"    Removed: '{removed}'")
            
        except Exception as e:
            print(f"    Error: {e}")
        
        print()


if __name__ == "__main__":
    print("🧪 URI Migration Functions Test Suite")
    print("=" * 60)
    print("Testing the URI transformation functions used in the database migration.")
    print()
    
    # Run the main tests
    success = test_uri_transformations()
    
    # Demonstrate edge cases
    demonstrate_edge_cases()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests completed successfully!")
        print("The URI transformation functions are ready for use in the migration.")
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        sys.exit(1)
