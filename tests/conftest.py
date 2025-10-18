"""
Global test configuration and fixtures for the admin-assistant project.
"""
import pytest
import os
import tempfile
from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock, AsyncMock

# Set test environment
os.environ['APP_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CORE_DATABASE_URL'] = 'sqlite:///:memory:'

from core.db import Base
from core.models.user import User
from core.models.appointment import Appointment
from core.models.location import Location
from core.models.category import Category
from core.models.calendar import Calendar
from core.models.archive_configuration import ArchiveConfiguration
from core.models.action_log import ActionLog
from core.models.audit_log import AuditLog
from core.models.chat_session import ChatSession
from core.models.entity_association import EntityAssociation
from core.models.job_configuration import JobConfiguration
from core.models.prompt import Prompt
from core.models.timesheet import Timesheet
from core.models.backup_job_configuration import BackupJobConfiguration
from core.models.backup_configuration import BackupConfiguration
from core.models.restoration_configuration import RestorationConfiguration
from core.models.reversible_operation import ReversibleOperation, ReversibleOperationItem


@pytest.fixture(scope="session")
def test_db_engine():
    """Create a test database engine for the session with enhanced cleanup."""
    from .utils.database_cleanup import _test_engines
    from sqlalchemy.pool import StaticPool

    # Create engine with optimized settings for testing
    # Use a shared in-memory database that persists across connections
    engine = create_engine(
        'sqlite:///file:memdb1?mode=memory&cache=shared&uri=true', 
        echo=False,
        future=True,
        # Use StaticPool for in-memory SQLite to prevent connection issues
        poolclass=StaticPool,
        connect_args={'check_same_thread': False, 'uri': True}
    )

    # Track the engine for global cleanup
    _test_engines.add(engine)

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    try:
        # Dispose engine to close all connections
        engine.dispose()

        # Remove from tracking set
        _test_engines.discard(engine)

        # Force garbage collection to clean up connection objects
        import gc
        gc.collect()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Error during engine cleanup: {e}")


@pytest.fixture(scope="function")
def db_session(test_db_engine):
    """Create a fresh database session for each test with enhanced cleanup."""
    from sqlalchemy.orm import scoped_session
    from core.db import SessionLocal, Base

    # Start a transaction
    connection = test_db_engine.connect()
    transaction = connection.begin()

    # Create all tables in this connection to ensure they exist for this test
    Base.metadata.create_all(connection)

    # Create a dedicated session for this test
    Session = scoped_session(sessionmaker(bind=connection))
    session = Session()

    # Bind the session to the transaction
    session.bind = connection

    yield session

    try:
        # Rollback the transaction and close
        if session.is_active:
            session.rollback()
        session.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).debug(f"Error during session cleanup: {e}")
    finally:
        # Ensure connection is closed even if session close fails
        try:
            transaction.rollback()
        except Exception:
            pass

        try:
            connection.close()
        except Exception:
            pass

        # Clear the scoped session registry
        Session.remove()

        # Also clear the global session registry to prevent leaks
        if hasattr(SessionLocal, 'remove'):
            SessionLocal.remove()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_location(db_session, test_user):
    """Create a test location."""
    location = Location(
        user_id=test_user.id,
        name="Test Office",
        address="123 Test St, Test City",
        latitude=40.7128,
        longitude=-74.0060
    )
    db_session.add(location)
    db_session.commit()
    return location


@pytest.fixture
def test_category(db_session, test_user):
    """Create a test category."""
    category = Category(
        user_id=test_user.id,
        name="Test Category",
        color="#FF0000",
        is_private=False
    )
    db_session.add(category)
    db_session.commit()
    return category


@pytest.fixture
def test_calendar(db_session, test_user):
    """Create a test calendar."""
    calendar = Calendar(
        user_id=test_user.id,
        name="Test Calendar",
        ms_calendar_id="test-calendar-id",
        is_primary=True
    )
    db_session.add(calendar)
    db_session.commit()
    return calendar


@pytest.fixture
def test_appointment(db_session, test_user, test_calendar):
    """Create a test appointment."""
    appointment = Appointment(
        user_id=test_user.id,
        calendar_id=test_calendar.ms_calendar_id,
        subject="Test Appointment",
        start_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
        end_time=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
        is_archived=False
    )
    db_session.add(appointment)
    db_session.commit()
    return appointment


@pytest.fixture
def test_archive_config(db_session, test_user, test_calendar):
    """Create a test archive configuration."""
    config = ArchiveConfiguration(
        user_id=test_user.id,
        name="Test Archive Config",
        source_calendar_uri=f"msgraph://{test_calendar.ms_calendar_id}",
        destination_calendar_uri="msgraph://archive-calendar-id",
        is_active=True,
        timezone="UTC"
    )
    db_session.add(config)
    db_session.commit()
    return config


@pytest.fixture
def mock_msgraph_client():
    """Create a mock MS Graph client."""
    mock = MagicMock()

    # Setup nested async mocks for events
    calendar = MagicMock()
    events = MagicMock()
    events.post = AsyncMock()
    events.get = AsyncMock()

    # by_event_id returns an object with patch, delete, get as AsyncMock
    by_event_id_mock = MagicMock()
    by_event_id_mock.patch = AsyncMock()
    by_event_id_mock.delete = AsyncMock()
    by_event_id_mock.get = AsyncMock()
    events.by_event_id = MagicMock(return_value=by_event_id_mock)
    calendar.events = events

    # calendar_view for list_for_user
    calendar_view = MagicMock()
    calendar_view.with_url = MagicMock(return_value=MagicMock(get=AsyncMock()))
    calendar.calendar_view = calendar_view

    mock.users.by_user_id.return_value.calendars.by_calendar_id.return_value = calendar
    mock.users.by_user_id.return_value.calendar = calendar

    return mock


@pytest.fixture
def mock_msgraph_event():
    """Create a mock MS Graph event object."""
    mock_event = MagicMock()
    mock_event.id = "test-event-id"
    mock_event.subject = "Test Event"
    mock_event.start = {'dateTime': '2025-06-01T09:00:00Z', 'timeZone': 'UTC'}
    mock_event.end = {'dateTime': '2025-06-01T10:00:00Z', 'timeZone': 'UTC'}
    mock_event.body = {'content': 'Test event body'}
    mock_event.location = {'displayName': 'Test Location'}
    mock_event.is_all_day = False
    mock_event.show_as = 'busy'
    mock_event.sensitivity = 'normal'
    return mock_event


@pytest.fixture
def sample_appointments_data():
    """Sample appointment data for testing."""
    return [
        {
            'subject': 'Meeting 1',
            'start_time': datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
            'end_time': datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
        },
        {
            'subject': 'Meeting 2',
            'start_time': datetime(2025, 6, 1, 11, 0, tzinfo=UTC),
            'end_time': datetime(2025, 6, 1, 12, 0, tzinfo=UTC),
        },
        {
            'subject': 'Overlapping Meeting',
            'start_time': datetime(2025, 6, 1, 9, 30, tzinfo=UTC),
            'end_time': datetime(2025, 6, 1, 10, 30, tzinfo=UTC),
        }
    ]


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Setup logging for tests."""
    import logging
    logging.getLogger().setLevel(logging.DEBUG)


@pytest.fixture(autouse=True, scope="function")
def comprehensive_test_cleanup():
    """Comprehensive cleanup after each test to prevent memory accumulation."""
    import gc
    import threading
    import time
    import sys
    from unittest.mock import patch

    # Store initial state for comparison
    initial_thread_count = threading.active_count()

    # Track memory before test (if psutil available)
    memory_before = None
    try:
        import psutil
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
    except ImportError:
        pass

    yield

    try:
        # 1. Shutdown AsyncRunner with more aggressive cleanup
        from core.utilities.async_runner import shutdown_global_runner
        shutdown_global_runner()

        # 2. Clear SQLAlchemy session registry
        from core.db import SessionLocal
        if hasattr(SessionLocal, 'remove'):
            SessionLocal.remove()

        # 3. Clean up database resources
        from .utils.database_cleanup import cleanup_database_resources
        cleanup_database_resources()

        # 4. Wait for background threads to actually terminate with increased timeout
        max_wait = 3.0  # Increased timeout
        wait_interval = 0.1
        waited = 0.0

        while threading.active_count() > initial_thread_count and waited < max_wait:
            time.sleep(wait_interval)
            waited += wait_interval
            # Force GC during wait to help with thread cleanup
            if waited % 0.5 < 0.001:  # Every ~0.5 seconds
                gc.collect()

        # 5. Force garbage collection multiple times with different generations
        for i in range(3):
            gc.collect(i)  # Collect specific generation

        # 6. Clear any remaining mock patches
        patch.stopall()

        # 7. Clear any module-level caches that might hold references
        sys.modules.get('core.utilities.async_runner', {}).clear()

        # 8. Log warning if threads are still active
        final_thread_count = threading.active_count()
        if final_thread_count > initial_thread_count:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Thread count increased from {initial_thread_count} to {final_thread_count} "
                f"after test cleanup. Potential thread leak."
            )

            # Log active thread names to help with debugging
            active_threads = threading.enumerate()
            thread_names = [t.name for t in active_threads]
            logger.warning(f"Active threads: {thread_names}")

        # 9. Check memory after cleanup if we tracked it before
        if memory_before is not None:
            try:
                import psutil
                process = psutil.Process()
                memory_after = process.memory_info().rss / 1024 / 1024  # MB
                memory_diff = memory_after - memory_before

                # Log significant memory increases
                if memory_diff > 10:  # More than 10MB increase
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Memory increased by {memory_diff:.1f}MB after test cleanup "
                        f"(before: {memory_before:.1f}MB, after: {memory_after:.1f}MB)"
                    )
            except Exception:
                pass

    except Exception as e:
        # Don't let cleanup failures break tests, but log them
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error during comprehensive test cleanup: {e}")


@pytest.fixture(autouse=True, scope="function")
def memory_monitor():
    """Monitor memory usage during tests and warn about excessive growth."""
    try:
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        yield

        # Check memory after test
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Warn if memory increased significantly (>50MB per test)
        if memory_increase > 50:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"High memory increase detected: {memory_increase:.1f} MB "
                f"(from {initial_memory:.1f} to {final_memory:.1f} MB)"
            )

    except ImportError:
        # psutil not available, skip monitoring
        yield


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        yield f.name
    os.unlink(f.name)
