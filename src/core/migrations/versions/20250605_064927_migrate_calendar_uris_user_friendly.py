"""Migrate calendar URIs to new user-friendly format with namespaces

Revision ID: migrate_calendar_uris_user_friendly
Revises: 3678d6cf30af
Create Date: 2025-01-27 12:00:00.000000

This migration updates existing calendar URIs from the legacy format to the new
user-friendly namespace-aware format:

Legacy formats:
- msgraph://activity-archive -> msgraph://calendars/"Activity Archive"
- msgraph://calendar -> msgraph://calendars/primary
- local://personal -> local://calendars/personal

The migration resolves actual calendar names from MS Graph to create proper
user-friendly URIs with appropriate quoting.
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "migrate_calendar_uris_user_friendly"
down_revision: Union[str, None] = "3678d6cf30af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def migrate_uri_to_user_friendly(uri: str, calendar_name_mapping: dict = None) -> str:
    """
    Migrate a legacy URI to the new user-friendly format.

    Args:
        uri: Legacy URI to migrate
        calendar_name_mapping: Optional mapping of legacy identifiers to actual calendar names

    Returns:
        User-friendly URI
    """
    if not uri:
        return uri

    # Handle special cases
    if uri in ('', 'calendar', 'primary'):
        return 'msgraph://calendars/primary'

    # Parse legacy format
    if uri.startswith('msgraph://'):
        identifier = uri[len('msgraph://'):]

        # Check if it's already in new format (has calendars namespace)
        if identifier.startswith('calendars/'):
            # Already in new format, just return as-is
            return uri

        if identifier == 'calendar':
            return 'msgraph://calendars/primary'

        # Try to resolve to actual calendar name if mapping provided
        if calendar_name_mapping and identifier in calendar_name_mapping:
            actual_name = calendar_name_mapping[identifier]
            # Use user-friendly formatting with quotes if needed
            if ' ' in actual_name or '"' in actual_name or "'" in actual_name:
                escaped_name = actual_name.replace('"', '\\"')
                return f'msgraph://calendars/"{escaped_name}"'
            else:
                return f'msgraph://calendars/{actual_name}'

        # Fallback to identifier as-is
        return f'msgraph://calendars/{identifier}'

    if uri.startswith('local://'):
        identifier = uri[len('local://'):]

        # Check if it's already in new format (has calendars namespace)
        if identifier.startswith('calendars/'):
            # Already in new format, just return as-is
            return uri

        return f'local://calendars/{identifier}'

    # If it doesn't match known patterns, assume it's already in new format
    return uri


def get_calendar_name_mapping(connection) -> dict:
    """
    Get mapping of legacy calendar identifiers to actual calendar names.

    This attempts to resolve legacy identifiers like 'activity-archive' to
    actual calendar names like 'Activity Archive' by querying available data.
    """
    mapping = {}

    try:
        # Try to get calendar names from the calendars table if it exists
        try:
            result = connection.execute(
                sa.text("SELECT name, ms_calendar_id FROM calendars WHERE name IS NOT NULL")
            )
            calendars = result.fetchall()

            for cal in calendars:
                name = cal[0]
                # Create legacy-style identifier from name
                import re
                legacy_id = name.lower().strip()
                legacy_id = re.sub(r"\s+", "-", legacy_id)
                legacy_id = re.sub(r"[^a-z0-9\-_]", "", legacy_id)

                if legacy_id:
                    mapping[legacy_id] = name

        except Exception:
            # calendars table might not exist or be accessible
            pass

        # Add known mappings for common cases
        known_mappings = {
            'activity-archive': 'Activity Archive',
            'personal': 'Personal',
            'work': 'Work',
            'home': 'Home'
        }
        mapping.update(known_mappings)

    except Exception:
        # If anything fails, return empty mapping
        pass

    return mapping


def upgrade() -> None:
    """Migrate calendar URIs to new user-friendly format."""

    # Get connection
    connection = op.get_bind()

    print("Starting URI migration to user-friendly format...")

    # Get calendar name mapping for better resolution
    calendar_mapping = get_calendar_name_mapping(connection)
    if calendar_mapping:
        print(f"Found {len(calendar_mapping)} calendar name mappings")

    # Migrate archive_configurations table
    print("Migrating archive_configurations...")
    try:
        result = connection.execute(
            sa.text("SELECT id, source_calendar_uri, destination_calendar_uri FROM archive_configurations")
        )
        configurations = result.fetchall()

        for config in configurations:
            config_id = config[0]
            source_uri = config[1]
            dest_uri = config[2]

            # Migrate URIs using calendar name mapping
            new_source_uri = migrate_uri_to_user_friendly(source_uri, calendar_mapping)
            new_dest_uri = migrate_uri_to_user_friendly(dest_uri, calendar_mapping)

            # Update if changed
            if new_source_uri != source_uri or new_dest_uri != dest_uri:
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

                print(f"  Config {config_id}:")
                print(f"    Source: {source_uri} -> {new_source_uri}")
                print(f"    Dest: {dest_uri} -> {new_dest_uri}")
            else:
                print(f"  Config {config_id}: No changes needed")

    except Exception as e:
        print(f"Error migrating archive_configurations: {e}")

    # Note: Other tables that might contain calendar URIs can be added here
    # For example: job_configurations, user_preferences, etc.

    print("URI migration completed!")


def downgrade() -> None:
    """Revert calendar URIs to legacy format."""

    # Get connection
    connection = op.get_bind()

    print("Starting URI reversion to legacy format...")

    # Revert archive_configurations table
    print("Reverting archive_configurations...")
    try:
        result = connection.execute(
            sa.text("SELECT id, source_calendar_uri, destination_calendar_uri FROM archive_configurations")
        )
        configurations = result.fetchall()

        for config in configurations:
            config_id = config[0]
            source_uri = config[1]
            dest_uri = config[2]

            # Revert URIs
            legacy_source_uri = revert_uri_to_legacy(source_uri)
            legacy_dest_uri = revert_uri_to_legacy(dest_uri)

            # Update if changed
            if legacy_source_uri != source_uri or legacy_dest_uri != dest_uri:
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

                print(f"  Config {config_id}:")
                print(f"    Source: {source_uri} -> {legacy_source_uri}")
                print(f"    Dest: {dest_uri} -> {legacy_dest_uri}")
            else:
                print(f"  Config {config_id}: No changes needed")

    except Exception as e:
        print(f"Error reverting archive_configurations: {e}")

    print("URI reversion completed!")


def revert_uri_to_legacy(uri: str) -> str:
    """Revert a user-friendly URI to legacy format."""
    if not uri:
        return uri

    # Handle user-friendly format
    if uri.startswith('msgraph://calendars/'):
        identifier_part = uri[len('msgraph://calendars/'):]

        # Handle primary calendar
        if identifier_part == 'primary':
            return 'msgraph://calendar'

        # Handle quoted identifiers - extract the content
        if identifier_part.startswith('"') and identifier_part.endswith('"'):
            # Remove quotes and unescape
            identifier = identifier_part[1:-1].replace('\\"', '"')
            # Convert back to legacy format (spaces to hyphens, etc.)
            import re
            legacy_id = identifier.lower().strip()
            legacy_id = re.sub(r"\s+", "-", legacy_id)
            legacy_id = re.sub(r"[^a-z0-9\-_]", "", legacy_id)
            return f'msgraph://{legacy_id}'

        # Handle unquoted identifiers
        return f'msgraph://{identifier_part}'

    if uri.startswith('local://calendars/'):
        identifier = uri[len('local://calendars/'):]
        return f'local://{identifier}'

    # If it doesn't match new format, assume it's already legacy
    return uri
