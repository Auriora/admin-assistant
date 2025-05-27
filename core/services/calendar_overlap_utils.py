from typing import List
from core.models.appointment import Appointment
from datetime import datetime

def merge_duplicates(appointments: List[Appointment]) -> List[Appointment]:
    """
    Merge duplicate appointments (same subject, start_time, end_time).
    Only model fields are considered for deduplication.
    """
    seen = {}
    for appt in appointments:
        subject = getattr(appt, 'subject', None)
        start_time = getattr(appt, 'start_time', None)
        end_time = getattr(appt, 'end_time', None)
        key = (
            subject,
            start_time,
            end_time,
        )
        if key not in seen:
            seen[key] = appt
    return list(seen.values())

def detect_overlaps(appointments: List[Appointment]) -> List[List[Appointment]]:
    """
    Returns a list of lists, where each sublist contains appointments that overlap.
    Uses start_time and end_time attributes. Ignores appointments missing these fields.
    """
    # Filter out appointments missing start_time or end_time or where start_time is not a datetime
    valid_appts = [a for a in appointments if isinstance(getattr(a, 'start_time', None), datetime) and isinstance(getattr(a, 'end_time', None), datetime)]
    # Use the actual value, not the SQLAlchemy Column object
    sorted_appts = sorted(valid_appts, key=lambda a: a.__dict__.get('start_time', None))
    overlaps = []
    current_group = []
    for appt in sorted_appts:
        if not current_group:
            current_group.append(appt)
        else:
            last = current_group[-1]
            if appt.__dict__.get('start_time', None) < last.__dict__.get('end_time', None):
                current_group.append(appt)
            else:
                if len(current_group) > 1:
                    overlaps.append(current_group)
                current_group = [appt]
    if len(current_group) > 1:
        overlaps.append(current_group)
    return overlaps 