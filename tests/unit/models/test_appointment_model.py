"""
Unit tests for the Appointment model properties and validation helpers.

Covers:
- is_private
- is_out_of_office
- is_immutable behavior with various users
- validate_modification_allowed raising ImmutableAppointmentException
"""
from datetime import datetime, timezone
import pytest

from core.models.appointment import Appointment
from core.exceptions import ImmutableAppointmentException


class DummyUser:
    def __init__(self, id):
        self.id = id


def make_appt(**kwargs):
    # Minimal Appointment instance with required fields set
    now = datetime.now(timezone.utc)
    appt = Appointment(
        user_id=kwargs.get('user_id', 1),
        start_time=kwargs.get('start_time', now),
        end_time=kwargs.get('end_time', now),
        subject=kwargs.get('subject', 'Test'),
        calendar_id=kwargs.get('calendar_id', 'cal-1'),
    )
    # set optional fields
    if 'sensitivity' in kwargs:
        appt.sensitivity = kwargs['sensitivity']
    if 'show_as' in kwargs:
        appt.show_as = kwargs['show_as']
    if 'is_archived' in kwargs:
        appt.is_archived = kwargs['is_archived']
    return appt


def test_is_private_true_and_false():
    a = make_appt(sensitivity='private')
    assert a.is_private is True

    b = make_appt(sensitivity='normal')
    assert b.is_private is False

    c = make_appt()
    # Default has no sensitivity -> False
    assert c.is_private is False


def test_is_out_of_office_true_and_false():
    a = make_appt(show_as='oof')
    assert a.is_out_of_office is True

    b = make_appt(show_as='busy')
    assert b.is_out_of_office is False

    c = make_appt()
    assert c.is_out_of_office is False


def test_is_immutable_logic():
    # Not archived => not immutable
    a = make_appt(is_archived=False, user_id=5)
    assert a.is_immutable() is False

    # Archived and no current user => immutable
    b = make_appt(is_archived=True, user_id=5)
    assert b.is_immutable() is True

    # Archived and current user is owner => not immutable
    c = make_appt(is_archived=True, user_id=5)
    owner = DummyUser(5)
    assert c.is_immutable(current_user=owner) is False

    # Archived and current user is not owner => immutable
    d = make_appt(is_archived=True, user_id=5)
    other = DummyUser(6)
    assert d.is_immutable(current_user=other) is True


def test_validate_modification_allowed_raises_for_immutable():
    appt = make_appt(is_archived=True, user_id=10)
    with pytest.raises(ImmutableAppointmentException):
        appt.validate_modification_allowed()

    # Owner should be allowed
    appt2 = make_appt(is_archived=True, user_id=10)
    owner = DummyUser(10)
    # Should not raise
    appt2.validate_modification_allowed(current_user=owner)

