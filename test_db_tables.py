import os
import sys
from sqlalchemy import inspect

# Set test environment
os.environ['APP_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CORE_DATABASE_URL'] = 'sqlite:///:memory:'

# Import all models to ensure they're registered with Base.metadata
from core.db import Base, engine
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

# Create all tables
Base.metadata.create_all(engine)

# Check if the users table exists
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Tables in database: {tables}")

if "users" in tables:
    print("Users table exists!")
else:
    print("Users table does not exist!")
    sys.exit(1)

# Try to create a user
from sqlalchemy.orm import Session
with Session(engine) as session:
    user = User(email="test@example.com", name="Test User")
    session.add(user)
    session.commit()
    
    # Query the user
    queried_user = session.query(User).filter_by(email="test@example.com").first()
    if queried_user:
        print(f"User created and queried successfully: {queried_user.name}")
    else:
        print("Failed to query user!")
        sys.exit(1)

print("All tests passed!")