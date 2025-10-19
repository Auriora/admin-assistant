import pytest
from unittest.mock import Mock

from core.models.audit_log import AuditLog
from core.repositories.audit_log_repository import AuditLogRepository


@pytest.fixture
def mock_session():
    return Mock()


@pytest.fixture
def repository(mock_session):
    return AuditLogRepository(session=mock_session)


def test_add_audit_log(repository, mock_session):
    audit_log = AuditLog(
        user_id=1,
        action_type='test',
        operation='test_operation',
        status='success'
    )

    mock_session.refresh = Mock()
    result = repository.add(audit_log)

    mock_session.add.assert_called_once_with(audit_log)
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once_with(audit_log)
    assert result == audit_log


def test_search_with_filters(repository, mock_session):
    filters = {
        'user_id': 1,
        'action_type': 'archive',
        'status': 'success'
    }

    mock_query = Mock()
    mock_session.query.return_value = mock_query
    mock_query.filter_by.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value = []

    repository.search(filters)

    mock_session.query.assert_called_once()
    assert mock_query.filter_by.call_count >= 3
    mock_query.order_by.assert_called_once()
    mock_query.all.assert_called_once()

