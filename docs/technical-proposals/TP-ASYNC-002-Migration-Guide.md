# Migration Guide: Enhanced Async Runner Implementation

## Overview

This guide provides step-by-step instructions for migrating from the current `_run_async()` implementation to the new enhanced `AsyncRunner` system.

## Phase 1: Immediate Implementation (This Week)

### Step 1: Update MSGraph Repository

Replace the current `_run_async()` function in `appointment_repository_msgraph.py`:

```python
# OLD CODE (remove):
def _run_async(coro, timeout=DEFAULT_TIMEOUT):
    # ... complex implementation with nest_asyncio and ThreadPoolExecutor

# NEW CODE (add):
from core.utilities.async_runner import run_async

# Replace all _run_async() calls with run_async()
```

### Step 2: Update Method Calls

Update all repository methods:

```python
# OLD:
def list_for_user(self, start_date=None, end_date=None) -> List[Appointment]:
    return _run_async(self.alist_for_user(start_date, end_date))

# NEW:
def list_for_user(self, start_date=None, end_date=None) -> List[Appointment]:
    return run_async(self.alist_for_user(start_date, end_date))
```

### Step 3: Remove Dependencies

Update `pyproject.toml` to remove `nest_asyncio`:

```toml
# Remove this line:
"nest_asyncio~=1.6.0",

# Add this for better async HTTP handling:
"httpx~=0.27.0",
```

### Step 4: Add Health Monitoring

Create a health check endpoint for the async runner:

```python
# In CLI or web interface
from core.utilities.async_runner import get_async_runner

def check_async_health():
    runner = get_async_runner()
    return {
        "healthy": runner.is_healthy(),
        "status": "operational" if runner.is_healthy() else "degraded"
    }
```

## Phase 2: Enhanced Error Handling (Next Week)

### Step 1: Implement Retry Logic

```python
from core.utilities.async_runner import run_async_safe
import time

def robust_msgraph_operation(operation_func, max_retries=3):
    """Wrapper for MS Graph operations with retry logic."""
    for attempt in range(max_retries):
        try:
            result = run_async_safe(operation_func(), timeout=30.0)
            if result is not None:
                return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
    
    raise RuntimeError(f"Operation failed after {max_retries} attempts")
```

### Step 2: Add Monitoring and Metrics

```python
import time
from contextlib import contextmanager

@contextmanager
def async_operation_metrics(operation_name: str):
    """Context manager for tracking async operation performance."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"Async operation '{operation_name}' took {duration:.2f}s")
        # Add metrics collection here if needed
```

### Step 3: Implement Circuit Breaker Pattern

```python
class AsyncCircuitBreaker:
    """Circuit breaker for async operations to prevent cascade failures."""
    
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, operation):
        """Execute operation with circuit breaker protection."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise RuntimeError("Circuit breaker is open")
        
        try:
            result = operation()
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            
            raise
```

## Phase 3: Testing and Validation (Week 3)

### Step 1: Add Comprehensive Tests

```python
# tests/unit/utilities/test_async_runner.py
import pytest
import asyncio
from core.utilities.async_runner import AsyncRunner, run_async

class TestAsyncRunner:
    
    def test_basic_async_operation(self):
        """Test basic async operation execution."""
        async def simple_operation():
            await asyncio.sleep(0.1)
            return "success"
        
        result = run_async(simple_operation())
        assert result == "success"
    
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
    
    def test_concurrent_operations(self):
        """Test multiple concurrent operations."""
        async def concurrent_operation(value):
            await asyncio.sleep(0.1)
            return value * 2
        
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(run_async, concurrent_operation(i))
                for i in range(10)
            ]
            results = [f.result() for f in futures]
        
        assert results == [i * 2 for i in range(10)]
```

### Step 2: Integration Tests

```python
# tests/integration/test_msgraph_async_integration.py
import pytest
from unittest.mock import AsyncMock, patch
from core.repositories.appointment_repository_msgraph import MSGraphAppointmentRepository

class TestMSGraphAsyncIntegration:
    
    @patch('core.repositories.appointment_repository_msgraph.get_graph_client')
    def test_list_appointments_with_new_runner(self, mock_get_client):
        """Test appointment listing with new async runner."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock calendar response
        mock_events = [
            {"id": "1", "subject": "Test Meeting 1"},
            {"id": "2", "subject": "Test Meeting 2"}
        ]
        mock_client.me.calendar.calendar_view.with_url.return_value.get.return_value.value = mock_events
        
        # Test the operation
        repo = MSGraphAppointmentRepository(user_id=1, msgraph_client=mock_client)
        appointments = repo.list_for_user()
        
        assert len(appointments) == 2
        assert appointments[0].subject == "Test Meeting 1"
```

## Phase 4: Production Deployment (Week 4)

### Step 1: Feature Flag Implementation

```python
# Add to configuration
ASYNC_RUNNER_ENABLED = os.getenv("ASYNC_RUNNER_ENABLED", "true").lower() == "true"

# In repository code
if ASYNC_RUNNER_ENABLED:
    from core.utilities.async_runner import run_async
    return run_async(self.alist_for_user(start_date, end_date))
else:
    # Fallback to old implementation
    return _run_async(self.alist_for_user(start_date, end_date))
```

### Step 2: Monitoring and Alerting

```python
# Add to application startup
from core.utilities.async_runner import get_async_runner
import logging

def setup_async_monitoring():
    """Setup monitoring for async operations."""
    runner = get_async_runner()
    
    # Health check endpoint
    @app.route('/health/async')
    def async_health():
        return {
            "healthy": runner.is_healthy(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Periodic health checks
    def periodic_health_check():
        if not runner.is_healthy():
            logger.error("AsyncRunner health check failed")
            # Send alert to monitoring system
    
    # Schedule periodic checks
    scheduler.add_job(
        periodic_health_check,
        'interval',
        minutes=5,
        id='async_health_check'
    )
```

### Step 3: Gradual Rollout

1. **Week 1**: Deploy with feature flag disabled, monitor baseline
2. **Week 2**: Enable for 10% of operations, monitor for issues
3. **Week 3**: Enable for 50% of operations, validate performance
4. **Week 4**: Enable for 100% of operations, remove old code

## Rollback Plan

If issues arise, immediate rollback steps:

1. **Set feature flag**: `ASYNC_RUNNER_ENABLED=false`
2. **Restart services**: Ensure old code path is active
3. **Monitor recovery**: Verify error rates return to baseline
4. **Investigate**: Analyze logs and metrics to identify root cause

## Success Metrics

Track these metrics during migration:

1. **Error Rate**: Should decrease by 90%+ for event loop errors
2. **Response Time**: Should improve by 20-30% for MS Graph operations
3. **Resource Usage**: Memory usage should be more stable
4. **Reliability**: Zero "Event loop is closed" errors

## Post-Migration Cleanup

After successful migration:

1. Remove `nest_asyncio` dependency
2. Delete old `_run_async()` function
3. Update documentation
4. Archive old workaround code
5. Plan for full async architecture migration
