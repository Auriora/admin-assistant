"""
Enhanced test fixtures for memory-efficient testing.
"""
import pytest
import gc
import threading
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from core.db import Base
from .database_cleanup import DatabaseTestManager


@pytest.fixture(scope="function")
def memory_efficient_db_session() -> Generator[Session, None, None]:
    """
    Create a memory-efficient database session that properly cleans up.
    
    This fixture should be used instead of creating individual engines in test files.
    """
    manager = DatabaseTestManager()
    
    try:
        # Create engine with memory-efficient settings
        engine = manager.create_test_engine(
            'sqlite:///:memory:',
            poolclass=StaticPool,
            connect_args={'check_same_thread': False},
            echo=False
        )
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        # Create session
        session = manager.create_test_session(engine)
        
        yield session
        
    finally:
        # Comprehensive cleanup
        manager.cleanup()


@pytest.fixture(scope="function") 
def isolated_test_environment():
    """
    Create a completely isolated test environment with cleanup verification.
    """
    initial_thread_count = threading.active_count()
    
    yield
    
    # Verify cleanup
    import time
    time.sleep(0.1)  # Allow cleanup to complete
    
    final_thread_count = threading.active_count()
    if final_thread_count > initial_thread_count + 1:  # Allow for some variance
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Thread count increased from {initial_thread_count} to {final_thread_count}. "
            "Possible resource leak."
        )


@contextmanager
def temporary_async_runner():
    """
    Context manager for creating a temporary AsyncRunner that's guaranteed to clean up.
    """
    from core.utilities.async_runner import AsyncRunner
    
    runner = AsyncRunner()
    try:
        yield runner
    finally:
        try:
            runner.shutdown(timeout=1.0)
        except Exception:
            pass
        
        # Force cleanup
        gc.collect()


@pytest.fixture
def clean_async_runner():
    """
    Fixture that provides a clean AsyncRunner instance with guaranteed cleanup.
    """
    with temporary_async_runner() as runner:
        yield runner


class MemoryTracker:
    """Track memory usage during tests."""
    
    def __init__(self):
        self.initial_memory = None
        self.peak_memory = None
        self.final_memory = None
        
        try:
            import psutil
            self.process = psutil.Process()
            self.available = True
        except ImportError:
            self.available = False
    
    def start(self):
        """Start memory tracking."""
        if self.available:
            self.initial_memory = self.process.memory_info().rss / 1024 / 1024
            self.peak_memory = self.initial_memory
    
    def update(self):
        """Update peak memory usage."""
        if self.available:
            current = self.process.memory_info().rss / 1024 / 1024
            if current > self.peak_memory:
                self.peak_memory = current
    
    def finish(self):
        """Finish tracking and return stats."""
        if self.available:
            self.final_memory = self.process.memory_info().rss / 1024 / 1024
            return {
                'initial': self.initial_memory,
                'peak': self.peak_memory,
                'final': self.final_memory,
                'increase': self.final_memory - self.initial_memory,
                'peak_increase': self.peak_memory - self.initial_memory
            }
        return None


@pytest.fixture
def memory_tracker():
    """Fixture that provides memory tracking for tests."""
    tracker = MemoryTracker()
    tracker.start()
    
    yield tracker
    
    stats = tracker.finish()
    if stats and stats['increase'] > 25:  # Warn if >25MB increase
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"High memory usage in test: {stats['increase']:.1f}MB increase "
            f"(peak: +{stats['peak_increase']:.1f}MB)"
        )


@pytest.fixture
def aggressive_cleanup():
    """
    Fixture that performs aggressive cleanup after test completion.
    """
    yield
    
    # Multiple garbage collection passes
    for i in range(3):
        collected = gc.collect()
        if collected == 0:
            break
    
    # Clear any remaining references
    import sys
    if hasattr(sys, '_clear_type_cache'):
        sys._clear_type_cache()


# Utility functions for test files
def create_memory_efficient_test_session():
    """
    Create a memory-efficient test session.
    Use this in test files that need custom session creation.
    """
    manager = DatabaseTestManager()
    engine = manager.create_test_engine()
    Base.metadata.create_all(engine)
    session = manager.create_test_session(engine)
    
    return session, manager


def cleanup_test_session(session, manager):
    """
    Clean up a test session created with create_memory_efficient_test_session.
    """
    try:
        session.close()
    except Exception:
        pass
    
    manager.cleanup()


# Decorator for memory-efficient test classes
def memory_efficient_test_class(cls):
    """
    Class decorator that adds memory efficiency to test classes.
    """
    original_setup = getattr(cls, 'setup_method', None)
    original_teardown = getattr(cls, 'teardown_method', None)
    
    def setup_method(self, method):
        if original_setup:
            original_setup(method)
        
        # Track initial state
        self._initial_thread_count = threading.active_count()
    
    def teardown_method(self, method):
        if original_teardown:
            original_teardown(method)
        
        # Cleanup and verify
        gc.collect()
        
        final_thread_count = threading.active_count()
        if final_thread_count > self._initial_thread_count + 1:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Thread leak in {cls.__name__}.{method.__name__}: "
                f"{self._initial_thread_count} -> {final_thread_count}"
            )
    
    cls.setup_method = setup_method
    cls.teardown_method = teardown_method
    
    return cls
