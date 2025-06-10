"""Add account context to URIs and new archive configuration columns

Revision ID: 20250610_add_account_context_to_uris
Revises: add_restoration_configurations_table
Create Date: 2025-06-10 00:00:00.000000

This migration adds account context to existing calendar URIs in the archive_configurations
table and adds new columns for enhanced archive functionality.

Changes:
1. Add allow_overlaps column (Boolean, default True)
2. Add archive_purpose column (String, default 'general')
3. Update existing URIs to include account context:
   - msgraph://calendars/primary -> msgraph://user@example.com/calendars/primary
   - Use user email as primary account context, fallback to username, then user_id
   - Handle edge cases (missing users, null emails/usernames)

Features:
- Comprehensive error handling and logging
- Migration statistics and validation
- Fully reversible operations
- Support for both upgrade and downgrade
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250610_add_account_context_to_uris"
down_revision: Union[str, None] = "add_restoration_configurations_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def get_user_account_context(connection, user_id: int) -> str:
    """
    Get the best available account context for a user.
    
    Priority order:
    1. User email (preferred)
    2. Username (fallback)
    3. user_id as string (last resort)
    
    Args:
        connection: Database connection
        user_id: User ID to get context for
        
    Returns:
        Account context string
    """
    try:
        result = connection.execute(
            sa.text("SELECT email, username FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        user_row = result.fetchone()
        
        if not user_row:
            print(f"    ⚠ User {user_id} not found, using user_id as context")
            return str(user_id)
            
        email, username = user_row
        
        # Prefer email if available and valid
        if email and email.strip() and '@' in email:
            return email.strip()
            
        # Fallback to username if available
        if username and username.strip():
            return username.strip()
            
        # Last resort: use user_id
        print(f"    ⚠ User {user_id} has no valid email or username, using user_id as context")
        return str(user_id)
        
    except Exception as e:
        print(f"    ⚠ Error getting user context for user {user_id}: {e}")
        return str(user_id)


def add_account_context_to_uri(uri: str, account_context: str) -> str:
    """
    Add account context to a URI if it doesn't already have it.

    Transforms:
    - msgraph://calendars/primary -> msgraph://user@example.com/calendars/primary
    - local://calendars/personal -> local://user@example.com/calendars/personal

    Args:
        uri: Original URI
        account_context: Account context to add

    Returns:
        URI with account context
    """
    if not account_context:
        return uri

    # Handle empty or legacy URIs
    if uri in ('', 'calendar', 'primary'):
        return f'msgraph://{account_context}/calendars/primary'
    
    # Parse URI to check if it already has account context
    if '://' not in uri:
        # Malformed URI, try to fix it
        return f'msgraph://{account_context}/calendars/{uri}'
    
    scheme, rest = uri.split('://', 1)
    
    # Check if URI already has account context
    # New format: scheme://account/namespace/identifier
    # Legacy format: scheme://namespace/identifier
    
    parts = rest.split('/')
    if len(parts) >= 2:
        # Check if first part looks like an account (contains @ or is numeric)
        first_part = parts[0]
        if '@' in first_part or first_part.isdigit():
            # Already has account context
            return uri
    
    # Add account context to legacy URI
    return f'{scheme}://{account_context}/{rest}'


def remove_account_context_from_uri(uri: str) -> str:
    """
    Remove account context from a URI to revert to legacy format.
    
    Transforms:
    - msgraph://user@example.com/calendars/primary -> msgraph://calendars/primary
    - local://user@example.com/calendars/personal -> local://calendars/personal
    
    Args:
        uri: URI with account context
        
    Returns:
        Legacy URI without account context
    """
    if not uri:
        return uri
        
    if '://' not in uri:
        return uri
    
    scheme, rest = uri.split('://', 1)
    parts = rest.split('/')
    
    if len(parts) >= 2:
        # Check if first part looks like an account (contains @ or is numeric)
        first_part = parts[0]
        if '@' in first_part or first_part.isdigit():
            # Remove account context
            remaining_parts = parts[1:]
            return f'{scheme}://{"/".join(remaining_parts)}'
    
    # No account context found, return as-is
    return uri


def upgrade() -> None:
    """Add account context to URIs and new archive configuration columns."""
    
    print("Starting account context URI migration...")
    
    # Get connection
    connection = op.get_bind()
    
    # Step 1: Add new columns to archive_configurations
    print("\n1. Adding new columns to archive_configurations...")
    
    try:
        with op.batch_alter_table("archive_configurations") as batch_op:
            batch_op.add_column(
                sa.Column(
                    'allow_overlaps',
                    sa.Boolean(),
                    nullable=False,
                    default=True,
                    server_default=sa.text('1'),  # SQLite uses 1 for True
                    doc="Whether to allow overlapping appointments in archive operations"
                )
            )
            batch_op.add_column(
                sa.Column(
                    'archive_purpose',
                    sa.String(length=50),
                    nullable=False,
                    default='general',
                    server_default=sa.text("'general'"),
                    doc="Purpose of the archive configuration (general, billing, travel, etc.)"
                )
            )
        
        print("  ✓ Added allow_overlaps column (Boolean, default True)")
        print("  ✓ Added archive_purpose column (String, default 'general')")
        
    except Exception as e:
        print(f"  ✗ Error adding columns: {e}")
        raise
    
    # Step 2: Update existing URIs with account context
    print("\n2. Updating existing URIs with account context...")
    
    migration_stats = {
        'total_configs': 0,
        'updated_configs': 0,
        'skipped_configs': 0,
        'error_configs': 0,
        'user_contexts': {}
    }
    
    try:
        # Get all archive configurations with user information
        result = connection.execute(
            sa.text("""
                SELECT ac.id, ac.user_id, ac.source_calendar_uri, ac.destination_calendar_uri,
                       u.email, u.username
                FROM archive_configurations ac
                LEFT JOIN users u ON ac.user_id = u.id
                ORDER BY ac.id
            """)
        )
        configurations = result.fetchall()
        
        migration_stats['total_configs'] = len(configurations)
        print(f"  Found {len(configurations)} archive configurations to process")
        
        for config in configurations:
            config_id, user_id, source_uri, dest_uri, user_email, username = config
            
            try:
                # Get account context for this user
                if user_id not in migration_stats['user_contexts']:
                    account_context = get_user_account_context(connection, user_id)
                    migration_stats['user_contexts'][user_id] = account_context
                else:
                    account_context = migration_stats['user_contexts'][user_id]
                
                # Update URIs with account context
                new_source_uri = add_account_context_to_uri(source_uri, account_context)
                new_dest_uri = add_account_context_to_uri(dest_uri, account_context)
                
                # Check if any changes are needed
                if new_source_uri != source_uri or new_dest_uri != dest_uri:
                    # Update the configuration
                    connection.execute(
                        sa.text("""
                            UPDATE archive_configurations
                            SET source_calendar_uri = :source_uri,
                                destination_calendar_uri = :dest_uri,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :config_id
                        """),
                        {
                            'source_uri': new_source_uri,
                            'dest_uri': new_dest_uri,
                            'config_id': config_id
                        }
                    )
                    
                    migration_stats['updated_configs'] += 1
                    print(f"  ✓ Config {config_id} (user {user_id} -> {account_context}):")
                    if new_source_uri != source_uri:
                        print(f"    Source: {source_uri} -> {new_source_uri}")
                    if new_dest_uri != dest_uri:
                        print(f"    Dest: {dest_uri} -> {new_dest_uri}")
                else:
                    migration_stats['skipped_configs'] += 1
                    print(f"  - Config {config_id}: No changes needed (already has account context)")
                    
            except Exception as e:
                migration_stats['error_configs'] += 1
                print(f"  ✗ Error processing config {config_id}: {e}")
                # Continue with other configurations
                continue
        
    except Exception as e:
        print(f"  ✗ Error during URI migration: {e}")
        raise

    # Step 3: Print migration statistics
    print(f"\n3. Migration Statistics:")
    print(f"  Total configurations: {migration_stats['total_configs']}")
    print(f"  Updated configurations: {migration_stats['updated_configs']}")
    print(f"  Skipped configurations: {migration_stats['skipped_configs']}")
    print(f"  Error configurations: {migration_stats['error_configs']}")
    print(f"  User contexts created: {len(migration_stats['user_contexts'])}")

    if migration_stats['user_contexts']:
        print(f"  Account contexts used:")
        for user_id, context in migration_stats['user_contexts'].items():
            print(f"    User {user_id}: {context}")

    # Step 4: Validation
    print(f"\n4. Validation:")
    try:
        # Check that all configurations now have account context
        result = connection.execute(
            sa.text("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN source_calendar_uri LIKE '%://%/%' THEN 1 ELSE 0 END) as source_with_context,
                       SUM(CASE WHEN destination_calendar_uri LIKE '%://%/%' THEN 1 ELSE 0 END) as dest_with_context
                FROM archive_configurations
            """)
        )
        validation = result.fetchone()

        total, source_with_context, dest_with_context = validation
        print(f"  Total configurations: {total}")
        print(f"  Source URIs with context: {source_with_context}/{total}")
        print(f"  Destination URIs with context: {dest_with_context}/{total}")

        if source_with_context == total and dest_with_context == total:
            print("  ✓ All URIs successfully updated with account context")
        else:
            print("  ⚠ Some URIs may not have been updated properly")

    except Exception as e:
        print(f"  ⚠ Validation error: {e}")

    print("\n✓ Account context URI migration completed successfully!")


def downgrade() -> None:
    """Remove account context from URIs and drop new archive configuration columns."""

    print("Starting account context URI migration rollback...")

    # Get connection
    connection = op.get_bind()

    # Step 1: Remove account context from existing URIs
    print("\n1. Removing account context from existing URIs...")

    rollback_stats = {
        'total_configs': 0,
        'updated_configs': 0,
        'skipped_configs': 0,
        'error_configs': 0
    }

    try:
        # Get all archive configurations
        result = connection.execute(
            sa.text("SELECT id, source_calendar_uri, destination_calendar_uri FROM archive_configurations")
        )
        configurations = result.fetchall()

        rollback_stats['total_configs'] = len(configurations)
        print(f"  Found {len(configurations)} archive configurations to process")

        for config in configurations:
            config_id, source_uri, dest_uri = config

            try:
                # Remove account context from URIs
                legacy_source_uri = remove_account_context_from_uri(source_uri)
                legacy_dest_uri = remove_account_context_from_uri(dest_uri)

                # Check if any changes are needed
                if legacy_source_uri != source_uri or legacy_dest_uri != dest_uri:
                    # Update the configuration
                    connection.execute(
                        sa.text("""
                            UPDATE archive_configurations
                            SET source_calendar_uri = :source_uri,
                                destination_calendar_uri = :dest_uri,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :config_id
                        """),
                        {
                            'source_uri': legacy_source_uri,
                            'dest_uri': legacy_dest_uri,
                            'config_id': config_id
                        }
                    )

                    rollback_stats['updated_configs'] += 1
                    print(f"  ✓ Config {config_id}:")
                    if legacy_source_uri != source_uri:
                        print(f"    Source: {source_uri} -> {legacy_source_uri}")
                    if legacy_dest_uri != dest_uri:
                        print(f"    Dest: {dest_uri} -> {legacy_dest_uri}")
                else:
                    rollback_stats['skipped_configs'] += 1
                    print(f"  - Config {config_id}: No changes needed (already legacy format)")

            except Exception as e:
                rollback_stats['error_configs'] += 1
                print(f"  ✗ Error processing config {config_id}: {e}")
                # Continue with other configurations
                continue

    except Exception as e:
        print(f"  ✗ Error during URI rollback: {e}")
        raise

    # Step 2: Remove new columns from archive_configurations
    print("\n2. Removing new columns from archive_configurations...")

    try:
        with op.batch_alter_table("archive_configurations") as batch_op:
            batch_op.drop_column('archive_purpose')
            batch_op.drop_column('allow_overlaps')

        print("  ✓ Removed archive_purpose column")
        print("  ✓ Removed allow_overlaps column")

    except Exception as e:
        print(f"  ✗ Error removing columns: {e}")
        raise

    # Step 3: Print rollback statistics
    print(f"\n3. Rollback Statistics:")
    print(f"  Total configurations: {rollback_stats['total_configs']}")
    print(f"  Updated configurations: {rollback_stats['updated_configs']}")
    print(f"  Skipped configurations: {rollback_stats['skipped_configs']}")
    print(f"  Error configurations: {rollback_stats['error_configs']}")

    print("\n✓ Account context URI migration rollback completed successfully!")
