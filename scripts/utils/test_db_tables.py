#!/usr/bin/env python3
"""
Utility script to create all DB tables and perform a simple smoke test
outside of the pytest framework. Intended for manual verification.
"""
import os
import sys
from typing import List

# Ensure src/ is importable when executed from scripts/utils/
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Set test environment (in-memory DBs)
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CORE_DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import inspect  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from core.db import Base, engine  # type: ignore
# Import models to ensure metadata is populated
from core.models.user import User  # type: ignore
from core.models.appointment import Appointment  # type: ignore
from core.models.location import Location  # type: ignore
from core.models.category import Category  # type: ignore
from core.models.calendar import Calendar  # type: ignore
from core.models.archive_configuration import ArchiveConfiguration  # type: ignore
from core.models.action_log import ActionLog  # type: ignore
from core.models.audit_log import AuditLog  # type: ignore
from core.models.chat_session import ChatSession  # type: ignore
from core.models.entity_association import EntityAssociation  # type: ignore
from core.models.job_configuration import JobConfiguration  # type: ignore
from core.models.prompt import Prompt  # type: ignore
from core.models.timesheet import Timesheet  # type: ignore
from core.models.backup_job_configuration import BackupJobConfiguration  # type: ignore
from core.models.backup_configuration import BackupConfiguration  # type: ignore
from core.models.restoration_configuration import RestorationConfiguration  # type: ignore
from core.models.reversible_operation import (  # type: ignore
    ReversibleOperation,
    ReversibleOperationItem,
)


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


def main() -> int:
    # Create all tables
    Base.metadata.create_all(engine)

    # Check tables exist
    inspector = inspect(engine)
    tables: List[str] = inspector.get_table_names()
    print(f"Tables in database: {tables}")

    expected_tables = {model.__tablename__ for model in MODEL_CLASSES}
    missing_tables = sorted(expected_tables - set(tables))
    if missing_tables:
        print(f"Missing tables: {missing_tables}")
        return 1

    # Simple user round-trip
    with Session(engine) as session:
        user = User(email="test@example.com", name="Test User")
        session.add(user)
        session.commit()

        queried_user = session.query(User).filter_by(email="test@example.com").first()
        if queried_user:
            print(f"User created and queried successfully: {queried_user.name}")
        else:
            print("Failed to query user!")
            return 1

    print("All tests passed!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
