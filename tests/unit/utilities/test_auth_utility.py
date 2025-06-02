"""
Unit tests for authentication utility

Tests the authentication utility functions including MSAL app creation, login flows,
token management, and security features.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock, mock_open
from core.utilities.auth_utility import (
    ensure_secure_cache_dir,
    get_msal_app,
    msal_login,
    get_cached_access_token,
    msal_logout
)


class TestAuthUtility:
    """Test suite for authentication utility functions"""
    
    def test_ensure_secure_cache_dir_creates_directory(self):
        """Test secure cache directory creation with proper permissions"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = os.path.join(temp_dir, 'test_cache')
            
            with patch('core.utilities.auth_utility.CACHE_DIR', cache_dir):
                ensure_secure_cache_dir()
                
                assert os.path.exists(cache_dir)
                # Check permissions (owner read/write/execute only)
                stat_info = os.stat(cache_dir)
                assert oct(stat_info.st_mode)[-3:] == '700'
    
    def test_ensure_secure_cache_dir_fixes_permissions(self):
        """Test fixing permissions on existing directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = os.path.join(temp_dir, 'test_cache')
            os.makedirs(cache_dir, mode=0o755)  # Insecure permissions
            
            with patch('core.utilities.auth_utility.CACHE_DIR', cache_dir):
                ensure_secure_cache_dir()
                
                stat_info = os.stat(cache_dir)
                assert oct(stat_info.st_mode)[-3:] == '700'
    
    def test_ensure_secure_cache_dir_handles_existing_secure_dir(self):
        """Test handling of existing directory with correct permissions"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = os.path.join(temp_dir, 'test_cache')
            os.makedirs(cache_dir, mode=0o700)  # Already secure
            
            with patch('core.utilities.auth_utility.CACHE_DIR', cache_dir):
                # Should not raise any errors
                ensure_secure_cache_dir()
                
                stat_info = os.stat(cache_dir)
                assert oct(stat_info.st_mode)[-3:] == '700'
    
    @patch('core.utilities.auth_utility.msal.PublicClientApplication')
    @patch('core.utilities.auth_utility.msal.SerializableTokenCache')
    def test_get_msal_app_new_cache(self, mock_cache_class, mock_msal):
        """Test MSAL application creation with new cache file"""
        # Arrange
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_msal.return_value = mock_app
        mock_cache_class.return_value = mock_cache
        
        with patch.dict(os.environ, {
            'MS_CLIENT_ID': 'test_client_id',
            'MS_TENANT_ID': 'test_tenant_id'
        }):
            with patch('core.utilities.auth_utility.os.path.exists', return_value=False):
                with patch('builtins.open', mock_open()):
                    with patch('core.utilities.auth_utility.os.chmod'):
                        # Act
                        app, cache = get_msal_app()
                        
                        # Assert
                        assert app == mock_app
                        assert cache == mock_cache
                        mock_msal.assert_called_once()
                        mock_cache_class.assert_called_once()
    
    @patch('core.utilities.auth_utility.msal.PublicClientApplication')
    @patch('core.utilities.auth_utility.msal.SerializableTokenCache')
    def test_get_msal_app_existing_cache(self, mock_cache_class, mock_msal):
        """Test MSAL application creation with existing cache file"""
        # Arrange
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_msal.return_value = mock_app
        mock_cache_class.return_value = mock_cache

        # Mock file stat to simulate secure permissions
        mock_stat = MagicMock()
        mock_stat.st_mode = 0o600  # Secure permissions

        with patch.dict(os.environ, {
            'MS_CLIENT_ID': 'test_client_id',
            'MS_TENANT_ID': 'test_tenant_id'
        }):
            with patch('core.utilities.auth_utility.os.path.exists', return_value=True):
                with patch('core.utilities.auth_utility.os.stat', return_value=mock_stat):
                    with patch('builtins.open', mock_open(read_data='cached_data')):
                        # Act
                        app, cache = get_msal_app()

                        # Assert
                        assert app == mock_app
                        assert cache == mock_cache
                        mock_cache.deserialize.assert_called_once_with('cached_data')
    
    def test_get_msal_app_missing_environment_variables(self):
        """Test MSAL app creation fails with missing environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="MS_CLIENT_ID and MS_TENANT_ID environment variables are required"):
                get_msal_app()
    
    @patch('core.utilities.auth_utility.get_msal_app')
    def test_msal_login_with_cached_token(self, mock_get_app):
        """Test login with cached valid token"""
        # Arrange
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_get_app.return_value = (mock_app, mock_cache)
        
        # Mock successful silent token acquisition
        mock_app.get_accounts.return_value = [{'account': 'test'}]
        mock_app.acquire_token_silent.return_value = {'access_token': 'token123'}
        
        with patch('builtins.open', mock_open()):
            with patch('core.utilities.auth_utility.os.chmod'):
                # Act
                result = msal_login()
                
                # Assert
                assert result['access_token'] == 'token123'
                mock_app.acquire_token_silent.assert_called_once()
    
    @patch('core.utilities.auth_utility.get_msal_app')
    def test_msal_login_device_flow(self, mock_get_app):
        """Test login using device flow when no cached token"""
        # Arrange
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_get_app.return_value = (mock_app, mock_cache)
        
        # Mock no cached accounts
        mock_app.get_accounts.return_value = []
        mock_app.acquire_token_silent.return_value = None
        
        # Mock device flow
        mock_app.initiate_device_flow.return_value = {
            'user_code': 'ABC123',
            'message': 'Enter code ABC123 at https://microsoft.com/devicelogin'
        }
        mock_app.acquire_token_by_device_flow.return_value = {'access_token': 'token123'}
        
        with patch('builtins.open', mock_open()):
            with patch('core.utilities.auth_utility.os.chmod'):
                with patch('builtins.print') as mock_print:  # Mock print for device flow message
                    # Act
                    result = msal_login()
                    
                    # Assert
                    assert result['access_token'] == 'token123'
                    mock_app.initiate_device_flow.assert_called_once()
                    mock_app.acquire_token_by_device_flow.assert_called_once()
                    mock_print.assert_called()
    
    @patch('core.utilities.auth_utility.get_msal_app')
    def test_msal_login_device_flow_failure(self, mock_get_app):
        """Test device flow login failure"""
        # Arrange
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_cache.serialize.return_value = 'serialized_cache_data'
        mock_get_app.return_value = (mock_app, mock_cache)

        mock_app.get_accounts.return_value = []
        mock_app.acquire_token_silent.return_value = None
        mock_app.initiate_device_flow.return_value = {
            'user_code': 'ABC123',
            'message': 'Enter code ABC123'
        }
        mock_app.acquire_token_by_device_flow.return_value = {'error': 'authentication_failed'}

        with patch('builtins.open', mock_open()):
            with patch('core.utilities.auth_utility.os.chmod'):
                with patch('builtins.print'):
                    # Act & Assert
                    with pytest.raises(RuntimeError, match="Failed to acquire token"):
                        msal_login()
    
    @patch('core.utilities.auth_utility.os.path.exists')
    @patch('core.utilities.auth_utility.os.remove')
    def test_msal_logout_cache_exists(self, mock_remove, mock_exists):
        """Test token cleanup during logout when cache exists"""
        # Arrange
        mock_exists.return_value = True
        
        # Act
        msal_logout()
        
        # Assert
        mock_remove.assert_called_once()
    
    @patch('core.utilities.auth_utility.os.path.exists')
    @patch('core.utilities.auth_utility.os.remove')
    def test_msal_logout_cache_not_exists(self, mock_remove, mock_exists):
        """Test logout when cache file doesn't exist"""
        # Arrange
        mock_exists.return_value = False
        
        # Act
        msal_logout()
        
        # Assert
        mock_remove.assert_not_called()
    
    @patch('core.utilities.auth_utility.get_msal_app')
    def test_get_cached_access_token_success(self, mock_get_app):
        """Test successful cached token retrieval"""
        # Arrange
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_get_app.return_value = (mock_app, mock_cache)
        
        mock_app.get_accounts.return_value = [{'account': 'test'}]
        mock_app.acquire_token_silent.return_value = {'access_token': 'cached_token'}
        
        # Act
        result = get_cached_access_token()
        
        # Assert
        assert result == 'cached_token'
        mock_app.acquire_token_silent.assert_called_once()
    
    @patch('core.utilities.auth_utility.get_msal_app')
    def test_get_cached_access_token_no_accounts(self, mock_get_app):
        """Test cached token retrieval when no accounts available"""
        # Arrange
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_get_app.return_value = (mock_app, mock_cache)
        
        mock_app.get_accounts.return_value = []
        
        # Act
        result = get_cached_access_token()
        
        # Assert
        assert result is None
        mock_app.acquire_token_silent.assert_not_called()
    
    @patch('core.utilities.auth_utility.get_msal_app')
    def test_get_cached_access_token_silent_fails(self, mock_get_app):
        """Test cached token retrieval when silent acquisition fails"""
        # Arrange
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_get_app.return_value = (mock_app, mock_cache)
        
        mock_app.get_accounts.return_value = [{'account': 'test'}]
        mock_app.acquire_token_silent.return_value = None
        
        # Act
        result = get_cached_access_token()
        
        # Assert
        assert result is None
    
    @patch('core.utilities.auth_utility.get_msal_app')
    def test_get_cached_access_token_error_response(self, mock_get_app):
        """Test cached token retrieval with error response"""
        # Arrange
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_get_app.return_value = (mock_app, mock_cache)
        
        mock_app.get_accounts.return_value = [{'account': 'test'}]
        mock_app.acquire_token_silent.return_value = {'error': 'token_expired'}
        
        # Act
        result = get_cached_access_token()
        
        # Assert
        assert result is None
    
    @patch('core.utilities.auth_utility.get_msal_app')
    def test_token_cache_security_file_permissions(self, mock_get_app):
        """Test that token cache files are created with secure permissions"""
        # Arrange
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_cache.serialize.return_value = 'serialized_cache_data'
        mock_get_app.return_value = (mock_app, mock_cache)
        
        mock_app.get_accounts.return_value = [{'account': 'test'}]
        mock_app.acquire_token_silent.return_value = {'access_token': 'token123'}
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('core.utilities.auth_utility.os.chmod') as mock_chmod:
                # Act
                msal_login()
                
                # Assert
                mock_file.assert_called()
                mock_chmod.assert_called()
                # Verify secure permissions (0o600 = owner read/write only)
                chmod_call_args = mock_chmod.call_args[0]
                assert chmod_call_args[1] == 0o600
