"""
Enhanced Async Runner for Sync/Async Integration

This module provides a robust solution for running async code from synchronous contexts,
specifically designed to resolve event loop issues in the admin-assistant project.
"""

import asyncio
import atexit
import gc
import logging
import os
import threading
import weakref
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Awaitable, Callable, Optional, TypeVar

# Optional psutil for memory monitoring
_has_psutil = False
_process = None
try:
    import psutil
    _process = psutil.Process(os.getpid())
    _has_psutil = True
except ImportError:
    # psutil is optional - we'll just disable memory monitoring if it's not available
    pass

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AsyncRunner:
    """
    Thread-safe async operation runner for sync contexts.

    This class maintains a dedicated background thread with its own event loop,
    allowing sync code to safely execute async operations without conflicts.
    """

    # Class variable to track atexit registration
    _atexit_registered = False

    # Maximum number of concurrent tasks before we start warning
    MAX_CONCURRENT_TASKS = 100

    # Memory threshold for warnings (80% of available memory)
    MEMORY_WARNING_THRESHOLD = 0.8

    @classmethod
    def _register_atexit_handler(cls):
        """Register the atexit handler only once for all instances."""
        if not cls._atexit_registered:
            atexit.register(shutdown_global_runner)
            cls._atexit_registered = True

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

        # Register cleanup on exit (class method ensures it's only done once)
        self.__class__._register_atexit_handler()

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
                            # Process pending tasks and callbacks
                            self._loop.run_until_complete(asyncio.sleep(0.1))
                        except Exception as e:
                            if not self._shutdown_event.is_set():
                                logger.exception(f"Error in background event loop: {e}")
                            break

                except Exception as e:
                    logger.exception(f"Failed to start background event loop: {e}")
                finally:
                    # Clean up the loop
                    if self._loop and not self._loop.is_closed():
                        try:
                            # Cancel all pending tasks
                            pending = asyncio.all_tasks(self._loop)
                            for task in pending:
                                if not task.done():
                                    task.cancel()

                            # Wait for cancellations to complete with timeout
                            if pending:
                                try:
                                    self._loop.run_until_complete(
                                        asyncio.wait_for(
                                            asyncio.gather(*pending, return_exceptions=True),
                                            timeout=2.0
                                        )
                                    )
                                except asyncio.TimeoutError:
                                    logger.warning("Some tasks did not cancel within timeout")
                                except Exception as e:
                                    logger.debug(f"Expected exception during task cancellation: {e}")

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

            # Use time.sleep instead of creating a new Event object each time
            import time
            while self._loop is None and waited < max_wait:
                time.sleep(wait_interval)
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

        # For extremely short timeouts, raise TimeoutError immediately
        # This ensures consistent behavior for unrealistic timeout values
        if timeout < 0.001:  # 1 millisecond threshold
            logger.error(f"Timeout value too small: {timeout} seconds")
            raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")

        # Check memory usage and task limits before running
        memory_percent = self._check_memory_usage()
        task_count = self._check_task_limits()

        # If we're approaching resource limits, be more aggressive with cleanup
        if memory_percent > self.MEMORY_WARNING_THRESHOLD * 0.8 or task_count > self.MAX_CONCURRENT_TASKS * 0.8:
            logger.info("Approaching resource limits, performing aggressive cleanup")
            self._cleanup_completed_tasks(force_cleanup=True)

            # If we're still over limits after cleanup, delay a bit to allow resources to be freed
            if self._check_memory_usage() > self.MEMORY_WARNING_THRESHOLD or self._check_task_limits() > self.MAX_CONCURRENT_TASKS:
                logger.warning("Resource limits still exceeded after cleanup, adding delay")
                time.sleep(0.1)  # Short delay to allow resources to be freed
                gc.collect()  # Force garbage collection again

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
        finally:
            # Help garbage collection by cleaning up completed tasks
            self._cleanup_completed_tasks()

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

    def _cleanup_completed_tasks(self, force_cleanup=False):
        """
        Clean up completed tasks to prevent memory leaks.
        This method should be called periodically to ensure resources are freed.

        Args:
            force_cleanup: If True, will force garbage collection even if no tasks are completed
        """
        if self._loop is None or self._loop.is_closed():
            return

        try:
            # Get all tasks in the loop
            tasks = asyncio.all_tasks(self._loop)

            # Identify completed tasks
            completed_tasks = [task for task in tasks if task.done()]
            completed_count = len(completed_tasks)

            # Log task counts for debugging
            total_tasks = len(tasks)
            if total_tasks > 10:  # Only log if there are many tasks
                logger.debug(f"Task status: {completed_count} completed, {total_tasks - completed_count} pending")

            if completed_count > 0 or force_cleanup:
                if completed_count > 0:
                    logger.debug(f"Cleaning up {completed_count} completed tasks")

                # Explicitly clear task references to help garbage collection
                for task in completed_tasks:
                    try:
                        # Get the result to ensure exceptions are retrieved and don't cause warnings
                        if task.done() and not task.cancelled():
                            task.result()
                    except Exception:
                        # Ignore exceptions, we just want to ensure they're retrieved
                        pass

                # Force garbage collection to clean up task resources
                gc.collect()

                # If we have too many tasks, log a warning as this might indicate a leak
                if total_tasks > 100:
                    logger.warning(f"High number of tasks detected: {total_tasks}. Possible memory leak.")
        except Exception as e:
            # Don't let cleanup errors affect the main operation
            logger.debug(f"Error during task cleanup: {e}")

    def _check_memory_usage(self):
        """
        Check current memory usage and log warnings if it's too high.
        Returns the current memory usage as a percentage.
        """
        if not _has_psutil:
            return 0.0

        try:
            # Get memory info
            memory_info = _process.memory_info()
            memory_percent = _process.memory_percent()

            # Log memory usage if it's high
            if memory_percent > self.MEMORY_WARNING_THRESHOLD:
                logger.warning(
                    f"High memory usage detected: {memory_percent:.1f}% "
                    f"({memory_info.rss / (1024 * 1024):.1f} MB)"
                )

                # Force garbage collection to try to free memory
                gc.collect()

            return memory_percent
        except Exception as e:
            logger.debug(f"Error checking memory usage: {e}")
            return 0.0

    def _check_task_limits(self):
        """
        Check if we have too many tasks and log warnings.
        Returns the current number of tasks.
        """
        if self._loop is None or self._loop.is_closed():
            return 0

        try:
            # Get all tasks
            tasks = asyncio.all_tasks(self._loop)
            task_count = len(tasks)

            # Log warning if we have too many tasks
            if task_count > self.MAX_CONCURRENT_TASKS:
                logger.warning(
                    f"Too many concurrent tasks: {task_count} "
                    f"(limit: {self.MAX_CONCURRENT_TASKS})"
                )

                # Force cleanup to try to reduce task count
                self._cleanup_completed_tasks(force_cleanup=True)

            return task_count
        except Exception as e:
            logger.debug(f"Error checking task limits: {e}")
            return 0

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

            # Check memory usage and task limits
            memory_percent = self._check_memory_usage()
            task_count = self._check_task_limits()

            # If we're severely over limits, consider the runner unhealthy
            if memory_percent > self.MEMORY_WARNING_THRESHOLD * 1.2 or task_count > self.MAX_CONCURRENT_TASKS * 1.5:
                logger.error(f"Runner considered unhealthy due to resource exhaustion: "
                            f"memory={memory_percent:.1f}%, tasks={task_count}")
                return False

            # Test with a simple coroutine
            async def health_check():
                return True

            result = self.run_async(health_check(), timeout=0.1)  # Reduced timeout for faster health checks
            return result is True

        except Exception as e:
            logger.exception(f"Health check failed: {e}")
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
                    # Try with timeout parameter first (Python 3.9+)
                    try:
                        self._executor.shutdown(wait=True, timeout=timeout)
                    except TypeError:
                        # Fallback for older Python versions or implementations
                        logger.debug("ThreadPoolExecutor.shutdown() doesn't support timeout parameter, using fallback")
                        self._executor.shutdown(wait=True)
                except Exception as e:
                    logger.exception(f"Error shutting down executor: {e}")
                finally:
                    self._executor = None

            # Stop the event loop gracefully
            if self._loop and not self._loop.is_closed():
                try:
                    # Simply stop the loop - the background thread cleanup will handle tasks
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
_async_runner_ref = None  # Will hold a weakref to the AsyncRunner instance
_async_runner_lock = threading.Lock()


def get_async_runner() -> AsyncRunner:
    """
    Get the global AsyncRunner instance, creating it if necessary.

    Returns:
        The global AsyncRunner instance
    """
    global _async_runner_ref

    with _async_runner_lock:
        # Get the runner from the weakref if it exists
        runner = None if _async_runner_ref is None else _async_runner_ref()

        # Check if we need to create a new runner
        if runner is None or not runner.is_healthy():
            if runner is not None:
                logger.warning("Recreating unhealthy AsyncRunner instance")
                try:
                    runner.shutdown(timeout=2.0)
                except Exception as e:
                    logger.exception(f"Error shutting down old AsyncRunner: {e}")
                # Help garbage collection
                runner = None
                # Force garbage collection to clean up resources
                gc.collect()

            # Create new runner and store a weak reference to it
            runner = AsyncRunner()
            _async_runner_ref = weakref.ref(runner)
            logger.debug("Created new global AsyncRunner instance")

        return runner


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
    global _async_runner_ref

    with _async_runner_lock:
        # Get the runner from the weakref if it exists
        runner = None if _async_runner_ref is None else _async_runner_ref()

        if runner is not None:
            try:
                runner.shutdown()
            except Exception as e:
                logger.exception(f"Error during global runner shutdown: {e}")

            # Clear the reference
            _async_runner_ref = None

            # Force garbage collection to clean up resources
            gc.collect()
