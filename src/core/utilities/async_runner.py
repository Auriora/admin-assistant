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
    # Note: psutil.memory_percent() returns percentage values (e.g., 1.7 for 1.7%)
    MEMORY_WARNING_THRESHOLD = 80.0

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
            if self._loop_thread and self._loop_thread.is_alive() and self._loop and not self._loop.is_closed():
                return  # Already running and healthy

            # Clear any previous state
            self._shutdown_event.clear()

            # Create a synchronization event to ensure the loop is ready before proceeding
            loop_ready_event = threading.Event()
            loop_error = [None]  # Use a list to capture error from thread

            def run_loop():
                """Background thread function that runs the event loop."""
                try:
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # Set the loop reference in the main object
                    self._loop = loop

                    # Signal that the loop is ready
                    loop_ready_event.set()

                    logger.debug("Started background event loop")

                    # Run until shutdown is requested
                    while not self._shutdown_event.is_set():
                        try:
                            # Process pending tasks and callbacks with shorter sleep for better responsiveness
                            self._loop.run_until_complete(asyncio.sleep(0.01))
                        except asyncio.CancelledError:
                            # This is expected during shutdown
                            logger.debug("Sleep task cancelled in event loop")
                            break
                        except RuntimeError as e:
                            # Handle specific runtime errors that can occur during shutdown
                            if "Event loop is closed" in str(e):
                                logger.debug("Event loop closed while running")
                                break
                            elif not self._shutdown_event.is_set():
                                logger.exception(f"RuntimeError in background event loop: {e}")
                                break
                            else:
                                # If shutdown is requested, just exit quietly
                                break
                        except Exception as e:
                            if not self._shutdown_event.is_set():
                                logger.exception(f"Error in background event loop: {e}")
                            break

                except Exception as e:
                    logger.exception(f"Failed to start background event loop: {e}")
                    # Store the error to be checked by the main thread
                    loop_error[0] = e
                    # Make sure to signal even on error
                    loop_ready_event.set()
                finally:
                    # Clean up the loop
                    if self._loop and not self._loop.is_closed():
                        try:
                            # Cancel all pending tasks
                            try:
                                pending = asyncio.all_tasks(self._loop)

                                # Log task count for debugging
                                if pending:
                                    logger.debug(f"Cancelling {len(pending)} pending tasks in event loop thread")

                                for task in pending:
                                    if not task.done():
                                        task.cancel()

                                # Wait for cancellations to complete with timeout
                                if pending:
                                    try:
                                        # Wrap in try/except to handle CancelledError
                                        try:
                                            self._loop.run_until_complete(
                                                asyncio.wait_for(
                                                    asyncio.gather(*pending, return_exceptions=True),
                                                    timeout=1.0  # Shorter timeout for faster shutdown
                                                )
                                            )
                                        except asyncio.CancelledError:
                                            # This is expected when cancelling tasks
                                            pass
                                    except asyncio.TimeoutError:
                                        logger.warning("Some tasks did not cancel within timeout")
                                    except RuntimeError as e:
                                        # This can happen if the loop is already stopping
                                        logger.debug(f"RuntimeError during task cancellation: {e}")
                                    except Exception as e:
                                        logger.debug(f"Expected exception during task cancellation: {e}")
                            except Exception as e:
                                logger.debug(f"Error getting tasks: {e}")

                            # Close the loop safely
                            try:
                                self._loop.close()
                            except Exception as e:
                                logger.debug(f"Error closing event loop: {e}")
                        except Exception as e:
                            logger.debug(f"Error during loop cleanup: {e}")

                    logger.debug("Background event loop stopped")

            # Shutdown any existing thread/loop before starting a new one
            if self._loop_thread and self._loop_thread.is_alive():
                logger.debug("Shutting down existing event loop thread")
                self._shutdown_event.set()
                try:
                    self._loop_thread.join(timeout=1.0)
                except Exception:
                    pass

            # Reset loop reference
            self._loop = None

            # Start new thread
            self._loop_thread = threading.Thread(
                target=run_loop, 
                name="AsyncRunner-EventLoop",
                daemon=True
            )
            self._loop_thread.start()

            # Wait for loop to be ready using the event (with timeout)
            max_wait = 5.0  # seconds
            if not loop_ready_event.wait(timeout=max_wait):
                raise RuntimeError("Failed to start background event loop within timeout")

            # Check if there was an error in the thread
            if loop_error[0] is not None:
                raise RuntimeError(f"Failed to start background event loop: {loop_error[0]}")

            # Double-check that the loop is actually set and not closed
            if self._loop is None or self._loop.is_closed():
                raise RuntimeError("Event loop was not properly initialized")

            # Initialize executor
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="AsyncRunner-Worker"
            )

    def run_async(self, coro: Awaitable[T], timeout: float = 30.0, skip_checks: bool = False) -> T:
        """
        Run an async coroutine in the background event loop.

        Args:
            coro: The coroutine to execute
            timeout: Maximum time to wait for completion (seconds)
            skip_checks: If True, skip memory and task limit checks for better performance

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

        # Only perform resource checks for non-trivial operations or when explicitly requested
        if not skip_checks:
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

            # For concurrent operations, we need to be more careful with timeouts
            # Use a slightly longer effective timeout to account for thread scheduling overhead
            effective_timeout = timeout * 1.1 if timeout > 0 else timeout

            try:
                result = future.result(timeout=effective_timeout)
                return result
            except FutureTimeoutError:
                # Cancel the future to prevent it from continuing to run and consuming resources
                future.cancel()
                logger.error(f"Async operation timed out after {timeout} seconds")
                raise asyncio.TimeoutError(f"Operation timed out after {timeout} seconds")

        except Exception as e:
            if not isinstance(e, asyncio.TimeoutError):
                logger.exception(f"Error running async operation: {e}")
            raise
        finally:
            # Only perform cleanup for non-trivial operations or when explicitly requested
            if not skip_checks:
                # Help garbage collection by cleaning up completed tasks
                self._cleanup_completed_tasks()

    def run_async_safe(self, coro: Awaitable[T], timeout: float = 30.0, 
                      default: Optional[T] = None, skip_checks: bool = False) -> Optional[T]:
        """
        Run an async coroutine with exception handling.

        Args:
            coro: The coroutine to execute
            timeout: Maximum time to wait for completion (seconds)
            default: Default value to return on error
            skip_checks: If True, skip memory and task limit checks for better performance

        Returns:
            The result of the coroutine, or default value on error
        """
        try:
            return self.run_async(coro, timeout, skip_checks=skip_checks)
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
            # First, check basic health indicators without touching the event loop
            with self._lock:
                # Check if shutdown has been requested
                if self._shutdown_event.is_set():
                    logger.debug("Health check failed: shutdown event is set")
                    return False

                # Check if thread is alive
                if not self._loop_thread or not self._loop_thread.is_alive():
                    logger.debug("Health check failed: event loop thread is not alive")
                    return False

                # Check if loop exists and is not closed
                if not self._loop or self._loop.is_closed():
                    logger.debug("Health check failed: event loop is None or closed")
                    return False

                # Check if executor exists
                if not self._executor:
                    logger.debug("Health check failed: executor is None")
                    return False

            # Only check resource limits if basic checks pass
            try:
                # Check memory usage and task limits
                memory_percent = self._check_memory_usage()
                task_count = self._check_task_limits()

                # If we're severely over limits, consider the runner unhealthy
                if memory_percent > self.MEMORY_WARNING_THRESHOLD * 1.2 or task_count > self.MAX_CONCURRENT_TASKS * 1.5:
                    logger.error(f"Runner considered unhealthy due to resource exhaustion: "
                                f"memory={memory_percent:.1f}%, tasks={task_count}")
                    return False
            except Exception as e:
                # Don't fail the health check just because resource checks failed
                logger.debug(f"Resource check failed during health check: {e}")

            # Only perform the coroutine test if everything else passes
            # This is the most expensive check, so we do it last
            try:
                # Test with a simple coroutine
                async def health_check():
                    return True

                # Use a very short timeout to avoid blocking
                # But make it a bit longer to be more resilient to resource contention
                try:
                    result = self.run_async(health_check(), timeout=0.5, skip_checks=True)
                    return result is True
                except asyncio.TimeoutError:
                    # If it times out, try one more time with a longer timeout
                    # This helps with resource contention from previous tests
                    logger.debug("Health check timed out, retrying with longer timeout")
                    try:
                        result = self.run_async(health_check(), timeout=1.0, skip_checks=True)
                        return result is True
                    except Exception as e:
                        logger.debug(f"Retry coroutine test failed during health check: {e}")
                        return False
            except Exception as e:
                logger.debug(f"Coroutine test failed during health check: {e}")
                return False

        except Exception as e:
            logger.exception(f"Health check failed with unexpected error: {e}")
            return False

    def shutdown(self, timeout: float = 5.0):
        """
        Gracefully shutdown the async runner with enhanced cleanup.

        Args:
            timeout: Maximum time to wait for shutdown (seconds)
        """
        logger.debug("Shutting down AsyncRunner...")

        with self._lock:
            # Signal shutdown
            self._shutdown_event.set()

            # Shutdown executor with aggressive cleanup
            if self._executor:
                try:
                    # Cancel all pending futures first
                    if hasattr(self._executor, '_threads'):
                        self._executor._threads.clear()  # Clear thread references

                    # Try with timeout parameter first (Python 3.9+)
                    try:
                        self._executor.shutdown(wait=True, timeout=timeout/2)
                    except TypeError:
                        # Fallback for older Python versions
                        logger.debug("ThreadPoolExecutor.shutdown() doesn't support timeout parameter, using fallback")
                        self._executor.shutdown(wait=True)

                    # Force cleanup if threads are still alive
                    if hasattr(self._executor, '_threads'):
                        for thread in list(self._executor._threads):
                            if thread.is_alive():
                                logger.warning(f"Force terminating executor thread: {thread.name}")
                                # We can't force-kill threads in Python, but we can try to help GC
                                for attr in dir(thread):
                                    if not attr.startswith('_'):
                                        try:
                                            setattr(thread, attr, None)
                                        except (AttributeError, TypeError):
                                            pass

                except Exception as e:
                    logger.exception(f"Error shutting down executor: {e}")
                finally:
                    # Ensure executor is cleared even if an exception occurs
                    self._executor = None

            # Stop the event loop with enhanced cleanup
            if self._loop and not self._loop.is_closed():
                try:
                    # Cancel all remaining tasks before stopping
                    try:
                        pending_tasks = asyncio.all_tasks(self._loop)

                        # Log the number of pending tasks for debugging
                        if pending_tasks:
                            logger.debug(f"Cancelling {len(pending_tasks)} pending tasks during shutdown")

                        # Cancel all tasks
                        for task in pending_tasks:
                            if not task.done():
                                # Get task name for better debugging
                                task_name = task.get_name() if hasattr(task, 'get_name') else str(task)
                                logger.debug(f"Cancelling task: {task_name}")
                                task.cancel()

                        # Wait briefly for tasks to cancel
                        if pending_tasks:
                            try:
                                # Use a very short timeout to avoid blocking
                                # Wrap in try/except to handle CancelledError
                                try:
                                    # Create the coroutine but don't run it yet
                                    wait_coro = asyncio.wait_for(
                                        asyncio.gather(*pending_tasks, return_exceptions=True),
                                        timeout=0.2
                                    )

                                    # Run the coroutine with proper exception handling
                                    self._loop.run_until_complete(wait_coro)
                                except asyncio.CancelledError:
                                    # This is expected when cancelling tasks
                                    pass
                            except (asyncio.TimeoutError, RuntimeError) as e:
                                # Expected if tasks don't complete or loop is already stopping
                                logger.debug(f"Expected error while waiting for tasks to cancel: {type(e).__name__}")
                    except RuntimeError as e:
                        # "There is no current event loop in thread" - can happen during shutdown
                        logger.debug(f"RuntimeError during task cancellation: {e}")

                    # Stop the loop
                    try:
                        self._loop.call_soon_threadsafe(self._loop.stop)
                    except RuntimeError:
                        # Loop might already be closed
                        pass

                    # Give tasks a moment to cancel
                    import time
                    time.sleep(0.1)

                    # Close the loop explicitly
                    try:
                        if not self._loop.is_closed():
                            self._loop.close()
                    except Exception as e:
                        logger.debug(f"Error closing event loop: {e}")

                except Exception as e:
                    logger.exception(f"Error stopping event loop: {e}")

            # Wait for thread to finish with verification
            if self._loop_thread and self._loop_thread.is_alive():
                try:
                    self._loop_thread.join(timeout=timeout/2)
                    if self._loop_thread.is_alive():
                        logger.warning(f"Background thread {self._loop_thread.name} did not stop within timeout")
                        # Try to help garbage collection by clearing thread attributes
                        for attr in dir(self._loop_thread):
                            if not attr.startswith('_'):
                                try:
                                    setattr(self._loop_thread, attr, None)
                                except (AttributeError, TypeError):
                                    pass
                except Exception as e:
                    logger.debug(f"Error joining thread: {e}")

            # Clear references to help garbage collection
            self._loop_thread = None
            self._loop = None

        # Force garbage collection to clean up resources
        import gc
        for i in range(2):
            gc.collect()

        logger.debug("AsyncRunner shutdown complete")


# Global instance tracking
_async_runner = None  # Will hold a strong reference to the AsyncRunner instance
_async_runner_lock = threading.Lock()
_runner_creation_time = 0  # Track when the runner was created


def get_async_runner() -> AsyncRunner:
    """
    Get the global AsyncRunner instance, creating it if necessary.

    Returns:
        The global AsyncRunner instance
    """
    global _async_runner, _runner_creation_time

    with _async_runner_lock:
        # Check if we have a runner and if it's healthy
        runner_exists = _async_runner is not None
        runner_healthy = runner_exists and _async_runner.is_healthy()

        # Check if the runner has been alive for too long (over 1 hour)
        runner_too_old = False
        if runner_exists and time.time() - _runner_creation_time > 3600:  # 1 hour
            logger.debug("AsyncRunner instance is old, checking if it needs recreation")
            runner_too_old = True

        # Create a new runner if needed
        if not runner_exists or not runner_healthy or runner_too_old:
            # Shutdown the old runner if it exists
            if runner_exists:
                old_runner = _async_runner
                _async_runner = None  # Clear reference first to avoid circular references

                if not runner_healthy:
                    logger.warning("Recreating unhealthy AsyncRunner instance")
                elif runner_too_old:
                    logger.info("Recreating old AsyncRunner instance for maintenance")

                try:
                    old_runner.shutdown(timeout=2.0)
                except Exception as e:
                    logger.exception(f"Error shutting down old AsyncRunner: {e}")

                # Help garbage collection
                old_runner = None
                # Force garbage collection to clean up resources
                gc.collect()

            # Create new runner and store a strong reference to it
            try:
                _async_runner = AsyncRunner()
                _runner_creation_time = time.time()
                logger.debug("Created new global AsyncRunner instance")
            except Exception as e:
                logger.exception(f"Failed to create AsyncRunner: {e}")
                # If we can't create a new runner but had an old one that was just old (not unhealthy),
                # restore the old one as a fallback
                if runner_exists and runner_healthy and runner_too_old:
                    logger.warning("Restoring old AsyncRunner instance after failed recreation")
                    _async_runner = old_runner
                else:
                    # Re-raise if we can't create a runner and don't have a fallback
                    raise

        return _async_runner


def run_async(coro: Awaitable[T], timeout: float = 30.0, skip_checks: bool = True) -> T:
    """
    Public interface for running async code from sync context.

    Args:
        coro: The coroutine to execute
        timeout: Maximum time to wait for completion (seconds)
        skip_checks: If True, skip memory and task limit checks for better performance

    Returns:
        The result of the coroutine
    """
    runner = get_async_runner()
    return runner.run_async(coro, timeout, skip_checks=skip_checks)


def run_async_safe(coro: Awaitable[T], timeout: float = 30.0, 
                  default: Optional[T] = None, skip_checks: bool = True) -> Optional[T]:
    """
    Public interface for safely running async code from sync context.

    Args:
        coro: The coroutine to execute
        timeout: Maximum time to wait for completion (seconds)
        default: Default value to return on error
        skip_checks: If True, skip memory and task limit checks for better performance

    Returns:
        The result of the coroutine, or default value on error
    """
    runner = get_async_runner()
    return runner.run_async_safe(coro, timeout, default, skip_checks=skip_checks)


def shutdown_global_runner():
    """Shutdown the global AsyncRunner instance with enhanced cleanup."""
    global _async_runner, _runner_creation_time

    # Import gc at the function level to avoid UnboundLocalError
    import gc

    with _async_runner_lock:
        # Get the runner if it exists
        runner = _async_runner

        if runner is not None:
            try:
                # Use shorter timeout for test cleanup
                runner.shutdown(timeout=2.0)

                # Verify shutdown completed
                if hasattr(runner, '_loop_thread') and runner._loop_thread and runner._loop_thread.is_alive():
                    logger.warning("AsyncRunner thread still alive after shutdown")

                    # Additional attempt to force thread termination
                    try:
                        # Try to stop the loop more aggressively
                        if hasattr(runner, '_loop') and runner._loop and not runner._loop.is_closed():
                            runner._loop.call_soon_threadsafe(runner._loop.stop)

                        # Wait a bit more for thread to terminate
                        if runner._loop_thread.is_alive():
                            runner._loop_thread.join(0.5)
                    except Exception as e:
                        logger.debug(f"Error during additional thread cleanup: {e}")

            except Exception as e:
                logger.exception(f"Error during global runner shutdown: {e}")
            finally:
                # Clear all references to the runner
                if hasattr(runner, '_executor') and runner._executor:
                    runner._executor = None
                if hasattr(runner, '_loop'):
                    runner._loop = None
                if hasattr(runner, '_loop_thread'):
                    runner._loop_thread = None

            # Clear the reference immediately
            _async_runner = None
            # Reset creation time
            _runner_creation_time = 0

            # Collect all generations
            for gen in range(3):
                gc.collect(gen)

        # Additional cleanup: clear any module-level caches
        if hasattr(gc, 'set_debug'):
            # Temporarily enable debug to catch reference cycles
            old_flags = gc.get_debug()
            gc.set_debug(gc.DEBUG_UNCOLLECTABLE | gc.DEBUG_LEAK)

        # Force multiple garbage collection passes with different strategies
        for i in range(3):
            # First pass: standard collection
            # Second pass: collect all generations
            # Third pass: collect with debug enabled
            if i == 1:
                # Collect all generations
                for gen in range(3):
                    collected = gc.collect(gen)
                    if collected > 0:
                        logger.debug(f"GC generation {gen}: collected {collected} objects")
            else:
                collected = gc.collect()
                if collected > 0:
                    logger.debug(f"GC pass {i+1}: collected {collected} objects")

        # Check for uncollectable objects
        if hasattr(gc, 'garbage') and gc.garbage:
            # Log at info level so routine test cleanup doesn't flood warning output
            logger.info(f"Found {len(gc.garbage)} uncollectable objects")
            # Clear the garbage list to prevent memory leaks
            gc.garbage.clear()

        if hasattr(gc, 'set_debug'):
            gc.set_debug(old_flags)

        # Clear any remaining async tasks that might be holding references
        try:
            import asyncio
            for task in asyncio.all_tasks():
                if not task.done():
                    task.cancel()
        except (RuntimeError, ImportError):
            # RuntimeError if no running event loop
            pass
