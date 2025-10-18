from datetime import datetime, date
import pytz
from types import SimpleNamespace

from core.utilities import calendar_recurrence_utility as cru
from core.models.appointment import Appointment


def make_appt(recurrence, start_dt, end_dt, **kwargs):
    # Create a minimal Appointment-like object; Appointment constructor is available
    appt = Appointment(
        user_id=kwargs.get('user_id', 1),
        subject=kwargs.get('subject', 'Test'),
        start_time=start_dt,
        end_time=end_dt,
        calendar_id=kwargs.get('calendar_id', 'cal-1')
    )
    appt.recurrence = recurrence
    return appt


def test_occurs_on_date_daily_rrule():
    utc = pytz.UTC
    start = utc.localize(datetime(2025, 10, 1, 9, 0, 0))
    end = utc.localize(datetime(2025, 10, 1, 10, 0, 0))
    # Daily recurrence
    appt = make_appt('FREQ=DAILY;INTERVAL=1', start, end)

    assert cru.occurs_on_date(appt, date(2025, 10, 1)) is True
    assert cru.occurs_on_date(appt, date(2025, 10, 2)) is True
    assert cru.occurs_on_date(appt, date(2025, 9, 30)) is False


def test_create_non_recurring_instance_preserves_duration_and_removes_recurrence():
    utc = pytz.UTC
    start = utc.localize(datetime(2025, 10, 1, 9, 0, 0))
    end = utc.localize(datetime(2025, 10, 1, 10, 30, 0))
    appt = make_appt('FREQ=DAILY;INTERVAL=1', start, end)

    inst = cru.create_non_recurring_instance(appt, date(2025, 10, 3))
    assert inst.recurrence is None
    assert inst.start_time.date() == date(2025, 10, 3)
    # duration preserved
    assert (inst.end_time - inst.start_time).seconds == (end - start).seconds


def test_expand_recurring_events_range_includes_non_recurring_and_recurring():
    utc = pytz.UTC
    rstart = utc.localize(datetime(2025, 10, 1, 9, 0, 0))
    rend = utc.localize(datetime(2025, 10, 1, 10, 0, 0))
    recurring = make_appt('FREQ=DAILY;INTERVAL=1', rstart, rend)

    nr_start = utc.localize(datetime(2025, 10, 2, 14, 0, 0))
    nr_end = utc.localize(datetime(2025, 10, 2, 15, 0, 0))
    nonrec = make_appt(None, nr_start, nr_end)

    expanded = cru.expand_recurring_events_range([recurring, nonrec], date(2025, 10, 1), date(2025, 10, 3))
    # recurring should produce instances for 1st,2nd,3rd (3 entries) plus the non-recurring on 2nd => total 4
    assert len([a for a in expanded if getattr(a, 'recurrence', None) is None]) >= 4

