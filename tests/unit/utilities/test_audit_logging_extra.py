import types
import pytest

from core.utilities import audit_logging_utility as al


class FakeAuditService:
    def __init__(self):
        self.calls = []

    def log_operation(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(id=999, **kwargs)

    def generate_correlation_id(self):
        return "fake-corr"


def test_audit_operation_decorator_various_user_extraction(monkeypatch):
    fake = FakeAuditService()
    monkeypatch.setattr(al, 'AuditLogService', lambda: fake)

    @al.audit_operation('act', 'doit')
    def f_positional_user(user_id, x):
        return x + 1

    res = f_positional_user(10, 2)
    assert res == 3
    assert fake.calls, "Audit service should have been called for positional user_id"
    fake.calls.clear()

    # user in kwargs
    @al.audit_operation('act', 'doit')
    def f_kw_user(x, user_id=None):
        return x * 2

    r = f_kw_user(5, user_id=7)
    assert r == 10
    assert fake.calls
    fake.calls.clear()

    # user object in kwargs (has id attr)
    class U: pass
    u = U(); u.id = 42

    @al.audit_operation('act', 'doit')
    def f_user_obj(x, user=None):
        return x

    r2 = f_user_obj(1, user=u)
    assert r2 == 1
    assert fake.calls
    fake.calls.clear()

    # auto_extract_user_id False -> no logging
    @al.audit_operation('act', 'doit', auto_extract_user_id=False)
    def f_no_user(x):
        return x

    rr = f_no_user(5)
    assert rr == 5
    assert not fake.calls


def test_audit_operation_with_correlation_param(monkeypatch):
    fake = FakeAuditService()
    monkeypatch.setattr(al, 'AuditLogService', lambda: fake)

    @al.audit_operation('act', 'doit', correlation_id_param='corr')
    def f_corr(user_id, corr=None):
        return True

    r = f_corr(1, corr='C123')
    assert r is True
    assert fake.calls
    assert fake.calls[-1].get('correlation_id') == 'C123'


def test_audit_context_failure_and_success(monkeypatch):
    fake = FakeAuditService()
    # use the fake directly
    ctx = al.AuditContext(audit_service=fake, user_id=1, action_type='a', operation='op')
    # success
    with ctx:
        pass
    assert fake.calls
    assert fake.calls[-1]['status'] == 'success'

    # failure inside context
    fake.calls.clear()

    def _invoke_failure():
        with al.AuditContext(audit_service=fake, user_id=2, action_type='a', operation='op2'):
            raise RuntimeError('boom')

    with pytest.raises(RuntimeError):
        _invoke_failure()
    assert fake.calls
    assert fake.calls[-1]['status'] == 'failure'
    assert 'error' in fake.calls[-1].get('details', {}) or 'details' in fake.calls[-1]


def test_auditloghelper_functions(monkeypatch):
    fake = FakeAuditService()
    monkeypatch.setattr(al, 'AuditLogService', lambda: fake)

    cid = al.AuditLogHelper.create_correlation_id()
    assert cid == 'fake-corr'

    fake.calls.clear()
    aid = al.AuditLogHelper.log_batch_operation_start(1, 'op', 3, 'corr')
    assert aid == 999
    assert fake.calls[-1]['action_type'] == 'batch_operation'

    fake.calls.clear()
    al.AuditLogHelper.log_batch_operation_end(1, 'op', aid, 2, 1, 'corr')
    assert fake.calls[-1]['action_type'] == 'batch_operation'
    assert fake.calls[-1]['details']['phase'] == 'end'

    fake.calls.clear()
    old = {'a': 1}
    new = {'a': 2}
    al.AuditLogHelper.log_data_modification(1, 'op', 'res', 'rid', old, new)
    assert fake.calls
    changes = fake.calls[-1]['details']['changes']
    assert 'a' in changes
