"""
Unit tests for ActionLogService

Tests the business logic for managing ActionLog entities including
state transitions, recommendations, and entity associations.
"""

import pytest
from unittest.mock import Mock, MagicMock
from core.services.action_log_service import ActionLogService
from core.models.action_log import ActionLog
from core.repositories.action_log_repository import ActionLogRepository
from core.services.entity_association_service import EntityAssociationService


class TestActionLogService:
    """Test suite for ActionLogService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_repository = Mock(spec=ActionLogRepository)
        self.mock_association_service = Mock(spec=EntityAssociationService)
        self.service = ActionLogService(
            repository=self.mock_repository,
            association_service=self.mock_association_service
        )
    
    def test_init_with_dependencies(self):
        """Test service initialization with provided dependencies"""
        service = ActionLogService(
            repository=self.mock_repository,
            association_service=self.mock_association_service
        )
        assert service.repository == self.mock_repository
        assert service.association_service == self.mock_association_service
    
    def test_init_with_default_dependencies(self):
        """Test service initialization with default dependencies"""
        service = ActionLogService()
        assert service.repository is not None
        assert service.association_service is not None
    
    def test_get_by_id(self):
        """Test retrieving action log by ID"""
        # Arrange
        log_id = 123
        expected_log = Mock(spec=ActionLog)
        self.mock_repository.get_by_id.return_value = expected_log
        
        # Act
        result = self.service.get_by_id(log_id)
        
        # Assert
        assert result == expected_log
        self.mock_repository.get_by_id.assert_called_once_with(log_id)
    
    def test_get_by_id_not_found(self):
        """Test retrieving non-existent action log"""
        # Arrange
        log_id = 999
        self.mock_repository.get_by_id.return_value = None
        
        # Act
        result = self.service.get_by_id(log_id)
        
        # Assert
        assert result is None
        self.mock_repository.get_by_id.assert_called_once_with(log_id)
    
    def test_create(self):
        """Test creating a new action log"""
        # Arrange
        log = Mock(spec=ActionLog)
        
        # Act
        self.service.create(log)
        
        # Assert
        self.mock_repository.add.assert_called_once_with(log)
    
    def test_list_for_user(self):
        """Test listing action logs for a specific user"""
        # Arrange
        user_id = 456
        expected_logs = [Mock(spec=ActionLog), Mock(spec=ActionLog)]
        self.mock_repository.list_for_user.return_value = expected_logs
        
        # Act
        result = self.service.list_for_user(user_id)
        
        # Assert
        assert result == expected_logs
        self.mock_repository.list_for_user.assert_called_once_with(user_id)
    
    def test_list_by_state(self):
        """Test listing action logs by state"""
        # Arrange
        state = "pending"
        expected_logs = [Mock(spec=ActionLog)]
        self.mock_repository.list_by_state.return_value = expected_logs
        
        # Act
        result = self.service.list_by_state(state)
        
        # Assert
        assert result == expected_logs
        self.mock_repository.list_by_state.assert_called_once_with(state)
    
    def test_transition_state_success(self):
        """Test successful state transition"""
        # Arrange
        log_id = 123
        new_state = "resolved"
        mock_log = Mock(spec=ActionLog)
        self.mock_repository.get_by_id.return_value = mock_log
        
        # Act
        self.service.transition_state(log_id, new_state)
        
        # Assert
        self.mock_repository.get_by_id.assert_called_once_with(log_id)
        # Check that state was set (using setattr in the actual code)
        self.mock_repository.update.assert_called_once_with(mock_log)
    
    def test_transition_state_log_not_found(self):
        """Test state transition when log doesn't exist"""
        # Arrange
        log_id = 999
        new_state = "resolved"
        self.mock_repository.get_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="ActionLog not found"):
            self.service.transition_state(log_id, new_state)
        
        self.mock_repository.get_by_id.assert_called_once_with(log_id)
        self.mock_repository.update.assert_not_called()
    
    def test_attach_recommendations(self):
        """Test attaching AI recommendations to action log"""
        # Arrange
        log_id = 123
        recommendations = {"suggestion": "merge appointments", "confidence": 0.85}
        
        # Act
        self.service.attach_recommendations(log_id, recommendations)
        
        # Assert
        self.mock_repository.update_recommendations.assert_called_once_with(
            log_id, recommendations
        )
    
    def test_summarize_actions_empty(self):
        """Test summarizing actions when no actions exist"""
        # Arrange
        user_id = 456
        self.mock_repository.list_for_user.return_value = []
        
        # Act
        result = self.service.summarize_actions(user_id)
        
        # Assert
        assert result == []
        self.mock_repository.list_for_user.assert_called_once_with(user_id)
    
    def test_summarize_actions_with_data(self):
        """Test summarizing actions with various states"""
        # Arrange
        user_id = 456
        
        # Create mock actions with different states
        action1 = Mock(spec=ActionLog)
        action1.state = "pending"
        
        action2 = Mock(spec=ActionLog)
        action2.state = "resolved"
        
        action3 = Mock(spec=ActionLog)
        action3.state = "pending"
        
        # Mock action without state attribute
        action4 = Mock(spec=ActionLog)
        del action4.state  # Remove state attribute to test getattr fallback
        
        self.mock_repository.list_for_user.return_value = [action1, action2, action3, action4]
        
        # Act
        result = self.service.summarize_actions(user_id)
        
        # Assert
        assert len(result) == 3  # pending, resolved, unknown
        
        # Find each state group
        pending_group = next(group for group in result if group["state"] == "pending")
        resolved_group = next(group for group in result if group["state"] == "resolved")
        unknown_group = next(group for group in result if group["state"] == "unknown")
        
        assert len(pending_group["actions"]) == 2
        assert len(resolved_group["actions"]) == 1
        assert len(unknown_group["actions"]) == 1
        
        self.mock_repository.list_for_user.assert_called_once_with(user_id)
    
    def test_get_related_entities(self):
        """Test getting related entities for an action log"""
        # Arrange
        log_id = 123
        expected_entities = [("appointment", "456"), ("calendar", "789")]
        self.mock_association_service.get_related_entities.return_value = expected_entities
        
        # Act
        result = self.service.get_related_entities(log_id)
        
        # Assert
        assert result == expected_entities
        self.mock_association_service.get_related_entities.assert_called_once_with(
            "action_log", log_id
        )
