"""
Tests for the enhanced async runner utility.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, patch

from core.utilities.async_runner import AsyncRunner, run_async, run_async_safe, get_async_runner


class TestAsyncRunner:
    """Test cases for the AsyncRunner class."""
    
    def test_basic_async_operation(self):
        """Test basic async operation execution."""
        async def simple_operation():
            await asyncio.sleep(0.1)
            return "success"
        
        result = run_async(simple_operation())
        assert result == "success"
    
    def test_async_operation_with_return_value(self):
        """Test async operation that returns a value."""
        async def operation_with_value():
            return {"status": "completed", "value": 42}
        
        result = run_async(operation_with_value())
        assert result == {"status": "completed", "value": 42}
    
    def test_timeout_handling(self):
        """Test timeout handling."""
        async def slow_operation():
            await asyncio.sleep(2.0)
            return "too_slow"
        
        with pytest.raises(asyncio.TimeoutError):
            run_async(slow_operation(), timeout=0.5)
    
    def test_exception_propagation(self):
        """Test that exceptions are properly propagated."""
        async def failing_operation():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            run_async(failing_operation())
    
    def test_safe_async_operation_success(self):
        """Test safe async operation with successful execution."""
        async def successful_operation():
            return "success"
        
        result = run_async_safe(successful_operation())
        assert result == "success"
    
    def test_safe_async_operation_failure(self):
        """Test safe async operation with failure returns default."""
        async def failing_operation():
            raise ValueError("Test error")
        
        result = run_async_safe(failing_operation(), default="default_value")
        assert result == "default_value"
    
    def test_safe_async_operation_failure_no_default(self):
        """Test safe async operation with failure and no default."""
        async def failing_operation():
            raise ValueError("Test error")
        
        result = run_async_safe(failing_operation())
        assert result is None
    
    def test_concurrent_operations(self):
        """Test multiple concurrent operations."""
        async def concurrent_operation(value):
            await asyncio.sleep(0.1)
            return value * 2
        
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(run_async, concurrent_operation(i))
                for i in range(5)
            ]
            results = [f.result() for f in futures]
        
        assert results == [i * 2 for i in range(5)]
    
    def test_async_runner_health_check(self):
        """Test async runner health check functionality."""
        runner = get_async_runner()
        assert runner.is_healthy() is True
    
    def test_async_runner_reuse(self):
        """Test that the global async runner is reused."""
        runner1 = get_async_runner()
        runner2 = get_async_runner()
        assert runner1 is runner2
    
    def test_async_operation_with_httpx_like_pattern(self):
        """Test async operation that simulates httpx usage pattern."""
        async def mock_http_request():
            # Simulate an HTTP request pattern similar to what MSGraph uses
            await asyncio.sleep(0.1)  # Simulate network delay
            return {
                "status_code": 200,
                "json": {"events": [{"id": "1", "subject": "Test Meeting"}]}
            }
        
        result = run_async(mock_http_request())
        assert result["status_code"] == 200
        assert len(result["json"]["events"]) == 1
    
    def test_nested_async_calls(self):
        """Test nested async calls to ensure no event loop conflicts."""
        async def inner_operation(value):
            await asyncio.sleep(0.05)
            return value + 1
        
        async def outer_operation():
            # This simulates the pattern where async code calls other async code
            result1 = await inner_operation(1)
            result2 = await inner_operation(result1)
            return result2
        
        result = run_async(outer_operation())
        assert result == 3
    
    def test_error_handling_with_context(self):
        """Test error handling preserves context information."""
        async def operation_with_context():
            try:
                raise ValueError("Original error")
            except ValueError as e:
                # Add context like the MSGraph repository does
                if hasattr(e, "add_note"):
                    e.add_note("Additional context")
                raise
        
        with pytest.raises(ValueError, match="Original error"):
            run_async(operation_with_context())


class TestAsyncRunnerIntegration:
    """Integration tests for async runner with realistic scenarios."""
    
    def test_msgraph_like_operation_pattern(self):
        """Test operation pattern similar to MSGraph repository."""
        async def mock_msgraph_operation():
            # Simulate the pattern used in MSGraph repository
            try:
                # Simulate API call
                await asyncio.sleep(0.1)
                
                # Simulate successful response
                return {
                    "value": [
                        {"id": "1", "subject": "Meeting 1"},
                        {"id": "2", "subject": "Meeting 2"}
                    ]
                }
            except Exception as e:
                # Simulate error handling pattern
                raise Exception(f"Failed to fetch appointments: {e}")
        
        result = run_async(mock_msgraph_operation())
        assert len(result["value"]) == 2
        assert result["value"][0]["subject"] == "Meeting 1"
    
    def test_bulk_operation_pattern(self):
        """Test bulk operation pattern similar to appointment archiving."""
        async def mock_bulk_operation(items):
            errors = []
            for i, item in enumerate(items):
                try:
                    # Simulate processing each item
                    await asyncio.sleep(0.01)
                    if item.get("should_fail"):
                        raise ValueError(f"Failed to process item {i}")
                except Exception as e:
                    errors.append(f"Item {i}: {str(e)}")
            return errors
        
        test_items = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2", "should_fail": True},
            {"id": 3, "name": "Item 3"}
        ]
        
        errors = run_async(mock_bulk_operation(test_items))
        assert len(errors) == 1
        assert "Item 1" in errors[0]
    
    def test_performance_comparison(self):
        """Test performance characteristics of the async runner."""
        async def fast_operation():
            return "fast"
        
        # Measure execution time
        start_time = time.time()
        for _ in range(10):
            result = run_async(fast_operation())
            assert result == "fast"
        end_time = time.time()
        
        # Should complete quickly (less than 1 second for 10 operations)
        assert end_time - start_time < 1.0
    
    @patch('core.utilities.async_runner.logger')
    def test_error_logging(self, mock_logger):
        """Test that errors are properly logged."""
        async def failing_operation():
            raise RuntimeError("Test runtime error")
        
        with pytest.raises(RuntimeError):
            run_async(failing_operation())
        
        # Verify that the safe version logs the error
        result = run_async_safe(failing_operation(), default="fallback")
        assert result == "fallback"
        
        # Check that logger.exception was called
        mock_logger.exception.assert_called()


class TestAsyncRunnerEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_very_short_timeout(self):
        """Test with very short timeout."""
        async def quick_operation():
            await asyncio.sleep(0.001)  # 1ms
            return "quick"
        
        # Should succeed with short but sufficient timeout
        result = run_async(quick_operation(), timeout=0.1)
        assert result == "quick"
        
        # Should fail with insufficient timeout
        with pytest.raises(asyncio.TimeoutError):
            run_async(quick_operation(), timeout=0.0001)
    
    def test_none_return_value(self):
        """Test operation that returns None."""
        async def none_operation():
            return None
        
        result = run_async(none_operation())
        assert result is None
    
    def test_complex_data_structures(self):
        """Test with complex data structures."""
        async def complex_operation():
            return {
                "nested": {
                    "list": [1, 2, {"inner": "value"}],
                    "tuple": (1, 2, 3),
                    "set_as_list": list({4, 5, 6})  # Sets aren't JSON serializable
                }
            }
        
        result = run_async(complex_operation())
        assert result["nested"]["list"][2]["inner"] == "value"
        assert result["nested"]["tuple"] == (1, 2, 3)
        assert len(result["nested"]["set_as_list"]) == 3
