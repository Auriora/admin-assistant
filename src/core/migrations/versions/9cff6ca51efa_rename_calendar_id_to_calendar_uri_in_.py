"""Rename calendar_id to calendar_uri in archive_configuration

Revision ID: 9cff6ca51efa
Revises: 2900fa9252a5
Create Date: 2025-05-30 18:41:39.824291

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9cff6ca51efa"
down_revision: Union[str, None] = "2900fa9252a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("archive_configurations") as batch_op:
        batch_op.alter_column(
            "source_calendar_id", new_column_name="source_calendar_uri"
        )
        batch_op.alter_column(
            "destination_calendar_id", new_column_name="destination_calendar_uri"
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("archive_configurations") as batch_op:
        batch_op.alter_column(
            "source_calendar_uri", new_column_name="source_calendar_id"
        )
        batch_op.alter_column(
            "destination_calendar_uri", new_column_name="destination_calendar_id"
        )
