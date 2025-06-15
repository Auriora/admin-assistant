"""
Database cleanup utilities for test isolation and memory management.
"""
import gc
import logging
import threading
import time
from typing import Optional, Set
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, scoped_session
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# Track all engines created during tests for cleanup
_test_engines: Set[Engine] = set()
_engines_lock = threading.Lock()


class DatabaseTestManager:
    """Manages database resources for tests with proper cleanup."""

    def __init__(self):
        self._engines: Set[Engine] = set()
        self._sessions: Set[Session] = set()

    def create_test_engine(self, url: str = 'sqlite:///file:memdb1?mode=memory&cache=shared&uri=true', **kwargs) -> Engine:
        """Create a test database engine with tracking for cleanup."""
        # Use StaticPool for SQLite in-memory to prevent connection issues
        if 'sqlite://' in url and ('memory' in url or ':memory:' in url):
            kwargs.setdefault('poolclass', StaticPool)
            connect_args = kwargs.get('connect_args', {})
            connect_args.setdefault('check_same_thread', False)
            if 'uri=true' in url or 'uri=True' in url:
                connect_args.setdefault('uri', True)
            kwargs['connect_args'] = connect_args

        kwargs.setdefault('echo', False)
        kwargs.setdefault('future', True)

        engine = create_engine(url, **kwargs)

        # Track engine for cleanup
        with _engines_lock:
            _test_engines.add(engine)
            self._engines.add(engine)

        return engine

    def create_test_session(self, engine: Engine) -> Session:
        """Create a test session with tracking for cleanup."""
        from sqlalchemy.orm import sessionmaker

        SessionClass = sessionmaker(bind=engine)
        session = SessionClass()

        self._sessions.add(session)
        return session

    def cleanup(self):
        """Clean up all tracked database resources."""
        # Close all sessions
        for session in list(self._sessions):
            try:
                if session.is_active:
                    session.rollback()
                session.close()
            except Exception as e:
                logger.debug(f"Error closing session: {e}")

        self._sessions.clear()

        # Dispose all engines
        for engine in list(self._engines):
            try:
                engine.dispose()
            except Exception as e:
                logger.debug(f"Error disposing engine: {e}")

        self._engines.clear()

        # Force garbage collection
        gc.collect()


def cleanup_all_test_databases():
    """Clean up all database resources created during tests."""
    global _test_engines

    with _engines_lock:
        engines_to_cleanup = list(_test_engines)
        _test_engines.clear()

    for engine in engines_to_cleanup:
        try:
            # Close all connections in the pool
            engine.dispose()

            # For SQLite, ensure the connection is fully closed
            if hasattr(engine.pool, '_creator'):
                creator = engine.pool._creator
                if hasattr(creator, 'close'):
                    creator.close()

        except Exception as e:
            logger.debug(f"Error during database cleanup: {e}")

    # Clear SQLAlchemy scoped session registry
    try:
        from core.db import SessionLocal
        if hasattr(SessionLocal, 'remove'):
            SessionLocal.remove()
    except Exception as e:
        logger.debug(f"Error clearing scoped session registry: {e}")

    # Force garbage collection to clean up connection objects
    for _ in range(2):
        gc.collect()


def wait_for_connection_cleanup(max_wait: float = 1.0):
    """Wait for database connections to be fully cleaned up."""
    import threading

    initial_thread_count = threading.active_count()
    wait_interval = 0.1
    waited = 0.0

    while waited < max_wait:
        current_thread_count = threading.active_count()

        # If thread count has returned to initial or lower, cleanup is likely complete
        if current_thread_count <= initial_thread_count:
            break

        time.sleep(wait_interval)
        waited += wait_interval

    if waited >= max_wait:
        logger.debug(f"Database cleanup wait timeout after {max_wait}s")


class IsolatedDatabaseTest:
    """Context manager for completely isolated database tests."""

    def __init__(self, url: str = 'sqlite:///file:memdb1?mode=memory&cache=shared&uri=true'):
        self.url = url
        self.manager = DatabaseTestManager()
        self.engine: Optional[Engine] = None
        self.session: Optional[Session] = None

    def __enter__(self):
        self.engine = self.manager.create_test_engine(self.url)

        # Create all tables
        from core.db import Base
        Base.metadata.create_all(self.engine)

        self.session = self.manager.create_test_session(self.engine)
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.session:
                if exc_type:
                    self.session.rollback()
                else:
                    self.session.commit()
        except Exception as e:
            logger.debug(f"Error during session cleanup: {e}")
        finally:
            self.manager.cleanup()
            wait_for_connection_cleanup()


# Pytest fixtures for easy use
def isolated_db_session():
    """Create an isolated database session for testing."""
    with IsolatedDatabaseTest(url='sqlite:///file:memdb1?mode=memory&cache=shared&uri=true') as session:
        yield session


def cleanup_database_resources():
    """Clean up all database resources - for use in test fixtures."""
    cleanup_all_test_databases()
    wait_for_connection_cleanup()
