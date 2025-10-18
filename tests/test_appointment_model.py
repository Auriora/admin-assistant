from core.models.appointment import Appointment
from types import SimpleNamespace
from datetime import datetime, timezone
import pytest


def make_appt(**kwargs):
    now = datetime.now(timezone.utc)
    appt = Appointment(
        user_id=kwargs.get('user_id', 1),
        subject=kwargs.get('subject', 'Test'),
        start_time=kwargs.get('start_time', now),
        end_time=kwargs.get('end_time', now),
        calendar_id=kwargs.get('calendar_id', 'cal-1')
    )
    # Set extra attributes if provided
    for k, v in kwargs.items():
        setattr(appt, k, v)
    return appt


def test_is_private_and_out_of_office_properties():
    a = make_appt(sensitivity='private', show_as='oof')
    assert a.is_private is True
    assert a.is_out_of_office is True

    b = make_appt(sensitivity='normal', show_as='busy')
    assert b.is_private is False
    assert b.is_out_of_office is False


def test_is_immutable_logic_for_archived_and_user():
    # Archived appointment should be immutable for other users
    appt = make_appt(is_archived=True, user_id=10)

    # No current user => immutable
    assert appt.is_immutable(None) is True

    # Current user is owner => not immutable
    current_user = SimpleNamespace(id=10)
    assert appt.is_immutable(current_user) is False

    # Different user => immutable
    other_user = SimpleNamespace(id=99)
    assert appt.is_immutable(other_user) is True

    # Not archived => not immutable
    appt2 = make_appt(is_archived=False, user_id=5)
    assert appt2.is_immutable(SimpleNamespace(id=123)) is False


def test_validate_modification_allowed_raises_for_immutable():
    appt = make_appt(is_archived=True, user_id=1)
    with pytest.raises(Exception):
        appt.validate_modification_allowed(None)

    # Owner should not raise
    appt.validate_modification_allowed(SimpleNamespace(id=1))

