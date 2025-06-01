from datetime import datetime
from typing import Any, Dict, List

from core.models.appointment import Appointment


def merge_duplicates(appointments: List[Appointment]) -> List[Appointment]:
    """
    Merge duplicate appointments (same subject, start_time, end_time).
    Only model fields are considered for deduplication.
    """
    seen = {}
    for appt in appointments:
        subject = getattr(appt, "subject", None)
        start_time = getattr(appt, "start_time", None)
        end_time = getattr(appt, "end_time", None)
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
    valid_appts = [
        a
        for a in appointments
        if isinstance(getattr(a, "start_time", None), datetime)
        and isinstance(getattr(a, "end_time", None), datetime)
    ]
    # Use the actual value, not the SQLAlchemy Column object
    sorted_appts = sorted(valid_appts, key=lambda a: a.__dict__.get("start_time", None))
    overlaps = []
    current_group = []
    for appt in sorted_appts:
        if not current_group:
            current_group.append(appt)
        else:
            last = current_group[-1]
            if appt.__dict__.get("start_time", None) < last.__dict__.get(
                "end_time", None
            ):
                current_group.append(appt)
            else:
                if len(current_group) > 1:
                    overlaps.append(current_group)
                current_group = [appt]
    if len(current_group) > 1:
        overlaps.append(current_group)
    return overlaps


def detect_overlaps_with_metadata(
    appointments: List[Appointment],
) -> List[Dict[str, Any]]:
    """
    Enhanced overlap detection that includes metadata for resolution.
    Returns list of overlap groups with resolution metadata.

    Returns:
        List of dicts with keys:
        - 'appointments': List of overlapping appointments
        - 'metadata': Dict with resolution-relevant info (show_as values, importance, etc.)
    """
    overlap_groups = detect_overlaps(appointments)

    result = []
    for group in overlap_groups:
        metadata = {
            "show_as_values": [getattr(appt, "show_as", None) for appt in group],
            "importance_values": [getattr(appt, "importance", None) for appt in group],
            "sensitivity_values": [
                getattr(appt, "sensitivity", None) for appt in group
            ],
            "subjects": [getattr(appt, "subject", None) for appt in group],
            "start_times": [getattr(appt, "start_time", None) for appt in group],
            "end_times": [getattr(appt, "end_time", None) for appt in group],
            "group_size": len(group),
        }

        result.append({"appointments": group, "metadata": metadata})

    return result
