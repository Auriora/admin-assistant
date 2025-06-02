"""empty message

Revision ID: 3678d6cf30af
Revises: 5bc75ccb8ad8
Create Date: 2025-06-02 19:41:18.471614

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3678d6cf30af'
down_revision: Union[str, None] = '5bc75ccb8ad8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite doesn't support ALTER COLUMN to change nullability
    # First, update any NULL values to False (the default)
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE appointments SET is_archived = 0 WHERE is_archived IS NULL"))

    # For SQLite, we need to recreate the table to change column constraints
    # Since this is a simple constraint change and we've handled NULL values,
    # we can use a batch operation which Alembic handles for SQLite
    with op.batch_alter_table('appointments', schema=None) as batch_op:
        batch_op.alter_column('is_archived',
                   existing_type=sa.BOOLEAN(),
                   nullable=False,
                   existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert the column back to nullable
    with op.batch_alter_table('appointments', schema=None) as batch_op:
        batch_op.alter_column('is_archived',
                   existing_type=sa.BOOLEAN(),
                   nullable=True,
                   existing_nullable=False)
