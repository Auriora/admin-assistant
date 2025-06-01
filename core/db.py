import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

# Determine DB URL from environment or default to dev SQLite
CORE_DATABASE_URL = os.getenv(
    "CORE_DATABASE_URL", "sqlite:///instance/admin_assistant_core_dev.db"
)

engine = create_engine(CORE_DATABASE_URL, echo=False, future=True)
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False)
)
Base = declarative_base()


def get_session():
    """
    Returns a new SQLAlchemy session using SessionLocal.
    """
    return SessionLocal()
