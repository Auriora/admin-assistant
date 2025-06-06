"""Add backup configurations table

Revision ID: d0c8b7242357
Revises: cddd73b7a59a
Create Date: 2025-06-06 08:39:40.441285

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0c8b7242357'
down_revision: Union[str, None] = 'cddd73b7a59a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add backup configurations table."""
    op.create_table('backup_configurations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('source_calendar_uri', sa.String(length=500), nullable=False),
    sa.Column('destination_uri', sa.String(length=500), nullable=False),
    sa.Column('backup_format', sa.String(length=32), nullable=False),
    sa.Column('include_metadata', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('timezone', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backup_configurations_user_id'), 'backup_configurations', ['user_id'], unique=False)


def downgrade() -> None:
    """Remove backup configurations table."""
    op.drop_index(op.f('ix_backup_configurations_user_id'), table_name='backup_configurations')
    op.drop_table('backup_configurations')
