"""
Unit tests for calendar recurrence utility functions.

Covers:
- occurs_on_date: determine if an RFC5545 RRULE recurrence occurs on a target date
- create_non_recurring_instance: create an instance of Appointment for a specific date
- expand_recurring_events_range: expand recurring appointments within a date range

These tests use the Appointment model by constructing instances with the required fields.
"""

from datetime import datetime, date, timezone

from core.models.appointment import Appointment
from core.utilities.calendar_recurrence_utility import (
    occurs_on_date,
    create_non_recurring_instance,
    expand_recurring_events_range,
)


def make_appt(start_dt, end_dt, recurrence=None, **kwargs):
    # Helper to create Appointment instances with minimal required fields
    appt = Appointment(
        user_id=kwargs.get('user_id', 1),
        subject=kwargs.get('subject', 'Test'),
        start_time=start_dt,
        end_time=end_dt,
        calendar_id=kwargs.get('calendar_id', 'cal-1'),
    )
    appt.recurrence = recurrence
    return appt


class TestOccursOnDate:
    def test_non_recurring_returns_false(self):
        start = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        appt = make_appt(start, end, recurrence=None)
        assert occurs_on_date(appt, date(2025, 1, 1)) is False

    def test_daily_rrule_occurs(self):
        # Daily recurrence starting on 2025-01-01
        start = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        rrule = 'RRULE:FREQ=DAILY;COUNT=5'  # occurs on 1,2,3,4,5 Jan
        appt = make_appt(start, end, recurrence=rrule)

        assert occurs_on_date(appt, date(2025, 1, 1)) is True
        assert occurs_on_date(appt, date(2025, 1, 3)) is True
        assert occurs_on_date(appt, date(2025, 1, 6)) is False

    def test_weekly_rrule_occurs(self):
        # Weekly recurrence, every week on the same weekday
        start = datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc)  # Monday
        end = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        rrule = 'RRULE:FREQ=WEEKLY;COUNT=3'  # 3 occurrences: Jan 6, 13, 20
        appt = make_appt(start, end, recurrence=rrule)

        assert occurs_on_date(appt, date(2025, 1, 6)) is True
        assert occurs_on_date(appt, date(2025, 1, 13)) is True
        assert occurs_on_date(appt, date(2025, 1, 20)) is True
        assert occurs_on_date(appt, date(2025, 1, 27)) is False


class TestCreateNonRecurringInstance:
    def test_create_instance_preserves_duration_and_timezone(self):
        start = datetime(2025, 2, 1, 15, 30, tzinfo=timezone.utc)
        end = datetime(2025, 2, 1, 16, 45, tzinfo=timezone.utc)
        rrule = 'RRULE:FREQ=DAILY;COUNT=10'
        appt = make_appt(start, end, recurrence=rrule)

        target = date(2025, 2, 5)
        inst = create_non_recurring_instance(appt, target)

        assert inst.recurrence is None
        assert inst.start_time.date() == target
        assert inst.end_time - inst.start_time == end - start
        assert inst.start_time.tzinfo == start.tzinfo


class TestExpandRecurringEventsRange:
    def test_expand_recurring_events_range_includes_instances_and_nonrecurring(self):
        # One recurring event, daily for 3 occurrences
        start = datetime(2025, 3, 10, 8, 0, tzinfo=timezone.utc)
        end = datetime(2025, 3, 10, 9, 0, tzinfo=timezone.utc)
        rrule = 'RRULE:FREQ=DAILY;COUNT=3'  # 10,11,12 March
        recurring = make_appt(start, end, recurrence=rrule, subject='Daily')

        # One non-recurring event inside range
        nr_start = datetime(2025, 3, 11, 14, 0, tzinfo=timezone.utc)
        nr_end = datetime(2025, 3, 11, 15, 0, tzinfo=timezone.utc)
        nonrec = make_appt(nr_start, nr_end, recurrence=None, subject='One-off')

        # Range covers 10-12 March
        expanded = expand_recurring_events_range([recurring, nonrec], date(2025, 3, 10), date(2025, 3, 12))

        # Should include 3 instances from recurring and the one non-recurring => 4 total
        assert len(expanded) == 4

        # Dates included
        dates = sorted([a.start_time.date() for a in expanded])
        assert dates == [date(2025, 3, 10), date(2025, 3, 11), date(2025, 3, 11), date(2025, 3, 12)]

    def test_expand_range_excludes_out_of_range_nonrecurring(self):
        start = datetime(2025, 4, 1, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 4, 1, 10, 0, tzinfo=timezone.utc)
        appt_nonrec = make_appt(start, end, recurrence=None)

        expanded = expand_recurring_events_range([appt_nonrec], date(2025, 4, 2), date(2025, 4, 3))
        assert expanded == []


if __name__ == '__main__':
    pytest.main([__file__])
