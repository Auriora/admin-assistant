from core.models.audit_log import AuditLog


def test_audit_log_creation_minimal_fields():
    audit_log = AuditLog(
        user_id=1,
        action_type='archive',
        operation='calendar_archive',
        status='success'
    )
    assert audit_log.user_id == 1
    assert audit_log.action_type == 'archive'
    assert audit_log.operation == 'calendar_archive'
    assert audit_log.status == 'success'


def test_audit_log_full_fields():
    audit_log = AuditLog(
        user_id=1,
        action_type='archive',
        operation='calendar_archive',
        resource_type='calendar',
        resource_id='test-calendar-123',
        status='success',
        message='ok',
        details={'archived_count': 1},
        duration_ms=1.2,
        correlation_id='corr-1'
    )
    assert audit_log.resource_type == 'calendar'
    assert audit_log.resource_id == 'test-calendar-123'
    assert audit_log.message == 'ok'
    assert audit_log.details == {'archived_count': 1}
    assert audit_log.duration_ms == 1.2
    assert audit_log.correlation_id == 'corr-1'

