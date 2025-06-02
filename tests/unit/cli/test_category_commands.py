"""
Unit tests for CLI category commands

Tests the category management CLI commands including list, add, edit, delete, and validate.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner
from cli.main import app, category_app


class TestCategoryCLICommands:
    """Test suite for category CLI commands"""

    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()
    
    @patch('cli.main.resolve_cli_user')
    @patch('core.db.get_session')
    @patch('core.repositories.get_category_repository')
    @patch('core.services.category_service.CategoryService')
    def test_category_list_command_success_local(self, mock_category_service_class,
                                                mock_get_repo, mock_get_session,
                                                mock_resolve_user):
        """Test successful category listing with local store"""
        # Arrange
        mock_user = Mock(id=1, email='test@example.com')
        mock_resolve_user.return_value = mock_user
        
        # Create simple category objects that work with Rich rendering
        class MockCategory:
            def __init__(self, id, name, description, user_id):
                self.id = id
                self.name = name
                self.description = description
                self.user_id = user_id

        mock_categories = [
            MockCategory(1, 'Client A - Hourly', 'Hourly work', 1),
            MockCategory(2, 'Client B - Fixed', 'Fixed price work', 1)
        ]
        mock_category_service = Mock()
        mock_category_service.list.return_value = mock_categories
        mock_category_service_class.return_value = mock_category_service
        
        mock_repository = Mock()
        mock_get_repo.return_value = mock_repository
        
        # Act
        result = self.runner.invoke(category_app, ['list', '--user', '1', '--store', 'local'])
        
        # Assert
        assert result.exit_code == 0
        assert 'Client A - Hourly' in result.output
        assert 'Client B - Fixed' in result.output
        mock_resolve_user.assert_called_once_with('1')
        mock_category_service.list.assert_called_once()
    
    def test_category_list_command_success_msgraph(self):
        """Test successful category listing with msgraph store"""
        with patch('cli.main.resolve_cli_user') as mock_resolve_user, \
             patch('core.utilities.auth_utility.get_cached_access_token') as mock_get_token, \
             patch('core.utilities.get_graph_client') as mock_get_graph_client, \
             patch('core.repositories.get_category_repository') as mock_get_repo, \
             patch('core.services.category_service.CategoryService') as mock_category_service_class:

            # Arrange
            mock_user = Mock(id=1, email='test@example.com')
            mock_resolve_user.return_value = mock_user

            mock_get_token.return_value = 'valid_token'
            mock_graph_client = Mock()
            mock_get_graph_client.return_value = mock_graph_client

            # Create mock categories with proper string attributes
            mock_category = Mock()
            mock_category.id = 1
            mock_category.name = 'Online Meeting'
            mock_category.description = 'Remote meetings'
            mock_categories = [mock_category]
            mock_category_service = Mock()
            mock_category_service.list.return_value = mock_categories
            mock_category_service_class.return_value = mock_category_service

            mock_repository = Mock()
            mock_get_repo.return_value = mock_repository

            # Act
            result = self.runner.invoke(category_app, ['list', '--user', '1', '--store', 'msgraph'])

            # Assert
            assert result.exit_code == 0
            assert 'Online Meeting' in result.output
            mock_get_token.assert_called_once()
            mock_get_graph_client.assert_called_once_with(mock_user, 'valid_token')

    @patch('core.services.user_service.UserService')
    @patch('core.utilities.auth_utility.get_cached_access_token')
    def test_category_list_command_no_token_msgraph(self, mock_get_token, mock_user_service_class):
        """Test category listing with msgraph store when no token available"""
        # Arrange
        mock_user = Mock(id=1, email='test@example.com')
        mock_user_service = Mock()
        mock_user_service.get_by_id.return_value = mock_user
        mock_user_service_class.return_value = mock_user_service

        mock_get_token.return_value = None

        # Act
        result = self.runner.invoke(category_app, ['list', '--user', '1', '--store', 'msgraph'])

        # Assert
        assert result.exit_code == 1
        assert 'No valid MS Graph token found' in result.output

    @patch('cli.main.resolve_cli_user')
    def test_category_list_command_user_not_found(self, mock_resolve_user):
        """Test category listing when user not found"""
        # Arrange
        mock_resolve_user.side_effect = ValueError("No user found for identifier: 999")

        # Act
        result = self.runner.invoke(category_app, ['list', '--user', '999'])

        # Assert
        assert result.exit_code == 1
        assert 'No user found for identifier: 999' in result.output
    
    @patch('core.services.user_service.UserService')
    @patch('core.db.get_session')
    @patch('core.repositories.get_category_repository')
    @patch('core.services.category_service.CategoryService')
    def test_category_list_command_no_categories(self, mock_category_service_class,
                                                mock_get_repo, mock_get_session,
                                                mock_user_service_class):
        """Test category listing when no categories found"""
        # Arrange
        mock_user = Mock(id=1, email='test@example.com')
        mock_user_service = Mock()
        mock_user_service.get_by_id.return_value = mock_user
        mock_user_service_class.return_value = mock_user_service
        
        mock_category_service = Mock()
        mock_category_service.list.return_value = []
        mock_category_service_class.return_value = mock_category_service
        
        # Act
        result = self.runner.invoke(category_app, ['list', '--user', '1'])

        # Assert
        assert result.exit_code == 0
        assert 'No categories found' in result.output

    def test_category_list_command_invalid_store(self):
        """Test category listing with invalid store option"""
        # Act
        result = self.runner.invoke(category_app, ['list', '--user', '1', '--store', 'invalid'])
        
        # Assert
        assert result.exit_code == 1
        assert "Invalid store 'invalid'" in result.output
    
    @patch('core.services.user_service.UserService')
    @patch('core.db.get_session')
    @patch('core.repositories.get_category_repository')
    @patch('core.services.category_service.CategoryService')
    @patch('typer.prompt')
    def test_category_add_command_success(self, mock_prompt, mock_category_service_class,
                                         mock_get_repo, mock_get_session,
                                         mock_user_service_class):
        """Test successful category creation"""
        # Arrange
        mock_user = Mock(id=1, email='test@example.com')
        mock_user_service = Mock()
        mock_user_service.get_by_id.return_value = mock_user
        mock_user_service_class.return_value = mock_user_service
        
        mock_prompt.side_effect = ['New Client - Hourly', 'Hourly billing work']
        
        mock_new_category = Mock(id=3, name='New Client - Hourly', description='Hourly billing work')
        mock_category_service = Mock()
        mock_category_service.create.return_value = mock_new_category
        mock_category_service_class.return_value = mock_category_service
        
        # Act
        result = self.runner.invoke(category_app, ['add', '--user', '1'])

        # Assert
        assert result.exit_code == 0
        assert 'created successfully in local store' in result.output
        assert 'New Client - Hourly' in result.output
        mock_category_service.create.assert_called_once()
    
    def test_category_add_command_with_options(self):
        """Test category creation with command line options"""
        with patch('core.services.UserService') as mock_user_service_class, \
             patch('core.db.get_session') as mock_get_session, \
             patch('core.repositories.get_category_repository') as mock_get_repo, \
             patch('core.services.category_service.CategoryService') as mock_category_service_class:

            # Arrange
            mock_user = Mock(id=1, email='test@example.com')
            mock_user_service = Mock()
            mock_user_service.get_by_id.return_value = mock_user
            mock_user_service_class.return_value = mock_user_service

            mock_new_category = Mock(id=3, name='Client C - Project', description='Project work')
            mock_category_service = Mock()
            mock_category_service.create.return_value = mock_new_category
            mock_category_service_class.return_value = mock_category_service

            # Act
            result = self.runner.invoke(category_app, [
                'add', '--user', '1',
                '--name', 'Client C - Project',
                '--description', 'Project work'
            ])

            # Assert
            assert result.exit_code == 0
            assert 'created successfully in local store' in result.output
            mock_category_service.create.assert_called_once()
    
    def test_category_delete_command_success(self):
        """Test successful category deletion with confirmation"""
        with patch('core.services.UserService') as mock_user_service_class, \
             patch('core.db.get_session') as mock_get_session, \
             patch('core.repositories.get_category_repository') as mock_get_repo, \
             patch('core.services.category_service.CategoryService') as mock_category_service_class:

            # Arrange
            mock_user = Mock(id=1, email='test@example.com')
            mock_user_service = Mock()
            mock_user_service.get_by_id.return_value = mock_user
            mock_user_service_class.return_value = mock_user_service

            # Create a simple category object for deletion
            class MockCategory:
                def __init__(self, id, name):
                    self.id = id
                    self.name = name

            mock_category = MockCategory(1, 'Test Category')
            mock_category_service = Mock()
            mock_category_service.get_by_id.return_value = mock_category
            mock_category_service_class.return_value = mock_category_service

            # Act - simulate user confirming deletion
            result = self.runner.invoke(category_app, [
                'delete', '--user', '1', '--id', '1'
            ], input='y\n')

            # Assert
            assert result.exit_code == 0
            assert 'deleted successfully from local store' in result.output
            mock_category_service.delete.assert_called_once_with('1')
    
    def test_category_delete_command_cancelled(self):
        """Test category deletion cancelled by user"""
        with patch('core.services.UserService') as mock_user_service_class, \
             patch('core.db.get_session') as mock_get_session, \
             patch('core.repositories.get_category_repository') as mock_get_repo, \
             patch('core.services.category_service.CategoryService') as mock_category_service_class:

            # Arrange
            mock_user = Mock(id=1, email='test@example.com')
            mock_user_service = Mock()
            mock_user_service.get_by_id.return_value = mock_user
            mock_user_service_class.return_value = mock_user_service

            # Create a simple category object for deletion
            class MockCategory:
                def __init__(self, id, name):
                    self.id = id
                    self.name = name

            mock_category = MockCategory(1, 'Test Category')
            mock_category_service = Mock()
            mock_category_service.get_by_id.return_value = mock_category
            mock_category_service_class.return_value = mock_category_service

            # Act - simulate user cancelling deletion
            result = self.runner.invoke(category_app, [
                'delete', '--user', '1', '--id', '1'
            ], input='n\n')

            # Assert
            assert result.exit_code == 0
            assert 'deletion cancelled' in result.output
            mock_category_service.delete.assert_not_called()
    
    @patch('core.services.user_service.UserService')
    @patch('core.db.get_session')
    @patch('core.repositories.get_category_repository')
    @patch('core.services.category_service.CategoryService')
    def test_category_delete_command_not_found(self, mock_category_service_class,
                                              mock_get_repo, mock_get_session,
                                              mock_user_service_class):
        """Test category deletion when category not found"""
        # Arrange
        mock_user = Mock(id=1, email='test@example.com')
        mock_user_service = Mock()
        mock_user_service.get_by_id.return_value = mock_user
        mock_user_service_class.return_value = mock_user_service

        mock_category_service = Mock()
        mock_category_service.get_by_id.return_value = None
        mock_category_service_class.return_value = mock_category_service

        # Act
        result = self.runner.invoke(category_app, [
            'delete', '--user', '1', '--id', '999'
        ])

        # Assert
        assert result.exit_code == 1
        assert 'Category 999 not found for user 1' in result.output

    @patch('cli.main.resolve_cli_user')
    @patch('core.db.get_session')
    @patch('core.services.category_processing_service.CategoryProcessingService')
    def test_category_validate_command_success(self, mock_category_processing_class,
                                              mock_get_session,
                                              mock_resolve_user):
        """Test successful category validation"""
        # Arrange
        mock_user = Mock(id=1, email='test@example.com')
        mock_resolve_user.return_value = mock_user

        # Mock session and query
        mock_session = Mock()
        mock_get_session.return_value = mock_session
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []  # No appointments found

        mock_stats = {
            'total_appointments': 0,
            'valid_categories': 0,
            'invalid_categories': 0,
            'validation_issues': []
        }
        mock_category_processing = Mock()
        mock_category_processing.get_category_statistics.return_value = mock_stats
        mock_category_processing_class.return_value = mock_category_processing

        # Act
        result = self.runner.invoke(category_app, [
            'validate', '--user', '1',
            '--start-date', '2024-01-01',
            '--end-date', '2024-01-31'
        ])

        # Assert
        assert result.exit_code == 0
        assert 'No appointments found for the specified date range' in result.output

    @patch('cli.main.resolve_cli_user')
    @patch('core.db.get_session')
    @patch('core.services.category_processing_service.CategoryProcessingService')
    def test_category_validate_command_no_issues(self, mock_category_processing_class,
                                                 mock_get_session,
                                                 mock_resolve_user):
        """Test category validation with no issues found"""
        # Arrange
        mock_user = Mock(id=1, email='test@example.com')
        mock_resolve_user.return_value = mock_user

        # Mock session and query
        mock_session = Mock()
        mock_get_session.return_value = mock_session
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []  # No appointments found

        mock_stats = {
            'total_appointments': 0,
            'valid_categories': 0,
            'invalid_categories': 0,
            'validation_issues': []
        }
        mock_category_processing = Mock()
        mock_category_processing.get_category_statistics.return_value = mock_stats
        mock_category_processing_class.return_value = mock_category_processing

        # Act
        result = self.runner.invoke(category_app, [
            'validate', '--user', '1',
            '--start-date', '2024-01-01',
            '--end-date', '2024-01-31'
        ])

        # Assert
        assert result.exit_code == 0
        assert 'No appointments found for the specified date range' in result.output

    @patch('cli.main.resolve_cli_user')
    def test_category_validate_command_user_not_found(self, mock_resolve_user):
        """Test category validation when user not found"""
        # Arrange
        mock_resolve_user.side_effect = ValueError("No user found for identifier: 999")

        # Act
        result = self.runner.invoke(category_app, [
            'validate', '--user', '999'
        ])

        # Assert
        assert result.exit_code == 1
        assert 'No user found for identifier: 999' in result.output

    @patch('core.services.user_service.UserService')
    @patch('core.db.get_session')
    @patch('core.repositories.get_category_repository')
    @patch('core.services.category_service.CategoryService')
    def test_category_edit_command_success(self, mock_category_service_class,
                                          mock_get_repo, mock_get_session,
                                          mock_user_service_class):
        """Test successful category editing"""
        # Arrange
        mock_user = Mock(id=1, email='test@example.com')
        mock_user_service = Mock()
        mock_user_service.get_by_id.return_value = mock_user
        mock_user_service_class.return_value = mock_user_service

        mock_category = Mock(id=1, name='Old Name', description='Old description')
        mock_updated_category = Mock(id=1, name='New Name', description='New description')
        mock_category_service = Mock()
        mock_category_service.get_by_id.return_value = mock_category
        mock_category_service.update.return_value = mock_updated_category
        mock_category_service_class.return_value = mock_category_service

        # Act
        result = self.runner.invoke(category_app, [
            'edit', '--user', '1', '--id', '1',
            '--name', 'New Name',
            '--description', 'New description'
        ])

        # Assert
        assert result.exit_code == 0
        assert 'Category 1 updated successfully in local store' in result.output
        mock_category_service.update.assert_called_once()

    @patch('core.services.user_service.UserService')
    @patch('core.db.get_session')
    @patch('core.repositories.get_category_repository')
    @patch('core.services.category_service.CategoryService')
    def test_category_commands_error_handling(self, mock_category_service_class,
                                             mock_get_repo, mock_get_session,
                                             mock_user_service_class):
        """Test error handling in category commands"""
        # Arrange
        mock_user = Mock(id=1, email='test@example.com')
        mock_user_service = Mock()
        mock_user_service.get_by_id.return_value = mock_user
        mock_user_service_class.return_value = mock_user_service

        mock_category_service = Mock()
        mock_category_service.list.side_effect = Exception('Database connection failed')
        mock_category_service_class.return_value = mock_category_service

        # Act
        result = self.runner.invoke(category_app, ['list', '--user', '1'])

        # Assert
        assert result.exit_code == 1
        assert 'Error listing categories' in result.output
