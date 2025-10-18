"""
Unit tests for audit_sanitizer utilities.

Covers:
- sanitize_for_audit behavior for primitives, datetimes, lists, dicts, sets
- circular reference detection
- max depth handling
- model sanitization for a dummy Appointment-like object
- fallback for objects that raise on str()
"""
from datetime import datetime, date
import pytz

import pytest

from core.utilities.audit_sanitizer import sanitize_for_audit


def test_primitives_and_none():
    assert sanitize_for_audit(None) is None
    assert sanitize_for_audit('string') == 'string'
    assert sanitize_for_audit(123) == 123
    assert sanitize_for_audit(1.5) == 1.5
    assert sanitize_for_audit(True) is True


def test_datetime_and_date():
    dt = datetime(2025, 1, 2, 3, 4, 5, tzinfo=pytz.UTC)
    d = date(2025, 1, 2)
    assert sanitize_for_audit(dt) == dt.isoformat()
    assert sanitize_for_audit(d) == d.isoformat()


def test_list_tuple_and_set():
    data = ['a', 1, {'k': 'v'}]
    out = sanitize_for_audit(data)
    assert isinstance(out, list)
    assert out[0] == 'a' and out[1] == 1 and isinstance(out[2], dict)

    tpl = ('x', 'y')
    out2 = sanitize_for_audit(tpl)
    assert out2 == ['x', 'y']

    s = {'a', 'b'}
    out3 = sanitize_for_audit(s)
    assert set(out3) == s


def test_dict_with_non_str_keys():
    data = {1: 'one', ('a',): 'tuple'}
    out = sanitize_for_audit(data)
    assert '1' in out and "('a',)" in out


def test_circular_reference_detection():
    a = []
    a.append(a)
    out = sanitize_for_audit(a)
    # Should show circular reference marker in nested element
    assert out[0].startswith('<circular_reference:') or out[0].startswith('<max_depth_exceeded:')


def test_max_depth_exceeded():
    nested = [1]
    for _ in range(15):
        nested = [nested]
    out = sanitize_for_audit(nested, max_depth=5)
    # The sanitizer returns nested lists; the max-depth marker may appear nested inside.
    def contains_max_depth_marker(obj):
        if isinstance(obj, str):
            return obj.startswith('<max_depth_exceeded:')
        if isinstance(obj, list):
            return any(contains_max_depth_marker(i) for i in obj)
        if isinstance(obj, dict):
            return any(contains_max_depth_marker(v) for v in obj.values())
        return False
    assert contains_max_depth_marker(out)


def test_sanitize_dummy_appointment_model():
    # Create a dummy Appointment-like object (no SQLAlchemy required)
    class Appointment:
        def __init__(self):
            self.id = 42
            self.subject = 'Meeting'
            self.start_time = datetime(2025, 5, 1, 9, 0, tzinfo=pytz.UTC)
            self.end_time = datetime(2025, 5, 1, 10, 0, tzinfo=pytz.UTC)
            self.location = 'Office'
            self.show_as = 'busy'
            self.sensitivity = 'normal'
            self.is_archived = False
            self.calendar_id = 'cal-1'
            self.user_id = 7
            self.category_id = None
            self.ms_event_id = 'evt-1'
            # Mark as sqlalchemy-like
            self.__table__ = type('T', (), {'name': 'appointments'})

    appt = Appointment()
    out = sanitize_for_audit(appt)
    assert isinstance(out, dict)
    assert out.get('_model_type') == 'Appointment'
    assert out.get('id') == 42
    assert out.get('subject') == 'Meeting'
    assert out.get('start_time') == appt.start_time.isoformat()


def test_fallback_on_unserializable_object():
    class Bad:
        def __str__(self):
            raise RuntimeError('boom')

    b = Bad()
    out = sanitize_for_audit(b)
    # Should return a string fallback
    assert isinstance(out, str)
    assert out.startswith('<unserializable:') or 'boom' not in out


def test_sanitize_user_and_calendar_models():
    # User-like object
    class User:
        def __init__(self):
            self.id = 5
            self.email = 'u@example.com'
            self.name = 'User'
            self.is_active = True
            self.__table__ = type('T', (), {'name': 'users'})

    u = User()
    out = sanitize_for_audit(u)
    assert isinstance(out, dict)
    assert out.get('_model_type') == 'User'
    assert out.get('email') == 'u@example.com'

    # Calendar-like object
    class Calendar:
        def __init__(self):
            self.id = 7
            self.name = 'Work'
            self.calendar_id = 'cal-7'
            self.user_id = 5
            self.is_default = False
            self.__table__ = type('T', (), {'name': 'calendars'})

    c = Calendar()
    out2 = sanitize_for_audit(c)
    assert isinstance(out2, dict)
    assert out2.get('_model_type') == 'Calendar'
    assert out2.get('calendar_id') == 'cal-7'


def test_sanitize_model_with_inspect_primary_key(monkeypatch):
    # Create a model type that is not Appointment/User/Calendar but has pk
    class OtherModel:
        def __init__(self):
            self.id = 99
            self.name = 'Other'
            self.__table__ = type('T', (), {'name': 'others'})

    # Fake mapper with primary_key attribute
    class FakeCol:
        def __init__(self, name):
            self.name = name

    class FakeMapper:
        def __init__(self):
            self.primary_key = [FakeCol('id')]

    # Monkeypatch sqlalchemy.inspection.inspect to return our fake mapper
    import sqlalchemy.inspection as insp
    monkeypatch.setattr(insp, 'inspect', lambda cls: FakeMapper())

    om = OtherModel()
    out = sanitize_for_audit(om)
    # Should include _pk_id and name
    assert out.get('_pk_id') == 99
    assert out.get('name') == 'Other'


def test_iterable_fallback_on_error(monkeypatch):
    # Iterable that raises when iterated
    class BrokenIter:
        def __iter__(self):
            raise RuntimeError('iteration failed')

        def __str__(self):
            return 'BrokenIter'

    b = BrokenIter()
    out = sanitize_for_audit(b)
    assert out == 'BrokenIter'


def test_sanitize_audit_data_wrapper():
    # If non-dict is passed, sanitize_for_audit should be applied and returned
    lst = ['a', 1]
    out = sanitize_for_audit(lst)
    # wrapper should behave similarly
    from core.utilities.audit_sanitizer import sanitize_audit_data
    out2 = sanitize_audit_data(lst)
    assert out == out2


def test_instrumented_attribute_exclusion(monkeypatch):
    # Make a fake InstrumentedAttribute class and set it in sqlalchemy.orm.attributes
    class FakeInstrumented:
        pass

    import sqlalchemy.orm.attributes as attrs
    monkeypatch.setattr(attrs, 'InstrumentedAttribute', FakeInstrumented, raising=False)

    class Model:
        def __init__(self):
            self.id = 1
            self.name = 'M'
            self.some_attr = FakeInstrumented()
            self.__table__ = type('T', (), {'name': 'models'})

    m = Model()
    out = sanitize_for_audit(m)
    # some_attr should not be included because it's an InstrumentedAttribute
    assert 'some_attr' not in out
    assert out.get('name') == 'M'


def test_inspect_raises_is_handled(monkeypatch):
    # Force sqlalchemy.inspection.inspect to raise and ensure code handles it
    import sqlalchemy.inspection as insp
    monkeypatch.setattr(insp, 'inspect', lambda cls: (_ for _ in ()).throw(RuntimeError('inspect fail')))

    class Model2:
        def __init__(self):
            self.id = 2
            self.title = 'T'
            self.__table__ = type('T', (), {'name': 'others2'})

    m2 = Model2()
    out = sanitize_for_audit(m2)
    # Should still include _model_type and basic fields
    assert out.get('_model_type') == 'Model2'
    assert out.get('title') == 'T'


def test_generator_iterable_is_converted():
    gen = (i for i in [10, 20, 30])
    out = sanitize_for_audit(gen)
    assert out == [10, 20, 30]


def test_sanitize_audit_data_with_dict():
    from core.utilities.audit_sanitizer import sanitize_audit_data
    data = {'a': 1, 'b': [2, 3]}
    out = sanitize_audit_data(data)
    assert isinstance(out, dict)
    assert out['a'] == 1


if __name__ == '__main__':
    pytest.main([__file__])
