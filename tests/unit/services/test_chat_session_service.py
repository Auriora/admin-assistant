"""
Unit tests for ChatSessionService

Tests the business logic for managing ChatSession entities including
CRUD operations, message handling, session state management, and entity associations.
"""

import pytest
from unittest.mock import Mock, MagicMock
from core.services.chat_session_service import ChatSessionService
from core.models.chat_session import ChatSession
from core.repositories.chat_session_repository import ChatSessionRepository
from core.services.entity_association_service import EntityAssociationService


class TestChatSessionService:
    """Test suite for ChatSessionService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_repository = Mock(spec=ChatSessionRepository)
        self.mock_association_service = Mock(spec=EntityAssociationService)
        self.service = ChatSessionService(
            repository=self.mock_repository,
            association_service=self.mock_association_service
        )
    
    def test_init_with_dependencies(self):
        """Test service initialization with provided dependencies"""
        service = ChatSessionService(
            repository=self.mock_repository,
            association_service=self.mock_association_service
        )
        assert service.repository == self.mock_repository
        assert service.association_service == self.mock_association_service
    
    def test_init_with_default_dependencies(self):
        """Test service initialization with default dependencies"""
        service = ChatSessionService()
        assert service.repository is not None
        assert service.association_service is not None
    
    def test_get_by_id(self):
        """Test retrieving chat session by ID"""
        # Arrange
        session_id = 123
        expected_session = Mock(spec=ChatSession)
        self.mock_repository.get_by_id.return_value = expected_session
        
        # Act
        result = self.service.get_by_id(session_id)
        
        # Assert
        assert result == expected_session
        self.mock_repository.get_by_id.assert_called_once_with(session_id)
    
    def test_get_by_id_not_found(self):
        """Test retrieving non-existent chat session"""
        # Arrange
        session_id = 999
        self.mock_repository.get_by_id.return_value = None
        
        # Act
        result = self.service.get_by_id(session_id)
        
        # Assert
        assert result is None
        self.mock_repository.get_by_id.assert_called_once_with(session_id)
    
    def test_create(self):
        """Test creating a new chat session"""
        # Arrange
        session = Mock(spec=ChatSession)
        
        # Act
        self.service.create(session)
        
        # Assert
        self.mock_repository.add.assert_called_once_with(session)
    
    def test_list_by_user(self):
        """Test listing chat sessions for a specific user"""
        # Arrange
        user_id = 456
        expected_sessions = [Mock(spec=ChatSession), Mock(spec=ChatSession)]
        self.mock_repository.list_by_user.return_value = expected_sessions
        
        # Act
        result = self.service.list_by_user(user_id)
        
        # Assert
        assert result == expected_sessions
        self.mock_repository.list_by_user.assert_called_once_with(user_id)
    
    def test_delete(self):
        """Test deleting a chat session"""
        # Arrange
        session_id = 123
        
        # Act
        self.service.delete(session_id)
        
        # Assert
        self.mock_repository.delete.assert_called_once_with(session_id)
    
    def test_append_message_success(self):
        """Test appending a message to an existing session"""
        # Arrange
        session_id = 123
        message = {"sender": "user", "content": "Hello", "timestamp": "2025-01-01T10:00:00Z"}

        mock_session = Mock(spec=ChatSession)
        existing_messages = [{"sender": "system", "content": "Welcome"}]
        mock_session.messages = existing_messages.copy()  # Use copy to avoid mutation

        self.mock_repository.get_by_id.return_value = mock_session

        # Act
        self.service.append_message(session_id, message)

        # Assert
        self.mock_repository.get_by_id.assert_called_once_with(session_id)
        # Verify message was appended
        expected_messages = [{"sender": "system", "content": "Welcome"}, message]
        assert mock_session.messages == expected_messages
        self.mock_repository.add.assert_called_once_with(mock_session)
    
    def test_append_message_no_existing_messages(self):
        """Test appending a message when session has no existing messages"""
        # Arrange
        session_id = 123
        message = {"sender": "user", "content": "Hello"}
        
        mock_session = Mock(spec=ChatSession)
        # Simulate getattr returning None for messages
        mock_session.messages = None
        
        self.mock_repository.get_by_id.return_value = mock_session
        
        # Act
        self.service.append_message(session_id, message)
        
        # Assert
        self.mock_repository.get_by_id.assert_called_once_with(session_id)
        assert mock_session.messages == [message]
        self.mock_repository.add.assert_called_once_with(mock_session)
    
    def test_append_message_session_not_found(self):
        """Test appending message when session doesn't exist"""
        # Arrange
        session_id = 999
        message = {"sender": "user", "content": "Hello"}
        self.mock_repository.get_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="ChatSession not found"):
            self.service.append_message(session_id, message)
        
        self.mock_repository.get_by_id.assert_called_once_with(session_id)
        self.mock_repository.add.assert_not_called()
    
    def test_get_chat_history_success(self):
        """Test retrieving chat history for an existing session"""
        # Arrange
        session_id = 123
        expected_messages = [
            {"sender": "user", "content": "Hello"},
            {"sender": "assistant", "content": "Hi there!"}
        ]
        
        mock_session = Mock(spec=ChatSession)
        mock_session.messages = expected_messages
        
        self.mock_repository.get_by_id.return_value = mock_session
        
        # Act
        result = self.service.get_chat_history(session_id)
        
        # Assert
        assert result == expected_messages
        self.mock_repository.get_by_id.assert_called_once_with(session_id)
    
    def test_get_chat_history_no_messages(self):
        """Test retrieving chat history when session has no messages"""
        # Arrange
        session_id = 123
        
        mock_session = Mock(spec=ChatSession)
        mock_session.messages = None
        
        self.mock_repository.get_by_id.return_value = mock_session
        
        # Act
        result = self.service.get_chat_history(session_id)
        
        # Assert
        assert result == []
        self.mock_repository.get_by_id.assert_called_once_with(session_id)
    
    def test_get_chat_history_session_not_found(self):
        """Test retrieving chat history when session doesn't exist"""
        # Arrange
        session_id = 999
        self.mock_repository.get_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="ChatSession not found"):
            self.service.get_chat_history(session_id)
        
        self.mock_repository.get_by_id.assert_called_once_with(session_id)
    
    def test_close_session_success(self):
        """Test closing an existing session"""
        # Arrange
        session_id = 123
        mock_session = Mock(spec=ChatSession)
        mock_session.status = "open"
        
        self.mock_repository.get_by_id.return_value = mock_session
        
        # Act
        self.service.close_session(session_id)
        
        # Assert
        self.mock_repository.get_by_id.assert_called_once_with(session_id)
        assert mock_session.status == "closed"
        self.mock_repository.add.assert_called_once_with(mock_session)
    
    def test_close_session_not_found(self):
        """Test closing a non-existent session"""
        # Arrange
        session_id = 999
        self.mock_repository.get_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="ChatSession not found"):
            self.service.close_session(session_id)
        
        self.mock_repository.get_by_id.assert_called_once_with(session_id)
        self.mock_repository.add.assert_not_called()
    
    def test_reopen_session_success(self):
        """Test reopening a closed session"""
        # Arrange
        session_id = 123
        mock_session = Mock(spec=ChatSession)
        mock_session.status = "closed"
        
        self.mock_repository.get_by_id.return_value = mock_session
        
        # Act
        self.service.reopen_session(session_id)
        
        # Assert
        self.mock_repository.get_by_id.assert_called_once_with(session_id)
        assert mock_session.status == "open"
        self.mock_repository.add.assert_called_once_with(mock_session)
    
    def test_reopen_session_not_found(self):
        """Test reopening a non-existent session"""
        # Arrange
        session_id = 999
        self.mock_repository.get_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="ChatSession not found"):
            self.service.reopen_session(session_id)
        
        self.mock_repository.get_by_id.assert_called_once_with(session_id)
        self.mock_repository.add.assert_not_called()
    
    def test_list_by_action_success(self):
        """Test listing chat sessions related to a specific action"""
        # Arrange
        action_id = 456
        
        # Mock entity associations
        mock_association1 = Mock()
        mock_association1.source_type = "chat_session"
        mock_association1.source_id = "123"
        
        mock_association2 = Mock()
        mock_association2.source_type = "chat_session"
        mock_association2.source_id = "124"
        
        mock_association3 = Mock()
        mock_association3.source_type = "other_entity"
        mock_association3.source_id = "999"
        
        self.mock_association_service.list_by_target.return_value = [
            mock_association1, mock_association2, mock_association3
        ]
        
        # Mock chat sessions
        mock_session1 = Mock(spec=ChatSession)
        mock_session2 = Mock(spec=ChatSession)
        
        self.mock_repository.get_by_id.side_effect = lambda sid: {
            123: mock_session1,
            124: mock_session2
        }.get(sid)
        
        # Act
        result = self.service.list_by_action(action_id)
        
        # Assert
        self.mock_association_service.list_by_target.assert_called_once_with("action_log", action_id)
        assert result == [mock_session1, mock_session2]
    
    def test_list_by_action_no_associations(self):
        """Test listing chat sessions when no associations exist"""
        # Arrange
        action_id = 456
        self.mock_association_service.list_by_target.return_value = []
        
        # Act
        result = self.service.list_by_action(action_id)
        
        # Assert
        self.mock_association_service.list_by_target.assert_called_once_with("action_log", action_id)
        assert result == []
    
    def test_list_by_action_with_missing_sessions(self):
        """Test listing chat sessions when some referenced sessions don't exist"""
        # Arrange
        action_id = 456
        
        mock_association = Mock()
        mock_association.source_type = "chat_session"
        mock_association.source_id = "999"  # Non-existent session
        
        self.mock_association_service.list_by_target.return_value = [mock_association]
        self.mock_repository.get_by_id.return_value = None
        
        # Act
        result = self.service.list_by_action(action_id)
        
        # Assert
        self.mock_association_service.list_by_target.assert_called_once_with("action_log", action_id)
        assert result == []
