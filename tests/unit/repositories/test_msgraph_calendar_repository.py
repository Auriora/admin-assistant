import pytest
from core.repositories.calendar_repository_msgraph import MSGraphCalendarRepository
from core.models.calendar import Calendar
from types import SimpleNamespace
from tests.mocks.msgraph_mocks import MockMSGraphClient
from unittest.mock import MagicMock

class MockUser:
    def __init__(self, id=1, email="test@example.com"):
        self.id = id
        self.email = email

@pytest.fixture
def mock_user():
    return MockUser()

@pytest.fixture
def mock_msgraph_client():
    # For calendar tests, events are not needed, so pass empty list
    return MockMSGraphClient([])

@pytest.fixture
def repo(mock_msgraph_client, mock_user):
    return MSGraphCalendarRepository(mock_msgraph_client, mock_user)

def make_calendar(user_id=1, ms_calendar_id="abc123", name="Test Calendar", description="A test calendar", is_primary=True, is_active=True):
    return Calendar(
        user_id=user_id,
        ms_calendar_id=ms_calendar_id,
        name=name,
        description=description,
        is_primary=is_primary,
        is_active=is_active
    )

def test_list_returns_calendars(repo):
    """Test that list() returns a list of Calendar objects (mocked)."""
    calendars = repo.list()
    assert isinstance(calendars, list)
    for cal in calendars:
        assert isinstance(cal, Calendar)

def test_get_by_id_returns_calendar_or_none(repo):
    """Test get_by_id returns a Calendar or None if not found (mocked)."""
    result = repo.get_by_id("nonexistent")
    assert result is None or isinstance(result, Calendar)

def test_add_calls_msgraph(mock_user):
    client = MagicMock()
    client.users.by_user_id.return_value.calendars.post = MagicMock()
    repo = MSGraphCalendarRepository(client, mock_user)
    cal = make_calendar(user_id=mock_user.id)
    repo.add(cal)
    client.users.by_user_id.return_value.calendars.post.assert_called_once()

def test_update_calls_msgraph(mock_user):
    client = MagicMock()
    client.users.by_user_id.return_value.calendars.by_calendar_id.return_value.patch = MagicMock()
    repo = MSGraphCalendarRepository(client, mock_user)
    cal = make_calendar(user_id=mock_user.id)
    repo.update(cal)
    client.users.by_user_id.return_value.calendars.by_calendar_id.return_value.patch.assert_called_once()

def test_delete_calls_msgraph(mock_user):
    client = MagicMock()
    client.users.by_user_id.return_value.calendars.by_calendar_id.return_value.delete = MagicMock()
    repo = MSGraphCalendarRepository(client, mock_user)
    cal_id = "abc123"
    repo.delete(cal_id)
    client.users.by_user_id.return_value.calendars.by_calendar_id.return_value.delete.assert_called_once()

def test_error_handling_on_get_by_id(monkeypatch, mock_user):
    client = MagicMock()
    def fake_get():
        raise Exception("fail")
    client.users.by_user_id.return_value.calendars.by_calendar_id.return_value.get = fake_get
    repo = MSGraphCalendarRepository(client, mock_user)
    with pytest.raises(RuntimeError):
        repo.get_by_id("fail")

def test_error_handling_on_add(monkeypatch, mock_user):
    client = MagicMock()
    def fake_post(*args, **kwargs):
        raise Exception("fail")
    client.users.by_user_id.return_value.calendars.post = fake_post
    repo = MSGraphCalendarRepository(client, mock_user)
    cal = make_calendar(user_id=mock_user.id)
    with pytest.raises(RuntimeError):
        repo.add(cal)

def test_error_handling_on_update(monkeypatch, mock_user):
    client = MagicMock()
    def fake_patch(*args, **kwargs):
        raise Exception("fail")
    client.users.by_user_id.return_value.calendars.by_calendar_id.return_value.patch = fake_patch
    repo = MSGraphCalendarRepository(client, mock_user)
    cal = make_calendar(user_id=mock_user.id)
    with pytest.raises(RuntimeError):
        repo.update(cal)

def test_error_handling_on_delete(monkeypatch, mock_user):
    client = MagicMock()
    def fake_delete(*args, **kwargs):
        raise Exception("fail")
    client.users.by_user_id.return_value.calendars.by_calendar_id.return_value.delete = fake_delete
    repo = MSGraphCalendarRepository(client, mock_user)
    cal_id = "abc123"
    with pytest.raises(RuntimeError):
        repo.delete(cal_id) 