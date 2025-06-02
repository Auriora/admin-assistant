"""
Unit tests for user resolution utility

Tests the user resolution utility functions including OS username detection,
precedence rules, and user lookup functionality.
"""

import os
import pytest
from unittest.mock import Mock, patch

from core.models.user import User
from core.services.user_service import UserService
from core.utilities.user_resolution import (
    get_os_username,
    resolve_user_identifier,
    resolve_user,
    get_user_identifier_source
)


class TestUserResolution:
    """Test suite for user resolution utility functions"""
    
    def test_get_os_username_user_env(self):
        """Test OS username detection from USER environment variable"""
        with patch.dict(os.environ, {'USER': 'testuser'}, clear=True):
            result = get_os_username()
            assert result == 'testuser'
    
    def test_get_os_username_username_env(self):
        """Test OS username detection from USERNAME environment variable"""
        with patch.dict(os.environ, {'USERNAME': 'testuser'}, clear=True):
            result = get_os_username()
            assert result == 'testuser'
    
    def test_get_os_username_logname_env(self):
        """Test OS username detection from LOGNAME environment variable"""
        with patch.dict(os.environ, {'LOGNAME': 'testuser'}, clear=True):
            result = get_os_username()
            assert result == 'testuser'
    
    def test_get_os_username_precedence(self):
        """Test OS username precedence: USER > USERNAME > LOGNAME"""
        with patch.dict(os.environ, {
            'USER': 'user_env',
            'USERNAME': 'username_env',
            'LOGNAME': 'logname_env'
        }, clear=True):
            result = get_os_username()
            assert result == 'user_env'
    
    def test_get_os_username_no_env(self):
        """Test OS username when no environment variables are set"""
        with patch.dict(os.environ, {}, clear=True):
            result = get_os_username()
            assert result is None
    
    def test_get_os_username_strips_whitespace(self):
        """Test OS username strips whitespace"""
        with patch.dict(os.environ, {'USER': '  testuser  '}, clear=True):
            result = get_os_username()
            assert result == 'testuser'
    
    def test_resolve_user_identifier_cli_precedence(self):
        """Test CLI argument has highest precedence"""
        with patch.dict(os.environ, {
            'ADMIN_ASSISTANT_USER': 'env_user',
            'USER': 'os_user'
        }, clear=True):
            result = resolve_user_identifier('cli_user')
            assert result == 'cli_user'
    
    def test_resolve_user_identifier_admin_env_precedence(self):
        """Test ADMIN_ASSISTANT_USER has precedence over OS env"""
        with patch.dict(os.environ, {
            'ADMIN_ASSISTANT_USER': 'env_user',
            'USER': 'os_user'
        }, clear=True):
            result = resolve_user_identifier()
            assert result == 'env_user'
    
    def test_resolve_user_identifier_os_env_fallback(self):
        """Test OS environment variable as fallback"""
        with patch.dict(os.environ, {'USER': 'os_user'}, clear=True):
            result = resolve_user_identifier()
            assert result == 'os_user'
    
    def test_resolve_user_identifier_no_identifier(self):
        """Test when no identifier is found"""
        with patch.dict(os.environ, {}, clear=True):
            result = resolve_user_identifier()
            assert result is None
    
    def test_resolve_user_by_id(self):
        """Test resolving user by numeric ID"""
        mock_user = Mock(spec=User)
        mock_user.id = 123
        mock_user.username = 'testuser'
        
        mock_service = Mock(spec=UserService)
        mock_service.get_by_id.return_value = mock_user
        mock_service.get_by_username.return_value = None
        
        result = resolve_user('123', mock_service)
        assert result == mock_user
        mock_service.get_by_id.assert_called_once_with(123)
    
    def test_resolve_user_by_username(self):
        """Test resolving user by username"""
        mock_user = Mock(spec=User)
        mock_user.id = 123
        mock_user.username = 'testuser'
        
        mock_service = Mock(spec=UserService)
        mock_service.get_by_id.side_effect = ValueError("Invalid ID")
        mock_service.get_by_username.return_value = mock_user
        
        result = resolve_user('testuser', mock_service)
        assert result == mock_user
        mock_service.get_by_username.assert_called_once_with('testuser')
    
    def test_resolve_user_not_found(self):
        """Test resolving user when not found"""
        mock_service = Mock(spec=UserService)
        mock_service.get_by_id.return_value = None
        mock_service.get_by_username.return_value = None
        
        with pytest.raises(ValueError, match="No user found for identifier: testuser"):
            resolve_user('testuser', mock_service)
    
    def test_resolve_user_no_identifier(self):
        """Test resolving user when no identifier found"""
        with patch.dict(os.environ, {}, clear=True):
            result = resolve_user()
            assert result is None
    
    def test_get_user_identifier_source_cli(self):
        """Test identifier source description for CLI argument"""
        result = get_user_identifier_source('cli_user')
        assert result == "command-line argument"
    
    def test_get_user_identifier_source_admin_env(self):
        """Test identifier source description for ADMIN_ASSISTANT_USER"""
        with patch.dict(os.environ, {'ADMIN_ASSISTANT_USER': 'env_user'}, clear=True):
            result = get_user_identifier_source()
            assert result == "ADMIN_ASSISTANT_USER environment variable"
    
    def test_get_user_identifier_source_os_env(self):
        """Test identifier source description for OS environment variable"""
        with patch.dict(os.environ, {'USER': 'os_user'}, clear=True):
            result = get_user_identifier_source()
            assert result == "USER environment variable"
    
    def test_get_user_identifier_source_no_source(self):
        """Test identifier source description when no source found"""
        with patch.dict(os.environ, {}, clear=True):
            result = get_user_identifier_source()
            assert result == "no source found"
