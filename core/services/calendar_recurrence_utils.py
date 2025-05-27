from typing import List, Dict
from datetime import date, datetime, timedelta
import pytz
from dateutil.rrule import rrulestr

def expand_recurring_events_range(appointments: List[dict], start_date: date, end_date: date) -> List[dict]:
    """
    Expand recurring events to non-recurring for each day in the date range (inclusive).
    Returns a flat list of all appointments in the range.
    """
    expanded = []
    day_count = (end_date - start_date).days + 1
    for appt in appointments:
        if appt.get('recurrence'):
            for n in range(day_count):
                day = start_date + timedelta(days=n)
                if occurs_on_date(appt, day):
                    expanded.append(create_non_recurring_instance(appt, day))
        else:
            if appt['start'].date() >= start_date and appt['start'].date() <= end_date:
                expanded.append(appt)
    return expanded

def occurs_on_date(appt: dict, target_date: date) -> bool:
    """
    Returns True if the recurring event occurs on target_date.
    Assumes appt['recurrence'] is an RFC 5545 RRULE string.
    Ensures all datetimes are timezone-aware (UTC).
    """
    if not appt.get('recurrence'):
        return False
    dtstart = appt['start']
    if dtstart.tzinfo is None:
        dtstart = dtstart.replace(tzinfo=pytz.UTC)
    range_start = pytz.UTC.localize(datetime.combine(target_date, datetime.min.time()))
    range_end = pytz.UTC.localize(datetime.combine(target_date, datetime.max.time()))
    rule = rrulestr(appt['recurrence'], dtstart=dtstart)
    occurrences = list(rule.between(range_start, range_end, inc=True))
    return bool(occurrences)

def create_non_recurring_instance(appt: dict, target_date: date) -> dict:
    """
    Returns a new dict representing a non-recurring instance of appt on target_date.
    """
    duration = appt['end'] - appt['start']
    new_start = datetime.combine(target_date, appt['start'].time())
    new_end = new_start + duration
    instance = appt.copy()
    instance['start'] = new_start
    instance['end'] = new_end
    instance.pop('recurrence', None)
    return instance 