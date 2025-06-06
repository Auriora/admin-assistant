"""Add restoration_configurations table

Revision ID: add_restoration_configurations_table
Revises: migrate_calendar_uris_user_friendly
Create Date: 2025-01-27 15:00:00.000000

This migration adds the restoration_configurations table to support the new
generic appointment restoration feature. The table stores configurations for
restoring appointments from various sources (audit logs, backup calendars,
export files) to various destinations (local calendars, MSGraph calendars,
export files).

Features:
- Configurable source and destination types
- JSON-based configuration storage for flexibility
- User-specific restoration policies
- Support for multiple restoration strategies
- Audit logging integration
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.types import JSON

# revision identifiers, used by Alembic.
revision: str = "add_restoration_configurations_table"
down_revision: Union[str, None] = "migrate_calendar_uris_user_friendly"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add restoration_configurations table."""
    print("Creating restoration_configurations table...")

    # Create the restoration_configurations table with foreign key included
    op.create_table(
        'restoration_configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'user_id',
            sa.Integer(),
            nullable=False,
            doc="User this configuration belongs to"
        ),
        sa.Column(
            'name',
            sa.String(length=100),
            nullable=False,
            doc="Human-readable name for this restoration configuration"
        ),
        sa.Column(
            'description',
            sa.Text(),
            nullable=True,
            doc="Optional description of the restoration configuration"
        ),
        sa.Column(
            'source_type',
            sa.String(length=50),
            nullable=False,
            doc="Type of restoration source (audit_log, backup_calendar, export_file)"
        ),
        sa.Column(
            'source_config',
            JSON(),
            nullable=False,
            doc="Source-specific configuration (calendar IDs, file paths, audit log filters, etc.)"
        ),
        sa.Column(
            'destination_type',
            sa.String(length=50),
            nullable=False,
            doc="Type of restoration destination (local_calendar, msgraph_calendar, export_file)"
        ),
        sa.Column(
            'destination_config',
            JSON(),
            nullable=False,
            doc="Destination-specific configuration (calendar names, file formats, etc.)"
        ),
        sa.Column(
            'restoration_policy',
            JSON(),
            nullable=True,
            doc="Policies for restoration (conflict resolution, date ranges, duplicate handling, etc.)"
        ),
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            default=True,
            doc="Whether this configuration is active"
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP')
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP')
        ),
        sa.PrimaryKeyConstraint('id'),
        # Include foreign key constraint in table creation for SQLite compatibility
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name='fk_restoration_configurations_user_id',
            ondelete='CASCADE'
        )
    )

    # Create indexes for better query performance
    op.create_index(
        'ix_restoration_configurations_user_id',
        'restoration_configurations',
        ['user_id']
    )
    op.create_index(
        'ix_restoration_configurations_source_type',
        'restoration_configurations',
        ['source_type']
    )
    op.create_index(
        'ix_restoration_configurations_destination_type',
        'restoration_configurations',
        ['destination_type']
    )
    op.create_index(
        'ix_restoration_configurations_is_active',
        'restoration_configurations',
        ['is_active']
    )
    op.create_index(
        'ix_restoration_configurations_user_active',
        'restoration_configurations',
        ['user_id', 'is_active']
    )
    
    print("✓ restoration_configurations table created successfully")
    
    # Insert sample configurations for testing (optional)
    print("Creating sample restoration configurations...")
    
    # Get connection for data insertion
    connection = op.get_bind()
    
    try:
        # Check if we have any users to create sample configurations for
        result = connection.execute(sa.text("SELECT id FROM users LIMIT 1"))
        user_row = result.fetchone()
        
        if user_row:
            user_id = user_row[0]
            
            # Sample configuration 1: Audit log to local calendar
            connection.execute(sa.text("""
                INSERT INTO restoration_configurations 
                (user_id, name, description, source_type, source_config, destination_type, destination_config, restoration_policy, is_active)
                VALUES 
                (:user_id, :name1, :desc1, :source_type1, :source_config1, :dest_type1, :dest_config1, :policy1, :active1)
            """), {
                'user_id': user_id,
                'name1': 'Audit Log Recovery',
                'desc1': 'Restore failed appointments from audit logs to Recovered calendar',
                'source_type1': 'audit_log',
                'source_config1': '{"action_types": ["archive", "restore"], "date_range": {"start": "2025-05-29", "end": "2025-12-31"}, "status": "failure"}',
                'dest_type1': 'local_calendar',
                'dest_config1': '{"calendar_name": "Recovered"}',
                'policy1': '{"skip_duplicates": true, "date_range": {"start": "2025-05-29", "end": "2025-12-31"}}',
                'active1': True
            })
            
            # Sample configuration 2: Backup calendar to MSGraph
            connection.execute(sa.text("""
                INSERT INTO restoration_configurations 
                (user_id, name, description, source_type, source_config, destination_type, destination_config, restoration_policy, is_active)
                VALUES 
                (:user_id, :name2, :desc2, :source_type2, :source_config2, :dest_type2, :dest_config2, :policy2, :active2)
            """), {
                'user_id': user_id,
                'name2': 'Backup to MSGraph',
                'desc2': 'Restore appointments from backup calendars to MSGraph Recovery calendar',
                'source_type2': 'backup_calendar',
                'source_config2': '{"calendar_names": ["Recovered", "Recovered Missing"], "date_range": {}}',
                'dest_type2': 'msgraph_calendar',
                'dest_config2': '{"calendar_name": "MSGraph Recovery"}',
                'policy2': '{"skip_duplicates": true}',
                'active2': True
            })
            
            # Sample configuration 3: Export file to local calendar (inactive)
            connection.execute(sa.text("""
                INSERT INTO restoration_configurations 
                (user_id, name, description, source_type, source_config, destination_type, destination_config, restoration_policy, is_active)
                VALUES 
                (:user_id, :name3, :desc3, :source_type3, :source_config3, :dest_type3, :dest_config3, :policy3, :active3)
            """), {
                'user_id': user_id,
                'name3': 'Import from CSV',
                'desc3': 'Import appointments from CSV export file',
                'source_type3': 'export_file',
                'source_config3': '{"file_path": "/path/to/backup.csv", "file_format": "csv"}',
                'dest_type3': 'local_calendar',
                'dest_config3': '{"calendar_name": "Imported"}',
                'policy3': '{"skip_duplicates": true, "subject_filters": {"exclude": ["test", "debug"]}}',
                'active3': False
            })
            
            print(f"✓ Created 3 sample restoration configurations for user {user_id}")
        else:
            print("⚠ No users found - skipping sample configuration creation")
            
    except Exception as e:
        print(f"⚠ Could not create sample configurations: {e}")
        # Don't fail the migration if sample data creation fails
        pass
    
    print("✓ Restoration configurations migration completed successfully")


def downgrade() -> None:
    """Remove restoration_configurations table."""
    print("Removing restoration_configurations table...")

    # Drop indexes first
    op.drop_index('ix_restoration_configurations_user_active', table_name='restoration_configurations')
    op.drop_index('ix_restoration_configurations_is_active', table_name='restoration_configurations')
    op.drop_index('ix_restoration_configurations_destination_type', table_name='restoration_configurations')
    op.drop_index('ix_restoration_configurations_source_type', table_name='restoration_configurations')
    op.drop_index('ix_restoration_configurations_user_id', table_name='restoration_configurations')

    # Drop the table (foreign key constraint will be dropped automatically with the table in SQLite)
    op.drop_table('restoration_configurations')

    print("✓ restoration_configurations table removed successfully")
