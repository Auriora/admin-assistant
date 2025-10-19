# Automatically ignore duplicate test file that conflicts by basename
collect_ignore = [
    "test_audit_sanitizer_extra.py",
]

# Mark all tests in this package as unit tests
import pytest
pytestmark = pytest.mark.unit
