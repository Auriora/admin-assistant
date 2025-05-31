"""Add audit_log table for comprehensive audit logging

Revision ID: add_audit_log_table
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_audit_log_table'
down_revision = None  # Update this to the latest revision
branch_labels = None
depends_on = None


def upgrade():
    """Create the audit_log table."""
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=64), nullable=False),
        sa.Column('operation', sa.String(length=128), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=True),
        sa.Column('resource_id', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('request_data', sa.JSON(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('correlation_id', sa.String(length=128), nullable=True),
        sa.Column('parent_audit_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['parent_audit_id'], ['audit_log.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index('ix_audit_log_user_id', 'audit_log', ['user_id'])
    op.create_index('ix_audit_log_action_type', 'audit_log', ['action_type'])
    op.create_index('ix_audit_log_operation', 'audit_log', ['operation'])
    op.create_index('ix_audit_log_status', 'audit_log', ['status'])
    op.create_index('ix_audit_log_resource_type', 'audit_log', ['resource_type'])
    op.create_index('ix_audit_log_correlation_id', 'audit_log', ['correlation_id'])
    op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])
    
    # Composite indexes for common query patterns
    op.create_index('ix_audit_log_user_action_type', 'audit_log', ['user_id', 'action_type'])
    op.create_index('ix_audit_log_user_created_at', 'audit_log', ['user_id', 'created_at'])


def downgrade():
    """Drop the audit_log table."""
    op.drop_index('ix_audit_log_user_created_at', table_name='audit_log')
    op.drop_index('ix_audit_log_user_action_type', table_name='audit_log')
    op.drop_index('ix_audit_log_created_at', table_name='audit_log')
    op.drop_index('ix_audit_log_correlation_id', table_name='audit_log')
    op.drop_index('ix_audit_log_resource_type', table_name='audit_log')
    op.drop_index('ix_audit_log_status', table_name='audit_log')
    op.drop_index('ix_audit_log_operation', table_name='audit_log')
    op.drop_index('ix_audit_log_action_type', table_name='audit_log')
    op.drop_index('ix_audit_log_user_id', table_name='audit_log')
    op.drop_table('audit_log')
