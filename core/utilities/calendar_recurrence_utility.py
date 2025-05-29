from typing import List
from datetime import date, datetime, timedelta
import pytz
from dateutil.rrule import rrulestr
from core.models.appointment import Appointment

def expand_recurring_events_range(appointments: List[Appointment], start_date: date, end_date: date) -> List[Appointment]:
    """
    Expand recurring Appointment model instances to non-recurring for each day in the date range (inclusive).
    Returns a flat list of all appointments in the range.
    """
    expanded = []
    day_count = (end_date - start_date).days + 1
    for appt in appointments:
        if getattr(appt, 'recurrence', None):
            for n in range(day_count):
                day = start_date + timedelta(days=n)
                if occurs_on_date(appt, day):
                    expanded.append(create_non_recurring_instance(appt, day))
        else:
            if appt.start_time.date() >= start_date and appt.start_time.date() <= end_date:
                expanded.append(appt)
    return expanded

def occurs_on_date(appt: Appointment, target_date: date) -> bool:
    """
    Returns True if the recurring Appointment occurs on target_date.
    Assumes appt.recurrence is an RFC 5545 RRULE string.
    Ensures all datetimes are timezone-aware (UTC).
    """
    recurrence = getattr(appt, 'recurrence', None)
    if not recurrence:
        return False
    dtstart = appt.start_time
    if dtstart.tzinfo is None:
        dtstart = dtstart.replace(tzinfo=pytz.UTC)
    range_start = pytz.UTC.localize(datetime.combine(target_date, datetime.min.time()))
    range_end = pytz.UTC.localize(datetime.combine(target_date, datetime.max.time()))
    rule = rrulestr(recurrence, dtstart=dtstart)
    occurrences = list(rule.between(range_start, range_end, inc=True))
    return bool(occurrences)

def create_non_recurring_instance(appt: Appointment, target_date: date) -> Appointment:
    """
    Returns a new Appointment instance representing a non-recurring instance of appt on target_date.
    """
    duration = appt.end_time - appt.start_time
    new_start = datetime.combine(target_date, appt.start_time.time(), tzinfo=appt.start_time.tzinfo)
    new_end = new_start + duration
    # Create a shallow copy and update times/recurrence
    instance = Appointment(
        user_id=appt.user_id,
        subject=appt.subject,
        start_time=new_start,
        end_time=new_end,
        calendar_id=getattr(appt, 'calendar_id', 'test-calendar-id')
        # Add other fields as needed
    )
    # Remove recurrence for the instance
    setattr(instance, 'recurrence', None)
    return instance 