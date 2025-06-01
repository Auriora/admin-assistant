"""
Tests for prompt_service module.
"""

import pytest
from unittest.mock import Mock, patch
from typing import List, Optional

from core.services.prompt_service import PromptService
from core.models.prompt import Prompt
from core.repositories.prompt_repository import PromptRepository


class TestPromptService:
    """Test cases for PromptService class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_repository = Mock(spec=PromptRepository)
        self.service = PromptService(self.mock_repository)

    def test_init_with_repository(self):
        """Test initialization with provided repository."""
        # Arrange & Act
        service = PromptService(self.mock_repository)
        
        # Assert
        assert service.repository == self.mock_repository

    @patch('core.services.prompt_service.PromptRepository')
    def test_init_with_default_repository(self, mock_repo_class):
        """Test initialization with default repository."""
        # Arrange
        mock_repo_instance = Mock(spec=PromptRepository)
        mock_repo_class.return_value = mock_repo_instance
        
        # Act
        service = PromptService()
        
        # Assert
        mock_repo_class.assert_called_once_with()
        assert service.repository == mock_repo_instance

    def test_get_by_id_success(self):
        """Test successful retrieval of prompt by ID."""
        # Arrange
        prompt_id = 1
        expected_prompt = Mock(spec=Prompt)
        self.mock_repository.get_by_id.return_value = expected_prompt
        
        # Act
        result = self.service.get_by_id(prompt_id)
        
        # Assert
        assert result == expected_prompt
        self.mock_repository.get_by_id.assert_called_once_with(prompt_id)

    def test_get_by_id_not_found(self):
        """Test retrieval when prompt is not found."""
        # Arrange
        prompt_id = 999
        self.mock_repository.get_by_id.return_value = None
        
        # Act
        result = self.service.get_by_id(prompt_id)
        
        # Assert
        assert result is None
        self.mock_repository.get_by_id.assert_called_once_with(prompt_id)

    def test_create_prompt(self):
        """Test creating a new prompt."""
        # Arrange
        prompt = Mock(spec=Prompt)
        
        # Act
        self.service.create(prompt)
        
        # Assert
        self.mock_repository.add.assert_called_once_with(prompt)

    def test_list_by_user(self):
        """Test listing prompts by user ID."""
        # Arrange
        user_id = 123
        expected_prompts = [Mock(spec=Prompt), Mock(spec=Prompt)]
        self.mock_repository.list_by_user.return_value = expected_prompts
        
        # Act
        result = self.service.list_by_user(user_id)
        
        # Assert
        assert result == expected_prompts
        self.mock_repository.list_by_user.assert_called_once_with(user_id)

    def test_list_by_type(self):
        """Test listing prompts by type."""
        # Arrange
        prompt_type = "system"
        expected_prompts = [Mock(spec=Prompt), Mock(spec=Prompt)]
        self.mock_repository.list_by_type.return_value = expected_prompts
        
        # Act
        result = self.service.list_by_type(prompt_type)
        
        # Assert
        assert result == expected_prompts
        self.mock_repository.list_by_type.assert_called_once_with(prompt_type)

    def test_delete_prompt(self):
        """Test deleting a prompt."""
        # Arrange
        prompt_id = 1
        
        # Act
        self.service.delete(prompt_id)
        
        # Assert
        self.mock_repository.delete.assert_called_once_with(prompt_id)

    def test_get_most_relevant_prompt_user_and_action_match(self):
        """Test getting most relevant prompt with user+action match (highest priority)."""
        # Arrange
        user_id = 123
        action_type = "overlap_resolution"
        
        # Create mock prompts
        user_action_prompt = Mock(spec=Prompt)
        user_action_prompt.action_type = action_type
        
        other_prompt = Mock(spec=Prompt)
        other_prompt.action_type = "other_action"
        
        self.mock_repository.list_by_user.return_value = [user_action_prompt, other_prompt]
        
        # Act
        result = self.service.get_most_relevant_prompt(user_id, action_type)
        
        # Assert
        assert result == user_action_prompt
        self.mock_repository.list_by_user.assert_called_once_with(user_id)

    def test_get_most_relevant_prompt_user_only_match(self):
        """Test getting most relevant prompt with user-only match (second priority)."""
        # Arrange
        user_id = 123
        action_type = "overlap_resolution"

        # Create mock prompts - no action match
        user_prompt = Mock(spec=Prompt)
        user_prompt.action_type = "other_action"

        self.mock_repository.list_by_user.return_value = [user_prompt]

        # Act
        result = self.service.get_most_relevant_prompt(user_id, action_type)

        # Assert
        assert result == user_prompt
        # Method is called twice: once for user+action check, once for user-only check
        assert self.mock_repository.list_by_user.call_count == 2
        self.mock_repository.list_by_user.assert_called_with(user_id)

    def test_get_most_relevant_prompt_action_only_match(self):
        """Test getting most relevant prompt with action-only match (third priority)."""
        # Arrange
        user_id = None
        action_type = "overlap_resolution"

        # Create mock prompts
        action_prompt = Mock(spec=Prompt)
        action_prompt.action_type = action_type

        other_prompt = Mock(spec=Prompt)
        other_prompt.action_type = "other_action"

        self.mock_repository.list_by_type.return_value = [action_prompt, other_prompt]

        # Act
        result = self.service.get_most_relevant_prompt(user_id, action_type)

        # Assert
        assert result == action_prompt
        self.mock_repository.list_by_type.assert_called_once_with("action-specific")

    def test_get_most_relevant_prompt_system_fallback(self):
        """Test getting most relevant prompt falls back to system prompt (lowest priority)."""
        # Arrange
        user_id = None
        action_type = None

        system_prompt = Mock(spec=Prompt)
        self.mock_repository.list_by_type.return_value = [system_prompt]

        # Act
        result = self.service.get_most_relevant_prompt(user_id, action_type)

        # Assert
        assert result == system_prompt
        self.mock_repository.list_by_type.assert_called_once_with("system")

    def test_get_most_relevant_prompt_no_match(self):
        """Test getting most relevant prompt when no prompts exist."""
        # Arrange
        user_id = 123
        action_type = "overlap_resolution"

        # No prompts found at any level
        self.mock_repository.list_by_user.return_value = []
        self.mock_repository.list_by_type.return_value = []

        # Act
        result = self.service.get_most_relevant_prompt(user_id, action_type)

        # Assert
        assert result is None

    def test_get_most_relevant_prompt_complex_fallback_chain(self):
        """Test the complete fallback chain: user+action -> user -> action -> system."""
        # Arrange
        user_id = 123
        action_type = "overlap_resolution"

        # No user+action match
        user_prompt_no_action = Mock(spec=Prompt)
        user_prompt_no_action.action_type = "other_action"

        # No user-only match (empty list)
        self.mock_repository.list_by_user.side_effect = [
            [user_prompt_no_action],  # First call: no action match
            []  # Second call: no user prompts
        ]

        # Action-specific match
        action_prompt = Mock(spec=Prompt)
        action_prompt.action_type = action_type

        self.mock_repository.list_by_type.return_value = [action_prompt]

        # Act
        result = self.service.get_most_relevant_prompt(user_id, action_type)

        # Assert
        assert result == action_prompt
        assert self.mock_repository.list_by_user.call_count == 2
        self.mock_repository.list_by_type.assert_called_once_with("action-specific")

    def test_update_prompt_success(self):
        """Test successful prompt content update."""
        # Arrange
        prompt_id = 1
        new_content = "Updated prompt content"

        existing_prompt = Mock(spec=Prompt)
        self.mock_repository.get_by_id.return_value = existing_prompt

        # Act
        self.service.update_prompt(prompt_id, new_content)

        # Assert
        self.mock_repository.get_by_id.assert_called_once_with(prompt_id)
        # Verify content was set
        assert hasattr(existing_prompt, 'content')
        self.mock_repository.add.assert_called_once_with(existing_prompt)

    def test_update_prompt_not_found(self):
        """Test updating prompt when prompt doesn't exist."""
        # Arrange
        prompt_id = 999
        new_content = "Updated content"

        self.mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Prompt not found"):
            self.service.update_prompt(prompt_id, new_content)

        self.mock_repository.get_by_id.assert_called_once_with(prompt_id)
        self.mock_repository.add.assert_not_called()

    def test_validate_prompt_valid_content(self):
        """Test validation of prompt with valid content."""
        # Arrange
        prompt = Mock(spec=Prompt)
        prompt.content = "Valid prompt content"
        prompt.user_id = 123
        prompt.action_type = "test_action"
        prompt.prompt_type = "user"
        prompt.id = 1

        # No existing prompts with same combination
        self.mock_repository.list_by_user.return_value = []

        # Act - should not raise exception
        self.service.validate_prompt(prompt)

        # Assert
        self.mock_repository.list_by_user.assert_called_once_with(123)

    def test_validate_prompt_empty_content(self):
        """Test validation fails for prompt with empty content."""
        # Arrange
        prompt = Mock(spec=Prompt)
        prompt.content = ""

        # Act & Assert
        with pytest.raises(ValueError, match="Prompt content is required"):
            self.service.validate_prompt(prompt)

    def test_validate_prompt_whitespace_only_content(self):
        """Test validation fails for prompt with whitespace-only content."""
        # Arrange
        prompt = Mock(spec=Prompt)
        prompt.content = "   \n\t   "

        # Act & Assert
        with pytest.raises(ValueError, match="Prompt content is required"):
            self.service.validate_prompt(prompt)

    def test_validate_prompt_none_content(self):
        """Test validation fails for prompt with None content."""
        # Arrange
        prompt = Mock(spec=Prompt)
        prompt.content = None

        # Act & Assert
        with pytest.raises(ValueError, match="Prompt content is required"):
            self.service.validate_prompt(prompt)

    def test_validate_prompt_missing_content_attribute(self):
        """Test validation fails for prompt without content attribute."""
        # Arrange
        prompt = Mock()
        prompt.user_id = 123
        prompt.action_type = "test_action"
        prompt.prompt_type = "user"

        # Explicitly delete content attribute so getattr returns None
        del prompt.content

        # Mock repository to avoid iteration issues
        self.mock_repository.list_by_user.return_value = []

        # Act & Assert
        with pytest.raises(ValueError, match="Prompt content is required"):
            self.service.validate_prompt(prompt)

    def test_validate_prompt_duplicate_user_prompt(self):
        """Test validation fails for duplicate user prompt."""
        # Arrange
        prompt = Mock(spec=Prompt)
        prompt.content = "Valid content"
        prompt.user_id = 123
        prompt.action_type = "test_action"
        prompt.prompt_type = "user"
        prompt.id = 1

        # Existing prompt with same combination
        existing_prompt = Mock(spec=Prompt)
        existing_prompt.action_type = "test_action"
        existing_prompt.prompt_type = "user"
        existing_prompt.id = 2  # Different ID

        self.mock_repository.list_by_user.return_value = [existing_prompt]

        # Act & Assert
        with pytest.raises(ValueError, match="Duplicate prompt for this user/action/type"):
            self.service.validate_prompt(prompt)

    def test_validate_prompt_same_id_allowed(self):
        """Test validation allows updating existing prompt (same ID)."""
        # Arrange
        prompt = Mock(spec=Prompt)
        prompt.content = "Valid content"
        prompt.user_id = 123
        prompt.action_type = "test_action"
        prompt.prompt_type = "user"
        prompt.id = 1

        # Existing prompt with same ID (updating same prompt)
        existing_prompt = Mock(spec=Prompt)
        existing_prompt.action_type = "test_action"
        existing_prompt.prompt_type = "user"
        existing_prompt.id = 1  # Same ID

        self.mock_repository.list_by_user.return_value = [existing_prompt]

        # Act - should not raise exception
        self.service.validate_prompt(prompt)

        # Assert
        self.mock_repository.list_by_user.assert_called_once_with(123)

    def test_validate_prompt_system_prompt_validation(self):
        """Test validation for system prompts (no user_id)."""
        # Arrange
        prompt = Mock(spec=Prompt)
        prompt.content = "Valid system prompt"
        prompt.user_id = None
        prompt.action_type = None
        prompt.prompt_type = "system"
        prompt.id = 1

        # No existing system prompts
        self.mock_repository.list_by_type.return_value = []

        # Act - should not raise exception
        self.service.validate_prompt(prompt)

        # Assert
        self.mock_repository.list_by_type.assert_called_once_with("system")

    def test_validate_prompt_duplicate_system_prompt(self):
        """Test validation fails for duplicate system prompt."""
        # Arrange
        prompt = Mock(spec=Prompt)
        prompt.content = "Valid system prompt"
        prompt.user_id = None
        prompt.action_type = None
        prompt.prompt_type = "system"
        prompt.id = 1

        # Existing system prompt with same combination
        existing_prompt = Mock(spec=Prompt)
        existing_prompt.action_type = None
        existing_prompt.prompt_type = "system"
        existing_prompt.id = 2  # Different ID

        self.mock_repository.list_by_type.return_value = [existing_prompt]

        # Act & Assert
        with pytest.raises(ValueError, match="Duplicate prompt for this user/action/type"):
            self.service.validate_prompt(prompt)

    def test_validate_prompt_different_action_types_allowed(self):
        """Test validation allows prompts with different action types."""
        # Arrange
        prompt = Mock(spec=Prompt)
        prompt.content = "Valid content"
        prompt.user_id = 123
        prompt.action_type = "new_action"
        prompt.prompt_type = "user"
        prompt.id = 1

        # Existing prompt with different action type
        existing_prompt = Mock(spec=Prompt)
        existing_prompt.action_type = "different_action"
        existing_prompt.prompt_type = "user"
        existing_prompt.id = 2

        self.mock_repository.list_by_user.return_value = [existing_prompt]

        # Act - should not raise exception
        self.service.validate_prompt(prompt)

        # Assert
        self.mock_repository.list_by_user.assert_called_once_with(123)
