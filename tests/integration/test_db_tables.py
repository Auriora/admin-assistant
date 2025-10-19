import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

# Ensure all models are imported so metadata is populated
from core.db import Base
from core.models.user import User
from core.models.appointment import Appointment  # noqa: F401
from core.models.location import Location  # noqa: F401
from core.models.category import Category  # noqa: F401
from core.models.calendar import Calendar  # noqa: F401
from core.models.archive_configuration import ArchiveConfiguration  # noqa: F401
from core.models.action_log import ActionLog  # noqa: F401
from core.models.audit_log import AuditLog  # noqa: F401
from core.models.chat_session import ChatSession  # noqa: F401
from core.models.entity_association import EntityAssociation  # noqa: F401
from core.models.job_configuration import JobConfiguration  # noqa: F401
from core.models.prompt import Prompt  # noqa: F401
from core.models.timesheet import Timesheet  # noqa: F401
from core.models.backup_job_configuration import BackupJobConfiguration  # noqa: F401
from core.models.backup_configuration import BackupConfiguration  # noqa: F401
from core.models.restoration_configuration import RestorationConfiguration  # noqa: F401
from core.models.reversible_operation import ReversibleOperation, ReversibleOperationItem  # noqa: F401


@pytest.mark.integration
def test_tables_exist_and_user_roundtrip(test_db_engine):
    # Create all tables for the shared in-memory test database
    Base.metadata.create_all(test_db_engine)

    inspector = inspect(test_db_engine)
    tables = inspector.get_table_names()
    assert "users" in tables, "Users table does not exist!"

    # Simple user round-trip using the same engine
    with Session(test_db_engine) as session:
        user = User(email="test@example.com", name="Test User")
        session.add(user)
        session.commit()

        queried = session.query(User).filter_by(email="test@example.com").first()
        assert queried is not None, "Failed to query user after insert"
