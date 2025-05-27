from typing import List, Dict

def merge_duplicates(appointments: List[dict]) -> List[dict]:
    """
    Merge duplicate appointments (same subject, start, end, attendees).
    Attendees are compared by their email addresses.
    """
    def attendee_emails(attendees):
        emails = []
        for a in attendees:
            if isinstance(a, dict):
                if 'emailAddress' in a and 'address' in a['emailAddress']:
                    emails.append(a['emailAddress']['address'].lower())
                elif 'address' in a:
                    emails.append(a['address'].lower())
            elif isinstance(a, str):
                emails.append(a.lower())
        return tuple(sorted(set(emails)))

    seen = {}
    for appt in appointments:
        key = (
            appt.get('subject'),
            appt.get('start'),
            appt.get('end'),
            attendee_emails(appt.get('attendees', []))
        )
        if key in seen:
            seen[key]['description'] = seen[key].get('description', '') + "\n---\n" + appt.get('description', '')
            merged_emails = set(attendee_emails(seen[key].get('attendees', []))) | set(attendee_emails(appt.get('attendees', [])))
            seen[key]['attendees'] = [{'emailAddress': {'address': e}} for e in merged_emails]
        else:
            seen[key] = appt
    return list(seen.values())

def detect_overlaps(appointments: List[dict]) -> List[List[dict]]:
    """
    Returns a list of lists, where each sublist contains appointments that overlap.
    """
    sorted_appts = sorted(appointments, key=lambda a: a['start'])
    overlaps = []
    current_group = []
    for appt in sorted_appts:
        if not current_group:
            current_group.append(appt)
        else:
            last = current_group[-1]
            if appt['start'] < last['end']:
                current_group.append(appt)
            else:
                if len(current_group) > 1:
                    overlaps.append(current_group)
                current_group = [appt]
    if len(current_group) > 1:
        overlaps.append(current_group)
    return overlaps 