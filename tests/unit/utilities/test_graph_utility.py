import pytest
from unittest.mock import Mock, patch
from azure.core.credentials import AccessToken
from msgraph.graph_service_client import GraphServiceClient
from core.utilities.graph_utility import AccessTokenCredential, get_graph_client
from core.models.user import User


class TestAccessTokenCredential:
    """Test suite for AccessTokenCredential class"""

    def test_init_stores_access_token(self):
        """Test that AccessTokenCredential stores the access token"""
        # Arrange
        token = "test_access_token_123"
        
        # Act
        credential = AccessTokenCredential(token)
        
        # Assert
        assert credential._access_token == token

    def test_get_token_returns_access_token_object(self):
        """Test that get_token returns an AccessToken object with correct token"""
        # Arrange
        token = "test_access_token_123"
        credential = AccessTokenCredential(token)
        
        # Act
        result = credential.get_token("https://graph.microsoft.com/.default")
        
        # Assert
        assert isinstance(result, AccessToken)
        assert result.token == token
        assert result.expires_on == 2**31 - 1  # Far future expiry

    def test_get_token_with_multiple_scopes(self):
        """Test that get_token works with multiple scopes"""
        # Arrange
        token = "test_access_token_123"
        credential = AccessTokenCredential(token)
        
        # Act
        result = credential.get_token(
            "https://graph.microsoft.com/.default",
            "https://graph.microsoft.com/User.Read"
        )
        
        # Assert
        assert isinstance(result, AccessToken)
        assert result.token == token

    def test_get_token_with_kwargs(self):
        """Test that get_token works with keyword arguments"""
        # Arrange
        token = "test_access_token_123"
        credential = AccessTokenCredential(token)
        
        # Act
        result = credential.get_token(
            "https://graph.microsoft.com/.default",
            tenant_id="test-tenant"
        )
        
        # Assert
        assert isinstance(result, AccessToken)
        assert result.token == token


class TestGetGraphClient:
    """Test suite for get_graph_client function"""

    @patch('core.utilities.graph_utility.GraphServiceClient')
    def test_get_graph_client_creates_client_with_correct_parameters(self, mock_graph_client_class):
        """Test that get_graph_client creates GraphServiceClient with correct parameters"""
        # Arrange
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        access_token = "test_access_token_123"
        
        mock_client = Mock(spec=GraphServiceClient)
        mock_graph_client_class.return_value = mock_client
        
        # Act
        result = get_graph_client(user, access_token)
        
        # Assert
        assert result == mock_client
        mock_graph_client_class.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_graph_client_class.call_args
        assert 'credentials' in call_args.kwargs
        assert 'scopes' in call_args.kwargs
        assert call_args.kwargs['scopes'] == ["https://graph.microsoft.com/.default"]
        
        # Verify the credential is an AccessTokenCredential
        credential = call_args.kwargs['credentials']
        assert isinstance(credential, AccessTokenCredential)
        assert credential._access_token == access_token

    @patch('core.utilities.graph_utility.GraphServiceClient')
    def test_get_graph_client_with_different_tokens(self, mock_graph_client_class):
        """Test that get_graph_client works with different access tokens"""
        # Arrange
        user = Mock(spec=User)
        user.id = 2
        user.email = "another@example.com"
        access_token = "different_token_456"
        
        mock_client = Mock(spec=GraphServiceClient)
        mock_graph_client_class.return_value = mock_client
        
        # Act
        result = get_graph_client(user, access_token)
        
        # Assert
        assert result == mock_client
        
        # Verify the credential has the correct token
        call_args = mock_graph_client_class.call_args
        credential = call_args.kwargs['credentials']
        assert credential._access_token == access_token

    @patch('core.utilities.graph_utility.GraphServiceClient')
    def test_get_graph_client_uses_default_scopes(self, mock_graph_client_class):
        """Test that get_graph_client uses the correct default scopes"""
        # Arrange
        user = Mock(spec=User)
        access_token = "test_token"
        
        mock_client = Mock(spec=GraphServiceClient)
        mock_graph_client_class.return_value = mock_client
        
        # Act
        get_graph_client(user, access_token)
        
        # Assert
        call_args = mock_graph_client_class.call_args
        expected_scopes = ["https://graph.microsoft.com/.default"]
        assert call_args.kwargs['scopes'] == expected_scopes

    def test_access_token_credential_integration(self):
        """Integration test for AccessTokenCredential with get_graph_client"""
        # Arrange
        user = Mock(spec=User)
        access_token = "integration_test_token"
        
        # Act - Create credential directly to test integration
        credential = AccessTokenCredential(access_token)
        token_result = credential.get_token("https://graph.microsoft.com/.default")
        
        # Assert
        assert token_result.token == access_token
        assert isinstance(token_result, AccessToken)
        
        # Verify the token has a far-future expiry
        assert token_result.expires_on > 1000000000  # Should be a large timestamp
