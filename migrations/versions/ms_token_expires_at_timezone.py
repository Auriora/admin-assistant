"""Make ms_token_expires_at timezone aware

Revision ID: ms_token_expires_at_timezone
Revises: 2ee69b0d98e4
Create Date: 2025-05-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ms_token_expires_at_timezone'
down_revision = '2ee69b0d98e4'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('ms_token_expires_at',
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=True)

def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('ms_token_expires_at',
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=True) 