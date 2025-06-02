"""Merge username and job_configurations migrations

Revision ID: 5bc75ccb8ad8
Revises: add_username_to_users, e0f6efc3e8c1
Create Date: 2025-06-02 15:30:22.907934

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5bc75ccb8ad8"
down_revision: Union[str, None] = ("add_username_to_users", "e0f6efc3e8c1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
