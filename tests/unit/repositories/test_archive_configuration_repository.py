"""
Unit tests for ArchiveConfigurationRepository.
"""
import pytest
from datetime import datetime, UTC
from core.models.archive_configuration import ArchiveConfiguration
from core.repositories.archive_configuration_repository import ArchiveConfigurationRepository


@pytest.mark.unit
@pytest.mark.db
class TestArchiveConfigurationRepository:
    """Test cases for ArchiveConfigurationRepository."""

    @pytest.fixture
    def repository(self, db_session, test_user):
        """Create repository instance."""
        return ArchiveConfigurationRepository(session=db_session, user=test_user)

    def test_create_archive_configuration(self, repository, test_user):
        """Test creating a new archive configuration."""
        config = ArchiveConfiguration(
            user_id=test_user.id,
            name="Test Config",
            source_calendar_uri="msgraph://test-calendar",
            archive_calendar_id="archive-calendar-id",
            is_active=True
        )
        
        result = repository.add(config)
        
        assert result.id is not None
        assert result.name == "Test Config"
        assert result.user_id == test_user.id
        assert result.is_active is True

    def test_get_by_id(self, repository, test_archive_config):
        """Test retrieving archive configuration by ID."""
        result = repository.get_by_id(test_archive_config.id)
        
        assert result is not None
        assert result.id == test_archive_config.id
        assert result.name == test_archive_config.name

    def test_get_by_id_not_found(self, repository):
        """Test retrieving non-existent archive configuration."""
        result = repository.get_by_id(99999)
        
        assert result is None

    def test_list_for_user(self, repository, test_user, db_session):
        """Test listing archive configurations for a user."""
        # Create multiple configurations
        config1 = ArchiveConfiguration(
            user_id=test_user.id,
            name="Config 1",
            source_calendar_uri="msgraph://calendar1",
            archive_calendar_id="archive1",
            is_active=True
        )
        config2 = ArchiveConfiguration(
            user_id=test_user.id,
            name="Config 2",
            source_calendar_uri="msgraph://calendar2",
            archive_calendar_id="archive2",
            is_active=False
        )
        
        db_session.add_all([config1, config2])
        db_session.commit()
        
        results = repository.list()
        
        assert len(results) >= 2
        config_names = [c.name for c in results]
        assert "Config 1" in config_names
        assert "Config 2" in config_names

    def test_list_active_only(self, repository, test_user, db_session):
        """Test listing only active archive configurations."""
        # Create active and inactive configurations
        active_config = ArchiveConfiguration(
            user_id=test_user.id,
            name="Active Config",
            source_calendar_uri="msgraph://calendar1",
            archive_calendar_id="archive1",
            is_active=True
        )
        inactive_config = ArchiveConfiguration(
            user_id=test_user.id,
            name="Inactive Config",
            source_calendar_uri="msgraph://calendar2",
            archive_calendar_id="archive2",
            is_active=False
        )
        
        db_session.add_all([active_config, inactive_config])
        db_session.commit()
        
        results = repository.list_active()
        
        assert len(results) >= 1
        assert all(c.is_active for c in results)
        config_names = [c.name for c in results]
        assert "Active Config" in config_names
        assert "Inactive Config" not in config_names

    def test_update_archive_configuration(self, repository, test_archive_config):
        """Test updating an archive configuration."""
        test_archive_config.name = "Updated Config"
        test_archive_config.is_active = False
        
        repository.update(test_archive_config)
        
        updated = repository.get_by_id(test_archive_config.id)
        assert updated.name == "Updated Config"
        assert updated.is_active is False

    def test_delete_archive_configuration(self, repository, test_archive_config):
        """Test deleting an archive configuration."""
        config_id = test_archive_config.id
        
        repository.delete(config_id)
        
        result = repository.get_by_id(config_id)
        assert result is None

    def test_get_by_name(self, repository, test_archive_config):
        """Test retrieving archive configuration by name."""
        result = repository.get_by_name(test_archive_config.name)
        
        assert result is not None
        assert result.id == test_archive_config.id
        assert result.name == test_archive_config.name

    def test_get_by_name_not_found(self, repository):
        """Test retrieving non-existent archive configuration by name."""
        result = repository.get_by_name("Non-existent Config")
        
        assert result is None

    def test_user_isolation(self, db_session, test_user):
        """Test that users can only see their own configurations."""
        # Create another user
        other_user = User(
            email="other@example.com",
            name="Other User",
            ms_user_id="other-ms-user-id"
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Create configurations for both users
        user1_config = ArchiveConfiguration(
            user_id=test_user.id,
            name="User 1 Config",
            source_calendar_uri="msgraph://calendar1",
            archive_calendar_id="archive1",
            is_active=True
        )
        user2_config = ArchiveConfiguration(
            user_id=other_user.id,
            name="User 2 Config",
            source_calendar_uri="msgraph://calendar2",
            archive_calendar_id="archive2",
            is_active=True
        )
        
        db_session.add_all([user1_config, user2_config])
        db_session.commit()
        
        # Test user 1 repository
        repo1 = ArchiveConfigurationRepository(session=db_session, user=test_user)
        results1 = repo1.list()
        config_names1 = [c.name for c in results1]
        
        assert "User 1 Config" in config_names1
        assert "User 2 Config" not in config_names1
        
        # Test user 2 repository
        repo2 = ArchiveConfigurationRepository(session=db_session, user=other_user)
        results2 = repo2.list()
        config_names2 = [c.name for c in results2]
        
        assert "User 2 Config" in config_names2
        assert "User 1 Config" not in config_names2
