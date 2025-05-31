"""Add is_archived column to appointments table

Revision ID: add_is_archived_column
Revises: f44e88f7e0bc
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_is_archived_column'
down_revision = 'f44e88f7e0bc'
branch_labels = None
depends_on = None


def upgrade():
    """Add is_archived column to appointments table."""
    # Add the column as nullable with default False
    # SQLite doesn't support adding NOT NULL columns with defaults easily
    op.add_column('appointments', sa.Column('is_archived', sa.Boolean(), nullable=True, default=False))

    # Update existing records to have is_archived = False
    op.execute("UPDATE appointments SET is_archived = 0 WHERE is_archived IS NULL")


def downgrade():
    """Remove is_archived column from appointments table."""
    op.drop_column('appointments', 'is_archived')
