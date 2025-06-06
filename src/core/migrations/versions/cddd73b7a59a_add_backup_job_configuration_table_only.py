"""Add backup job configuration table only

Revision ID: cddd73b7a59a
Revises: 59bbcf7684b2
Create Date: 2025-06-06 08:21:28.221335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cddd73b7a59a'
down_revision: Union[str, None] = 'add_restoration_configurations_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add backup job configuration table."""
    op.create_table('backup_job_configurations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('source_calendar_name', sa.String(length=255), nullable=False),
    sa.Column('backup_destination', sa.String(length=500), nullable=False),
    sa.Column('backup_format', sa.String(length=32), nullable=False),
    sa.Column('schedule_type', sa.String(length=16), nullable=False),
    sa.Column('schedule_hour', sa.Integer(), nullable=False),
    sa.Column('schedule_minute', sa.Integer(), nullable=False),
    sa.Column('schedule_day_of_week', sa.Integer(), nullable=True),
    sa.Column('include_metadata', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backup_job_configurations_user_id'), 'backup_job_configurations', ['user_id'], unique=False)


def downgrade() -> None:
    """Remove backup job configuration table."""
    op.drop_index(op.f('ix_backup_job_configurations_user_id'), table_name='backup_job_configurations')
    op.drop_table('backup_job_configurations')
