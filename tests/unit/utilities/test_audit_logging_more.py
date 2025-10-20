import types
from core.utilities import audit_logging_utility as al


class FakeAuditService:
    def __init__(self):
        self.calls = []

    def log_operation(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(id=111, **kwargs)

    def generate_correlation_id(self):
        return "gen-corr"


def test_audit_operation_resource_id_extraction(monkeypatch):
    fake = FakeAuditService()
    monkeypatch.setattr(al, 'AuditLogService', lambda: fake)

    @al.audit_operation('act', 'doit')
    def f_cal(user_id, calendar_id=None):
        return True

    f_cal(1, calendar_id='cal-1')
    assert fake.calls
    assert fake.calls[-1]['resource_id'] == 'cal-1'

    fake.calls.clear()

    @al.audit_operation('act', 'doit')
    def f_appt(user_id, appointment_id=None):
        return True

    f_appt(2, appointment_id='appt-2')
    assert fake.calls
    assert fake.calls[-1]['resource_id'] == 'appt-2'

    fake.calls.clear()

    @al.audit_operation('act', 'doit')
    def f_action(user_id, action_log_id=None):
        return True

    f_action(3, action_log_id=55)
    assert fake.calls
    # action_log_id should be converted to str
    assert fake.calls[-1]['resource_id'] == '55'


def test_result_with_dict_and_result_with_object(monkeypatch):
    fake = FakeAuditService()
    monkeypatch.setattr(al, 'AuditLogService', lambda: fake)

    class R:
        def __init__(self):
            self.x = 1

    @al.audit_operation('act', 'doit')
    def f_obj(user_id):
        return R()

    f_obj(1)
    assert fake.calls
    # response data should have result_type when result has __dict__
    assert 'result_type' in fake.calls[-1]['response_data']


def test_set_request_and_response_data_sanitization_failure(monkeypatch):
    fake = FakeAuditService()
    monkeypatch.setattr(al, 'AuditLogService', lambda: fake)

    # Make sanitize_for_audit raise inside audit_logging_utility
    monkeypatch.setattr(al, 'sanitize_for_audit', lambda v: (_ for _ in ()).throw(Exception('boom')))

    ctx = al.AuditContext(audit_service=fake, user_id=1, action_type='a', operation='op')
    with ctx:
        # set_request_data should catch the exception and set an error dict
        ctx.set_request_data({'a': 1})
        assert isinstance(ctx.request_data, dict)
        assert 'error' in ctx.request_data or ctx.request_data.get('error', None) is not None

        # set_response_data should also catch the exception
        ctx.set_response_data({'r': 2})
        assert isinstance(ctx.response_data, dict)
        assert 'error' in ctx.response_data or ctx.response_data.get('error', None) is not None


def test_update_resource_and_batch_end_statuses(monkeypatch):
    fake = FakeAuditService()
    monkeypatch.setattr(al, 'AuditLogService', lambda: fake)

    # update_resource
    ctx = al.AuditContext(audit_service=fake, user_id=1, action_type='a', operation='op')
    ctx.update_resource('calendar', 'cal-1')
    assert ctx.resource_type == 'calendar'
    assert ctx.resource_id == 'cal-1'

    # batch end statuses
    fake.calls.clear()
    al.AuditLogHelper.log_batch_operation_end(1, 'op', 10, success_count=5, failure_count=0, correlation_id='c')
    assert fake.calls[-1]['status'] == 'success'

    fake.calls.clear()
    al.AuditLogHelper.log_batch_operation_end(1, 'op', 10, success_count=3, failure_count=2, correlation_id='c')
    assert fake.calls[-1]['status'] == 'partial'

    fake.calls.clear()
    al.AuditLogHelper.log_batch_operation_end(1, 'op', 10, success_count=0, failure_count=2, correlation_id='c')
    assert fake.calls[-1]['status'] == 'failure'
