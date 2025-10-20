import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

# Ensure all models are imported so metadata is populated
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


MODEL_CLASSES = (
    User,
    Appointment,
    Location,
    Category,
    Calendar,
    ArchiveConfiguration,
    ActionLog,
    AuditLog,
    ChatSession,
    EntityAssociation,
    JobConfiguration,
    Prompt,
    Timesheet,
    BackupJobConfiguration,
    BackupConfiguration,
    RestorationConfiguration,
    ReversibleOperation,
    ReversibleOperationItem,
)


@pytest.mark.integration
def test_tables_exist_and_user_roundtrip(test_db_engine):
    # Create all tables for the shared in-memory test database
    Base.metadata.create_all(test_db_engine)

    inspector = inspect(test_db_engine)
    tables = set(inspector.get_table_names())

    expected_tables = {model.__tablename__ for model in MODEL_CLASSES}
    missing_tables = sorted(expected_tables - tables)
    assert not missing_tables, f"Missing tables: {missing_tables}"

    # Simple user round-trip using the same engine
    with Session(test_db_engine) as session:
        user = User(email="db_tables_user@example.com", name="Test User")
        session.add(user)
        session.commit()

        queried = session.query(User).filter_by(email="db_tables_user@example.com").first()
        assert queried is not None, "Failed to query user after insert"
