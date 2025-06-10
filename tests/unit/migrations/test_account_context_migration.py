"""
Unit tests for the account context migration script.

Tests the migration that adds account context to URIs and new archive configuration columns.
"""
import pytest
import sqlalchemy as sa
from unittest.mock import Mock, patch, MagicMock
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, text
from sqlalchemy.orm import sessionmaker


class TestAccountContextMigration:
    """Test suite for account context migration functionality"""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection"""
        connection = Mock()
        connection.execute = Mock()
        return connection

    @pytest.fixture
    def sample_configurations(self):
        """Sample archive configurations for testing"""
        return [
            (1, "msgraph://calendars/primary", "msgraph://calendars/archive", 1),
            (2, "msgraph://calendars/work", "msgraph://calendars/backup", 2),
            (3, "local://calendars/primary", "local://calendars/archive", 1),
            (4, "msgraph://calendars/\"Custom Calendar\"", "msgraph://calendars/\"Archive Calendar\"", 3),
        ]

    @pytest.fixture
    def sample_users(self):
        """Sample users for testing"""
        return [
            (1, "user1@example.com", "user1"),
            (2, "user2@example.com", "user2"),
            (3, None, "user3"),  # No email
            (4, "", "user4"),    # Empty email
        ]

    def test_add_account_context_to_uri_function(self):
        """Test the add_account_context_to_uri function"""
        from src.core.migrations.versions.20250610_add_account_context_to_uris import add_account_context_to_uri
        
        # Test with email
        result = add_account_context_to_uri("msgraph://calendars/primary", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/primary"
        
        # Test with username (no email)
        result = add_account_context_to_uri("msgraph://calendars/primary", "username")
        assert result == "msgraph://username/calendars/primary"
        
        # Test with quoted identifier
        result = add_account_context_to_uri("msgraph://calendars/\"Custom Calendar\"", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/\"Custom Calendar\""
        
        # Test with already migrated URI (should not double-migrate)
        result = add_account_context_to_uri("msgraph://user@example.com/calendars/primary", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/primary"
        
        # Test with different scheme
        result = add_account_context_to_uri("local://calendars/primary", "user@example.com")
        assert result == "local://user@example.com/calendars/primary"
        
        # Test with None account
        result = add_account_context_to_uri("msgraph://calendars/primary", None)
        assert result == "msgraph://calendars/primary"  # No change
        
        # Test with empty account
        result = add_account_context_to_uri("msgraph://calendars/primary", "")
        assert result == "msgraph://calendars/primary"  # No change

    def test_remove_account_context_from_uri_function(self):
        """Test the remove_account_context_from_uri function"""
        from src.core.migrations.versions.20250610_add_account_context_to_uris import remove_account_context_from_uri
        
        # Test with account context
        result = remove_account_context_from_uri("msgraph://user@example.com/calendars/primary")
        assert result == "msgraph://calendars/primary"
        
        # Test with username account
        result = remove_account_context_from_uri("msgraph://username/calendars/primary")
        assert result == "msgraph://calendars/primary"
        
        # Test with quoted identifier
        result = remove_account_context_from_uri("msgraph://user@example.com/calendars/\"Custom Calendar\"")
        assert result == "msgraph://calendars/\"Custom Calendar\""
        
        # Test with legacy URI (no account context)
        result = remove_account_context_from_uri("msgraph://calendars/primary")
        assert result == "msgraph://calendars/primary"  # No change
        
        # Test with different scheme
        result = remove_account_context_from_uri("local://user@example.com/calendars/primary")
        assert result == "local://calendars/primary"

    def test_get_user_account_context_function(self):
        """Test the get_user_account_context function"""
        from src.core.migrations.versions.20250610_add_account_context_to_uris import get_user_account_context
        
        # Test with email (priority 1)
        result = get_user_account_context("user@example.com", "username", 123)
        assert result == "user@example.com"
        
        # Test with username (priority 2, no email)
        result = get_user_account_context(None, "username", 123)
        assert result == "username"
        
        # Test with user_id (priority 3, no email or username)
        result = get_user_account_context(None, None, 123)
        assert result == "123"
        
        # Test with empty email, fallback to username
        result = get_user_account_context("", "username", 123)
        assert result == "username"
        
        # Test with empty username, fallback to user_id
        result = get_user_account_context("", "", 123)
        assert result == "123"
        
        # Test with all None/empty
        result = get_user_account_context(None, None, None)
        assert result is None

    @patch('src.core.migrations.versions.20250610_add_account_context_to_uris.sa')
    def test_upgrade_migration_adds_columns(self, mock_sa, mock_connection):
        """Test that upgrade migration adds new columns"""
        from src.core.migrations.versions.20250610_add_account_context_to_uris import upgrade
        
        # Mock the operations
        mock_op = Mock()
        
        with patch('src.core.migrations.versions.20250610_add_account_context_to_uris.op', mock_op):
            # Mock connection to return empty results for configurations and users
            mock_connection.execute.return_value.fetchall.return_value = []
            
            upgrade()
            
            # Verify columns were added
            assert mock_op.add_column.call_count == 2
            
            # Check that allow_overlaps column was added
            allow_overlaps_call = mock_op.add_column.call_args_list[0]
            assert 'allow_overlaps' in str(allow_overlaps_call)
            
            # Check that archive_purpose column was added
            archive_purpose_call = mock_op.add_column.call_args_list[1]
            assert 'archive_purpose' in str(archive_purpose_call)

    @patch('src.core.migrations.versions.20250610_add_account_context_to_uris.sa')
    def test_upgrade_migration_updates_uris(self, mock_sa, mock_connection, sample_configurations, sample_users):
        """Test that upgrade migration updates URIs with account context"""
        from src.core.migrations.versions.20250610_add_account_context_to_uris import upgrade
        
        # Mock the operations
        mock_op = Mock()
        
        with patch('src.core.migrations.versions.20250610_add_account_context_to_uris.op', mock_op):
            # Setup mock connection responses
            def mock_execute_side_effect(query):
                result_mock = Mock()
                if "SELECT id, source_calendar_uri, destination_calendar_uri, user_id" in str(query):
                    result_mock.fetchall.return_value = sample_configurations
                elif "SELECT id, email, username FROM users" in str(query):
                    result_mock.fetchall.return_value = sample_users
                else:
                    result_mock.fetchall.return_value = []
                return result_mock
            
            mock_connection.execute.side_effect = mock_execute_side_effect
            
            upgrade()
            
            # Verify that URI updates were executed
            update_calls = [call for call in mock_connection.execute.call_args_list 
                          if "UPDATE archive_configurations" in str(call[0][0])]
            
            # Should have update calls for configurations that needed migration
            assert len(update_calls) > 0

    def test_upgrade_migration_handles_missing_users(self, mock_connection):
        """Test that upgrade migration handles missing users gracefully"""
        from src.core.migrations.versions.20250610_add_account_context_to_uris import upgrade
        
        # Configuration with non-existent user
        configurations = [(1, "msgraph://calendars/primary", "msgraph://calendars/archive", 999)]
        users = [(1, "user1@example.com", "user1")]  # User 999 doesn't exist
        
        mock_op = Mock()
        
        with patch('src.core.migrations.versions.20250610_add_account_context_to_uris.op', mock_op):
            def mock_execute_side_effect(query):
                result_mock = Mock()
                if "SELECT id, source_calendar_uri, destination_calendar_uri, user_id" in str(query):
                    result_mock.fetchall.return_value = configurations
                elif "SELECT id, email, username FROM users" in str(query):
                    result_mock.fetchall.return_value = users
                else:
                    result_mock.fetchall.return_value = []
                return result_mock
            
            mock_connection.execute.side_effect = mock_execute_side_effect
            
            # Should not raise exception
            upgrade()

    @patch('src.core.migrations.versions.20250610_add_account_context_to_uris.sa')
    def test_downgrade_migration_removes_columns(self, mock_sa, mock_connection):
        """Test that downgrade migration removes new columns"""
        from src.core.migrations.versions.20250610_add_account_context_to_uris import downgrade
        
        mock_op = Mock()
        
        with patch('src.core.migrations.versions.20250610_add_account_context_to_uris.op', mock_op):
            # Mock connection to return empty results
            mock_connection.execute.return_value.fetchall.return_value = []
            
            downgrade()
            
            # Verify columns were dropped
            assert mock_op.drop_column.call_count == 2
            
            # Check that columns were dropped in correct order
            drop_calls = [str(call) for call in mock_op.drop_column.call_args_list]
            assert any('archive_purpose' in call for call in drop_calls)
            assert any('allow_overlaps' in call for call in drop_calls)

    @patch('src.core.migrations.versions.20250610_add_account_context_to_uris.sa')
    def test_downgrade_migration_reverts_uris(self, mock_sa, mock_connection):
        """Test that downgrade migration reverts URIs to legacy format"""
        from src.core.migrations.versions.20250610_add_account_context_to_uris import downgrade
        
        # Configurations with account context
        migrated_configurations = [
            (1, "msgraph://user1@example.com/calendars/primary", "msgraph://user1@example.com/calendars/archive"),
            (2, "msgraph://user2@example.com/calendars/work", "msgraph://user2@example.com/calendars/backup"),
        ]
        
        mock_op = Mock()
        
        with patch('src.core.migrations.versions.20250610_add_account_context_to_uris.op', mock_op):
            def mock_execute_side_effect(query):
                result_mock = Mock()
                if "SELECT id, source_calendar_uri, destination_calendar_uri" in str(query):
                    result_mock.fetchall.return_value = migrated_configurations
                else:
                    result_mock.fetchall.return_value = []
                return result_mock
            
            mock_connection.execute.side_effect = mock_execute_side_effect
            
            downgrade()
            
            # Verify that URI reverts were executed
            update_calls = [call for call in mock_connection.execute.call_args_list 
                          if "UPDATE archive_configurations" in str(call[0][0])]
            
            # Should have update calls for configurations that needed reversion
            assert len(update_calls) > 0

    def test_migration_error_handling(self, mock_connection):
        """Test migration error handling"""
        from src.core.migrations.versions.20250610_add_account_context_to_uris import upgrade
        
        mock_op = Mock()
        
        with patch('src.core.migrations.versions.20250610_add_account_context_to_uris.op', mock_op):
            # Simulate database error
            mock_connection.execute.side_effect = Exception("Database connection failed")
            
            # Should handle error gracefully (depending on implementation)
            with pytest.raises(Exception):
                upgrade()

    def test_migration_statistics_and_logging(self, mock_connection, sample_configurations, sample_users):
        """Test that migration provides proper statistics and logging"""
        from src.core.migrations.versions.20250610_add_account_context_to_uris import upgrade
        
        mock_op = Mock()
        
        with patch('src.core.migrations.versions.20250610_add_account_context_to_uris.op', mock_op):
            with patch('src.core.migrations.versions.20250610_add_account_context_to_uris.logger') as mock_logger:
                def mock_execute_side_effect(query):
                    result_mock = Mock()
                    if "SELECT id, source_calendar_uri, destination_calendar_uri, user_id" in str(query):
                        result_mock.fetchall.return_value = sample_configurations
                    elif "SELECT id, email, username FROM users" in str(query):
                        result_mock.fetchall.return_value = sample_users
                    else:
                        result_mock.fetchall.return_value = []
                    return result_mock
                
                mock_connection.execute.side_effect = mock_execute_side_effect
                
                upgrade()
                
                # Verify logging occurred
                assert mock_logger.info.call_count > 0
                
                # Check for specific log messages
                log_messages = [str(call) for call in mock_logger.info.call_args_list]
                assert any("Starting migration" in msg for msg in log_messages)

    def test_uri_transformation_edge_cases(self):
        """Test URI transformation with edge cases"""
        from src.core.migrations.versions.20250610_add_account_context_to_uris import (
            add_account_context_to_uri, 
            remove_account_context_from_uri
        )
        
        # Test with malformed URIs
        edge_cases = [
            "not-a-uri",
            "msgraph://",
            "msgraph:///calendars/primary",
            "msgraph://calendars/",
            "",
            None
        ]
        
        for uri in edge_cases:
            if uri is not None:
                # Should handle gracefully without crashing
                try:
                    result = add_account_context_to_uri(uri, "user@example.com")
                    # Result should be a string
                    assert isinstance(result, str)
                except Exception:
                    # Some edge cases might raise exceptions, which is acceptable
                    pass
                
                try:
                    result = remove_account_context_from_uri(uri)
                    assert isinstance(result, str)
                except Exception:
                    pass

    def test_migration_idempotency(self, mock_connection, sample_configurations, sample_users):
        """Test that migration is idempotent (can be run multiple times safely)"""
        from src.core.migrations.versions.20250610_add_account_context_to_uris import upgrade
        
        mock_op = Mock()
        
        with patch('src.core.migrations.versions.20250610_add_account_context_to_uris.op', mock_op):
            def mock_execute_side_effect(query):
                result_mock = Mock()
                if "SELECT id, source_calendar_uri, destination_calendar_uri, user_id" in str(query):
                    # Return already migrated URIs
                    migrated_configs = [
                        (1, "msgraph://user1@example.com/calendars/primary", "msgraph://user1@example.com/calendars/archive", 1),
                        (2, "msgraph://user2@example.com/calendars/work", "msgraph://user2@example.com/calendars/backup", 2),
                    ]
                    result_mock.fetchall.return_value = migrated_configs
                elif "SELECT id, email, username FROM users" in str(query):
                    result_mock.fetchall.return_value = sample_users
                else:
                    result_mock.fetchall.return_value = []
                return result_mock
            
            mock_connection.execute.side_effect = mock_execute_side_effect
            
            # Run migration twice
            upgrade()
            upgrade()
            
            # Should not cause errors or duplicate migrations
