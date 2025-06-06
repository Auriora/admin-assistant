"""
Enhanced Async Runner for Sync/Async Integration

This module provides a robust solution for running async code from synchronous contexts,
specifically designed to resolve event loop issues in the admin-assistant project.
"""

import asyncio
import atexit
import logging
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Awaitable, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AsyncRunner:
    """
    Thread-safe async operation runner for sync contexts.
    
    This class maintains a dedicated background thread with its own event loop,
    allowing sync code to safely execute async operations without conflicts.
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize the async runner.
        
        Args:
            max_workers: Maximum number of worker threads for the executor
        """
        self._max_workers = max_workers
        self._executor = None
        self._loop_thread = None
        self._loop = None
        self._shutdown_event = threading.Event()
        self._lock = threading.Lock()
        self._start_background_loop()
        
        # Register cleanup on exit
        atexit.register(self.shutdown)
    
    def _start_background_loop(self):
        """Start a dedicated event loop in a background thread."""
        with self._lock:
            if self._loop_thread and self._loop_thread.is_alive():
                return  # Already running
            
            self._shutdown_event.clear()
            
            def run_loop():
                """Background thread function that runs the event loop."""
                try:
                    # Create new event loop for this thread
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)
                    
                    logger.debug("Started background event loop")
                    
                    # Run until shutdown is requested
                    while not self._shutdown_event.is_set():
                        try:
                            # Run pending tasks with timeout to allow shutdown checks
                            self._loop.run_until_complete(
                                asyncio.wait_for(
                                    asyncio.sleep(0.1), 
                                    timeout=1.0
                                )
                            )
                        except asyncio.TimeoutError:
                            continue  # Normal timeout, check for shutdown
                        except Exception as e:
                            logger.exception(f"Error in background event loop: {e}")
                            
                except Exception as e:
                    logger.exception(f"Failed to start background event loop: {e}")
                finally:
                    # Clean up the loop
                    if self._loop and not self._loop.is_closed():
                        try:
                            # Cancel all pending tasks
                            pending = asyncio.all_tasks(self._loop)
                            for task in pending:
                                task.cancel()
                            
                            # Wait for cancellations to complete
                            if pending:
                                self._loop.run_until_complete(
                                    asyncio.gather(*pending, return_exceptions=True)
                                )
                            
                            self._loop.close()
                        except Exception as e:
                            logger.exception(f"Error during loop cleanup: {e}")
                    
                    logger.debug("Background event loop stopped")
            
            self._loop_thread = threading.Thread(
                target=run_loop, 
                name="AsyncRunner-EventLoop",
                daemon=True
            )
            self._loop_thread.start()
            
            # Wait for loop to be ready (with timeout)
            max_wait = 5.0  # seconds
            wait_interval = 0.01
            waited = 0.0
            
            while self._loop is None and waited < max_wait:
                threading.Event().wait(wait_interval)
                waited += wait_interval
            
            if self._loop is None:
                raise RuntimeError("Failed to start background event loop within timeout")
            
            # Initialize executor
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="AsyncRunner-Worker"
            )
    
    def run_async(self, coro: Awaitable[T], timeout: float = 30.0) -> T:
        """
        Run an async coroutine in the background event loop.
        
        Args:
            coro: The coroutine to execute
            timeout: Maximum time to wait for completion (seconds)
            
        Returns:
            The result of the coroutine
            
        Raises:
            asyncio.TimeoutError: If the operation times out
            RuntimeError: If the async runner is not available
            Exception: Any exception raised by the coroutine
        """
        if self._shutdown_event.is_set():
            raise RuntimeError("AsyncRunner has been shut down")
        
        if self._loop is None or self._loop.is_closed():
            logger.warning("Background loop not available, restarting...")
            self._start_background_loop()
        
        try:
            # Submit the coroutine to the background loop
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            result = future.result(timeout=timeout)
            return result
            
        except FutureTimeoutError:
            logger.error(f"Async operation timed out after {timeout} seconds")
            raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")
        except Exception as e:
            logger.exception(f"Error running async operation: {e}")
            raise
    
    def run_async_safe(self, coro: Awaitable[T], timeout: float = 30.0, 
                      default: Optional[T] = None) -> Optional[T]:
        """
        Run an async coroutine with exception handling.
        
        Args:
            coro: The coroutine to execute
            timeout: Maximum time to wait for completion (seconds)
            default: Default value to return on error
            
        Returns:
            The result of the coroutine, or default value on error
        """
        try:
            return self.run_async(coro, timeout)
        except Exception as e:
            logger.exception(f"Async operation failed safely: {e}")
            return default
    
    def is_healthy(self) -> bool:
        """
        Check if the async runner is healthy and operational.
        
        Returns:
            True if the runner is healthy, False otherwise
        """
        try:
            if self._shutdown_event.is_set():
                return False
            
            if not self._loop_thread or not self._loop_thread.is_alive():
                return False
            
            if not self._loop or self._loop.is_closed():
                return False
            
            # Test with a simple coroutine
            async def health_check():
                return True
            
            result = self.run_async(health_check(), timeout=1.0)
            return result is True
            
        except Exception:
            return False
    
    def shutdown(self, timeout: float = 5.0):
        """
        Gracefully shutdown the async runner.
        
        Args:
            timeout: Maximum time to wait for shutdown (seconds)
        """
        logger.debug("Shutting down AsyncRunner...")
        
        with self._lock:
            # Signal shutdown
            self._shutdown_event.set()
            
            # Shutdown executor
            if self._executor:
                try:
                    self._executor.shutdown(wait=True, timeout=timeout)
                except Exception as e:
                    logger.exception(f"Error shutting down executor: {e}")
                finally:
                    self._executor = None
            
            # Stop the event loop
            if self._loop and not self._loop.is_closed():
                try:
                    self._loop.call_soon_threadsafe(self._loop.stop)
                except Exception as e:
                    logger.exception(f"Error stopping event loop: {e}")
            
            # Wait for thread to finish
            if self._loop_thread and self._loop_thread.is_alive():
                self._loop_thread.join(timeout=timeout)
                if self._loop_thread.is_alive():
                    logger.warning("Background thread did not stop within timeout")
            
            self._loop_thread = None
            self._loop = None
        
        logger.debug("AsyncRunner shutdown complete")


# Global instance with weak reference tracking
_async_runner: Optional[AsyncRunner] = None
_async_runner_lock = threading.Lock()


def get_async_runner() -> AsyncRunner:
    """
    Get the global AsyncRunner instance, creating it if necessary.
    
    Returns:
        The global AsyncRunner instance
    """
    global _async_runner
    
    with _async_runner_lock:
        if _async_runner is None or not _async_runner.is_healthy():
            if _async_runner is not None:
                logger.warning("Recreating unhealthy AsyncRunner instance")
                try:
                    _async_runner.shutdown(timeout=2.0)
                except Exception as e:
                    logger.exception(f"Error shutting down old AsyncRunner: {e}")
            
            _async_runner = AsyncRunner()
            logger.debug("Created new global AsyncRunner instance")
        
        return _async_runner


def run_async(coro: Awaitable[T], timeout: float = 30.0) -> T:
    """
    Public interface for running async code from sync context.
    
    Args:
        coro: The coroutine to execute
        timeout: Maximum time to wait for completion (seconds)
        
    Returns:
        The result of the coroutine
    """
    runner = get_async_runner()
    return runner.run_async(coro, timeout)


def run_async_safe(coro: Awaitable[T], timeout: float = 30.0, 
                  default: Optional[T] = None) -> Optional[T]:
    """
    Public interface for safely running async code from sync context.
    
    Args:
        coro: The coroutine to execute
        timeout: Maximum time to wait for completion (seconds)
        default: Default value to return on error
        
    Returns:
        The result of the coroutine, or default value on error
    """
    runner = get_async_runner()
    return runner.run_async_safe(coro, timeout, default)


def shutdown_global_runner():
    """Shutdown the global AsyncRunner instance."""
    global _async_runner
    
    with _async_runner_lock:
        if _async_runner is not None:
            _async_runner.shutdown()
            _async_runner = None
