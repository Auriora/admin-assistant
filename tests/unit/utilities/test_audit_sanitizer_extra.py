import sys
import types
import pytest
import datetime

from core.utilities import audit_sanitizer as asanit


def _setup_fake_sqlalchemy(monkeypatch, inspect_func=None):
    """Install fake sqlalchemy packages into sys.modules with InstrumentedAttribute and inspect().
    Returns the InstrumentedAttribute class created for tests.
    """
    # Create module hierarchy: sqlalchemy, sqlalchemy.inspection, sqlalchemy.orm, sqlalchemy.orm.attributes
    sqlalchemy_mod = types.ModuleType("sqlalchemy")
    inspection_mod = types.ModuleType("sqlalchemy.inspection")
    orm_mod = types.ModuleType("sqlalchemy.orm")
    attributes_mod = types.ModuleType("sqlalchemy.orm.attributes")

    # Fake InstrumentedAttribute type
    class InstrumentedAttribute:
        pass

    attributes_mod.InstrumentedAttribute = InstrumentedAttribute

    # Default inspect behaviour if none provided
    if inspect_func is None:
        def inspect_func(cls):
            m = types.SimpleNamespace()
            m.primary_key = []
            return m

    inspection_mod.inspect = inspect_func

    # Insert into sys.modules so `from sqlalchemy.inspection import inspect` works
    monkeypatch.setitem(sys.modules, "sqlalchemy", sqlalchemy_mod)
    monkeypatch.setitem(sys.modules, "sqlalchemy.inspection", inspection_mod)
    monkeypatch.setitem(sys.modules, "sqlalchemy.orm", orm_mod)
    monkeypatch.setitem(sys.modules, "sqlalchemy.orm.attributes", attributes_mod)

    return InstrumentedAttribute


def test_other_model_pk_and_instrumented_exclusion(monkeypatch):
    """Exercise _sanitize_sqlalchemy_model for a non-special model, including InstrumentedAttribute exclusion
    and the inspect primary-key path.
    """
    # Setup inspect to return a mapper with a primary_key named 'id'
    def inspect_func(cls):
        pk_col = types.SimpleNamespace(name="id")
        m = types.SimpleNamespace()
        m.primary_key = [pk_col]
        return m

    InstrumentedAttribute = _setup_fake_sqlalchemy(monkeypatch, inspect_func=inspect_func)

    # Create a dummy model class with __table__ and various attributes
    class OtherModel:
        __table__ = types.SimpleNamespace(name="other_tbl")

        def __init__(self):
            self.id = 42
            # This should be excluded because it's an InstrumentedAttribute
            self.name = InstrumentedAttribute()
            self.title = "My Title"
            self.email = "me@example.com"

    obj = OtherModel()

    result = asanit.sanitize_for_audit(obj)

    # Basic metadata fields
    assert result["_model_type"] == "OtherModel"
    assert result["_table_name"] == "other_tbl"

    # Primary key should have been added
    assert result.get("_pk_id") == 42

    # 'title' and 'email' are normal values and should be present
    assert result.get("title") == "My Title"
    assert result.get("email") == "me@example.com"

    # 'name' was an InstrumentedAttribute and should NOT be present
    assert "name" not in result


def test_inspect_raises_and_identifying_fields(monkeypatch):
    """When inspect() raises, sanitizer should continue and still collect identifying fields.
    """
    # Setup inspect to raise
    def inspect_raise(cls):
        raise RuntimeError("inspect failed")

    InstrumentedAttribute = _setup_fake_sqlalchemy(monkeypatch, inspect_func=inspect_raise)

    class OtherModel2:
        __table__ = types.SimpleNamespace(name="tbl2")

        def __init__(self):
            self.id = 7
            self.name = "Name2"
            self.subject = "Subj"

    obj = OtherModel2()

    result = asanit.sanitize_for_audit(obj)

    assert result["_model_type"] == "OtherModel2"
    assert result["_table_name"] == "tbl2"
    # No _pk_* fields because inspect raised
    assert not any(k.startswith("_pk_") for k in result.keys())
    # Identifying fields should still be included
    assert result.get("id") == 7
    assert result.get("name") == "Name2"
    assert result.get("subject") == "Subj"


def test_appointment_model_exception_branch(monkeypatch):
    """Cause sanitize_for_audit called from _sanitize_appointment_model to raise for a particular
    field value so the except/continue branch is exercised.
    """
    InstrumentedAttribute = _setup_fake_sqlalchemy(monkeypatch)

    class Appointment:
        __table__ = types.SimpleNamespace(name="appts")

        def __init__(self):
            self.id = 1
            self.subject = "Sub"
            # We'll cause this value to trigger an exception inside the sanitizer wrapper
            self.start_time = "RAISE_ME"
            self.end_time = "2025-01-01T10:00:00"
            self.location = "Room"
            self.show_as = "Busy"
            self.sensitivity = "Normal"
            self.is_archived = False
            self.calendar_id = 99
            self.user_id = 5
            self.category_id = None
            self.ms_event_id = "evt-1"

    appt = Appointment()

    # Monkeypatch sanitize_for_audit so that when it's asked to sanitize the sentinel value
    # it raises. But calls for other objects should use the original implementation.
    original = asanit.sanitize_for_audit

    def fake_sanitize(obj, *args, **kwargs):
        if obj == "RAISE_ME":
            raise RuntimeError("boom in sanitizer")
        return original(obj, *args, **kwargs)

    monkeypatch.setattr(asanit, "sanitize_for_audit", fake_sanitize)

    try:
        result = original(appt)
    finally:
        # Restore original function to avoid affecting other tests
        monkeypatch.setattr(asanit, "sanitize_for_audit", original)

    # Appointment should be recognized and many key fields present
    assert result["_model_type"] == "Appointment"
    assert result["_table_name"] == "appts"
    assert result.get("id") == 1
    assert result.get("subject") == "Sub"
    # start_time should have been skipped due to the fake exception
    assert "start_time" not in result
    # end_time should be present
    assert result.get("end_time") == "2025-01-01T10:00:00"


def test_user_and_calendar_key_fields(monkeypatch):
    """Exercise all key fields for user and calendar sanitizers.
    """
    InstrumentedAttribute = _setup_fake_sqlalchemy(monkeypatch)

    class User:
        __table__ = types.SimpleNamespace(name="users")

        def __init__(self):
            self.id = 11
            self.email = "u@example.com"
            self.name = "User Name"
            self.is_active = True

    class Calendar:
        __table__ = types.SimpleNamespace(name="cals")

        def __init__(self):
            self.id = 22
            self.name = "Work"
            self.calendar_id = "cal-22"
            self.user_id = 11
            self.is_default = True

    user = User()
    cal = Calendar()

    ures = asanit.sanitize_for_audit(user)
    cres = asanit.sanitize_for_audit(cal)

    # Assert user fields
    assert ures["_model_type"] == "User"
    assert ures.get("id") == 11
    assert ures.get("email") == "u@example.com"
    assert ures.get("name") == "User Name"
    assert ures.get("is_active") is True

    # Assert calendar fields
    assert cres["_model_type"] == "Calendar"
    assert cres.get("id") == 22
    assert cres.get("name") == "Work"
    assert cres.get("calendar_id") == "cal-22"
    assert cres.get("user_id") == 11
    assert cres.get("is_default") is True


def test_primitives_none_and_dates():
    # None
    assert asanit.sanitize_for_audit(None) is None

    # Primitives
    assert asanit.sanitize_for_audit("s") == "s"
    assert asanit.sanitize_for_audit(10) == 10
    assert asanit.sanitize_for_audit(3.14) == 3.14
    assert asanit.sanitize_for_audit(True) is True

    # datetime and date
    dt = datetime.datetime(2025, 1, 2, 3, 4, 5)
    d = datetime.date(2025, 1, 2)
    assert asanit.sanitize_for_audit(dt) == dt.isoformat()
    assert asanit.sanitize_for_audit(d) == d.isoformat()

    # list and tuple
    assert asanit.sanitize_for_audit([1, 2, 3]) == [1, 2, 3]
    assert asanit.sanitize_for_audit((1, 2)) == [1, 2]

    # dict with non-string key should convert keys to strings
    got = asanit.sanitize_for_audit({1: 'a', 'b': 2})
    assert got.get('1') == 'a' and got.get('b') == 2

    # set becomes list (order not guaranteed)
    sres = asanit.sanitize_for_audit({7, 8})
    assert set(sres) == {7, 8}


def test_circular_reference():
    a = []
    a.append(a)
    res = asanit.sanitize_for_audit(a)
    # inner element should be circular reference marker
    assert res == ["<circular_reference:list>"]


def test_iterable_iteration_raises_and_fallback(monkeypatch):
    class BadIter:
        def __iter__(self):
            raise RuntimeError("nope")

        def __str__(self):
            return "BADITER"

    bi = BadIter()
    # Because __iter__ raises, sanitizer should fall back to str(obj)
    assert asanit.sanitize_for_audit(bi) == "BADITER"


def test_str_raises_results_in_unserializable():
    class BadStr:
        def __str__(self):
            raise RuntimeError("boom-str")

    bs = BadStr()
    assert asanit.sanitize_for_audit(bs) == "<unserializable:BadStr>"


def test_max_depth_exceeded():
    class X:
        pass

    # Force current_depth > max_depth to exercise that branch
    res = asanit.sanitize_for_audit(X(), max_depth=0, _current_depth=1)
    assert res.startswith("<max_depth_exceeded:")


def test_generator_iterable():
    gen = (x for x in [4, 5, 6])
    assert asanit.sanitize_for_audit(gen) == [4, 5, 6]


def test_sanitize_audit_data_non_dict():
    # When a non-dict is passed, it should delegate to sanitize_for_audit
    assert asanit.sanitize_audit_data(123) == 123


def test_identifying_field_getattr_raises(monkeypatch):
    # Ensure that if processing a field raises in the sanitizer, the loop continues
    InstrumentedAttribute = _setup_fake_sqlalchemy(monkeypatch)

    class Bad:
        __table__ = types.SimpleNamespace(name="badtbl")

        def __init__(self, sentinel):
            self.id = 9
            self.name = sentinel

    sentinel = object()
    b = Bad(sentinel)

    original = asanit.sanitize_for_audit

    def fake_sanitize(obj, *args, **kwargs):
        if obj is sentinel:
            raise RuntimeError("boom-during-sanitize")
        return original(obj, *args, **kwargs)

    monkeypatch.setattr(asanit, "sanitize_for_audit", fake_sanitize)
    try:
        res = original(b)
    finally:
        monkeypatch.setattr(asanit, "sanitize_for_audit", original)

    # id should be present, name should be skipped due to the fake exception
    assert res.get("id") == 9
    assert "name" not in res


def test_user_calendar_getattr_raises(monkeypatch):
    InstrumentedAttribute = _setup_fake_sqlalchemy(monkeypatch)

    class UserBad:
        __table__ = types.SimpleNamespace(name="ub")

        def __init__(self, sentinel):
            self.id = 3
            self.email = sentinel

    class CalBad:
        __table__ = types.SimpleNamespace(name="cb")

        def __init__(self, sentinel):
            self.id = 4
            self.name = sentinel

    sentinel_u = object()
    sentinel_c = object()
    ub = UserBad(sentinel_u)
    cb = CalBad(sentinel_c)

    original = asanit.sanitize_for_audit

    def fake_sanitize(obj, *args, **kwargs):
        if obj is sentinel_u or obj is sentinel_c:
            raise RuntimeError("boom-during-sanitize")
        return original(obj, *args, **kwargs)

    monkeypatch.setattr(asanit, "sanitize_for_audit", fake_sanitize)
    try:
        ures = original(ub)
        cres = original(cb)
    finally:
        monkeypatch.setattr(asanit, "sanitize_for_audit", original)

    assert ures.get("id") == 3
    assert "email" not in ures

    assert cres.get("id") == 4
    assert "name" not in cres
