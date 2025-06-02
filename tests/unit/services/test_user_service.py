"""
Unit tests for UserService

Tests the business logic for managing User entities including
CRUD operations, validation, and filtering functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock
from core.services.user_service import UserService
from core.models.user import User
from core.repositories.user_repository import UserRepository


class TestUserService:
    """Test suite for UserService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_repository = Mock(spec=UserRepository)
        self.service = UserService(repository=self.mock_repository)
    
    def test_init_with_repository(self):
        """Test service initialization with provided repository"""
        service = UserService(repository=self.mock_repository)
        assert service.repository == self.mock_repository
    
    def test_init_with_default_repository(self):
        """Test service initialization with default repository"""
        service = UserService()
        assert service.repository is not None
    
    def test_get_by_id(self):
        """Test retrieving user by ID"""
        # Arrange
        user_id = 123
        expected_user = Mock(spec=User)
        self.mock_repository.get_by_id.return_value = expected_user
        
        # Act
        result = self.service.get_by_id(user_id)
        
        # Assert
        assert result == expected_user
        self.mock_repository.get_by_id.assert_called_once_with(user_id)
    
    def test_get_by_id_not_found(self):
        """Test retrieving non-existent user by ID"""
        # Arrange
        user_id = 999
        self.mock_repository.get_by_id.return_value = None
        
        # Act
        result = self.service.get_by_id(user_id)
        
        # Assert
        assert result is None
        self.mock_repository.get_by_id.assert_called_once_with(user_id)
    
    def test_get_by_email(self):
        """Test retrieving user by email"""
        # Arrange
        email = "test@example.com"
        expected_user = Mock(spec=User)
        self.mock_repository.get_by_email.return_value = expected_user
        
        # Act
        result = self.service.get_by_email(email)
        
        # Assert
        assert result == expected_user
        self.mock_repository.get_by_email.assert_called_once_with(email)
    
    def test_get_by_email_not_found(self):
        """Test retrieving non-existent user by email"""
        # Arrange
        email = "nonexistent@example.com"
        self.mock_repository.get_by_email.return_value = None

        # Act
        result = self.service.get_by_email(email)

        # Assert
        assert result is None
        self.mock_repository.get_by_email.assert_called_once_with(email)

    def test_get_by_username(self):
        """Test getting user by username"""
        # Arrange
        username = "testuser"
        expected_user = Mock(spec=User)
        self.mock_repository.get_by_username.return_value = expected_user

        # Act
        result = self.service.get_by_username(username)

        # Assert
        assert result == expected_user
        self.mock_repository.get_by_username.assert_called_once_with(username)

    def test_get_by_username_not_found(self):
        """Test getting user by username when not found"""
        # Arrange
        username = "notfound"
        self.mock_repository.get_by_username.return_value = None

        # Act
        result = self.service.get_by_username(username)

        # Assert
        assert result is None
        self.mock_repository.get_by_username.assert_called_once_with(username)
    
    def test_create_valid_user(self):
        """Test creating a valid user"""
        # Arrange
        user = Mock(spec=User)
        user.email = "test@example.com"
        user.username = None  # No username

        # Act
        self.service.create(user)

        # Assert
        self.mock_repository.add.assert_called_once_with(user)
    
    def test_create_user_validation_error(self):
        """Test creating user with validation error"""
        # Arrange
        user = Mock(spec=User)
        user.email = ""  # Invalid email
        
        # Act & Assert
        with pytest.raises(ValueError, match="User email is required"):
            self.service.create(user)
        
        self.mock_repository.add.assert_not_called()
    
    def test_list_all_users(self):
        """Test listing all users without filter"""
        # Arrange
        expected_users = [Mock(spec=User), Mock(spec=User)]
        self.mock_repository.list.return_value = expected_users
        
        # Act
        result = self.service.list()
        
        # Assert
        assert result == expected_users
        self.mock_repository.list.assert_called_once_with(is_active=None)
    
    def test_list_active_users(self):
        """Test listing only active users"""
        # Arrange
        expected_users = [Mock(spec=User)]
        self.mock_repository.list.return_value = expected_users
        
        # Act
        result = self.service.list(is_active=True)
        
        # Assert
        assert result == expected_users
        self.mock_repository.list.assert_called_once_with(is_active=True)
    
    def test_list_inactive_users(self):
        """Test listing only inactive users"""
        # Arrange
        expected_users = [Mock(spec=User)]
        self.mock_repository.list.return_value = expected_users
        
        # Act
        result = self.service.list(is_active=False)
        
        # Assert
        assert result == expected_users
        self.mock_repository.list.assert_called_once_with(is_active=False)
    
    def test_update_valid_user(self):
        """Test updating a valid user"""
        # Arrange
        user = Mock(spec=User)
        user.email = "updated@example.com"
        user.username = None  # No username

        # Act
        self.service.update(user)

        # Assert
        self.mock_repository.update.assert_called_once_with(user)
    
    def test_update_user_validation_error(self):
        """Test updating user with validation error"""
        # Arrange
        user = Mock(spec=User)
        user.email = None  # Invalid email
        
        # Act & Assert
        with pytest.raises(ValueError, match="User email is required"):
            self.service.update(user)
        
        self.mock_repository.update.assert_not_called()
    
    def test_delete_user(self):
        """Test deleting a user"""
        # Arrange
        user_id = 123
        
        # Act
        self.service.delete(user_id)
        
        # Assert
        self.mock_repository.delete.assert_called_once_with(user_id)
    
    def test_validate_valid_email(self):
        """Test validation with valid email"""
        # Arrange
        user = Mock(spec=User)
        user.email = "valid@example.com"
        user.username = None

        # Act & Assert - should not raise exception
        self.service.validate(user)

    def test_validate_valid_username(self):
        """Test validation with valid username"""
        # Arrange
        user = Mock(spec=User)
        user.email = "valid@example.com"
        user.username = "validuser"
        user.id = 123

        self.mock_repository.get_by_username.return_value = None

        # Act & Assert - should not raise exception
        self.service.validate(user)
        self.mock_repository.get_by_username.assert_called_once_with("validuser")

    def test_validate_empty_username(self):
        """Test validation with empty username"""
        # Arrange
        user = Mock(spec=User)
        user.email = "valid@example.com"
        user.username = "   "  # Whitespace only

        # Act & Assert
        with pytest.raises(ValueError, match="Username cannot be empty or whitespace"):
            self.service.validate(user)

    def test_validate_duplicate_username(self):
        """Test validation with duplicate username"""
        # Arrange
        user = Mock(spec=User)
        user.email = "valid@example.com"
        user.username = "existinguser"
        user.id = 123

        existing_user = Mock(spec=User)
        existing_user.id = 456  # Different ID
        self.mock_repository.get_by_username.return_value = existing_user

        # Act & Assert
        with pytest.raises(ValueError, match="Username 'existinguser' is already taken"):
            self.service.validate(user)

    def test_validate_same_user_username(self):
        """Test validation allows same username for same user (update scenario)"""
        # Arrange
        user = Mock(spec=User)
        user.email = "valid@example.com"
        user.username = "sameuser"
        user.id = 123

        existing_user = Mock(spec=User)
        existing_user.id = 123  # Same ID
        self.mock_repository.get_by_username.return_value = existing_user

        # Act & Assert - should not raise exception
        self.service.validate(user)
    
    def test_validate_empty_email(self):
        """Test validation with empty email"""
        # Arrange
        user = Mock(spec=User)
        user.email = ""
        
        # Act & Assert
        with pytest.raises(ValueError, match="User email is required"):
            self.service.validate(user)
    
    def test_validate_whitespace_email(self):
        """Test validation with whitespace-only email"""
        # Arrange
        user = Mock(spec=User)
        user.email = "   "
        
        # Act & Assert
        with pytest.raises(ValueError, match="User email is required"):
            self.service.validate(user)
    
    def test_validate_none_email(self):
        """Test validation with None email"""
        # Arrange
        user = Mock(spec=User)
        user.email = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="User email is required"):
            self.service.validate(user)
    
    def test_validate_missing_email_attribute(self):
        """Test validation when email attribute is missing"""
        # Arrange
        user = Mock(spec=User)
        # Remove email attribute to test getattr fallback
        if hasattr(user, 'email'):
            delattr(user, 'email')
        
        # Act & Assert
        with pytest.raises(ValueError, match="User email is required"):
            self.service.validate(user)
    
    def test_validate_email_with_numeric_value(self):
        """Test validation when email is a number (edge case)"""
        # Arrange
        user = Mock(spec=User)
        user.email = 123  # Non-string value
        user.username = None  # No username

        # Act & Assert - should not raise exception since str(123).strip() is "123"
        self.service.validate(user)
    
    def test_validate_email_with_zero(self):
        """Test validation when email is zero (edge case)"""
        # Arrange
        user = Mock(spec=User)
        user.email = 0  # Falsy value that fails the 'not email' check

        # Act & Assert - should raise exception since 0 is falsy
        with pytest.raises(ValueError, match="User email is required"):
            self.service.validate(user)
    
    def test_validate_email_with_false(self):
        """Test validation when email is False (edge case)"""
        # Arrange
        user = Mock(spec=User)
        user.email = False  # Falsy value
        
        # Act & Assert
        with pytest.raises(ValueError, match="User email is required"):
            self.service.validate(user)
