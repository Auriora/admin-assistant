from datetime import datetime, timezone, timedelta

import pytest

from core.models.appointment import UTCDateTime, Appointment
from core.exceptions import ImmutableAppointmentException


def test_utcdatetime_bind_and_result_roundtrip():
    td = UTCDateTime()
    # timezone-aware datetime in a non-UTC zone
    aware = datetime(2025, 10, 18, 12, 30, tzinfo=timezone.utc)
    # process_bind_param should return a naive datetime in UTC
    bound = td.process_bind_param(aware, dialect=None)
    assert bound.tzinfo is None
    # process_result_value should return an aware datetime in UTC
    result = td.process_result_value(bound, dialect=None)
    assert result.tzinfo == timezone.utc
    assert result.year == aware.year and result.hour == aware.hour


def test_is_private_and_is_out_of_office_properties():
    appt = Appointment()
    appt.sensitivity = 'private'
    appt.show_as = 'oof'
    assert appt.is_private is True
    assert appt.is_out_of_office is True

    appt.sensitivity = 'normal'
    appt.show_as = 'busy'
    assert appt.is_private is False
    assert appt.is_out_of_office is False


def test_is_immutable_and_validate_modification_allowed():
    appt = Appointment()
    appt.is_archived = False
    appt.user_id = 42
    # not archived -> mutable
    assert appt.is_immutable() is False

    # archived and no current_user -> immutable
    appt.is_archived = True
    assert appt.is_immutable() is True

    # archived but current_user is the owner -> mutable for owner
    class User:
        def __init__(self, id):
            self.id = id

    owner = User(42)
    other = User(99)

    assert appt.is_immutable(current_user=owner) is False
    assert appt.is_immutable(current_user=other) is True

    # validate_modification_allowed raises for other owner
    with pytest.raises(ImmutableAppointmentException):
        appt.validate_modification_allowed(current_user=other)

    # validate_modification_allowed does not raise for owner
    appt.validate_modification_allowed(current_user=owner)

