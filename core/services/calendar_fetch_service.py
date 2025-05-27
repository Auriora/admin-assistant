from typing import List
from datetime import date

def fetch_appointments_from_ms365(user, start_date: date, end_date: date, msgraph_session, logger=None) -> List[dict]:
    """
    Fetch appointments for the given user and date range (inclusive) from Microsoft 365 via Graph API.
    Returns a list of appointment dicts (all event fields).
    """
    try:
        calendar_id = getattr(getattr(user, 'archive_preference', None), 'ms_calendar_id', None)
        user_email = user.email
        if calendar_id:
            endpoint = f"https://graph.microsoft.com/v1.0/users/{user_email}/calendars/{calendar_id}/calendarView"
        else:
            endpoint = f"https://graph.microsoft.com/v1.0/users/{user_email}/calendarView"
        start_str = start_date.strftime('%Y-%m-%dT00:00:00Z')
        end_str = end_date.strftime('%Y-%m-%dT23:59:59Z')
        params = {
            'startDateTime': start_str,
            'endDateTime': end_str,
            '$top': 1000
        }
        response = msgraph_session.get(endpoint, params=params)
        response.raise_for_status()
        events = response.json().get('value', [])
        if logger:
            logger.info(f"Fetched {len(events)} appointments for {user.email} from {start_date} to {end_date}")
        return events
    except Exception as e:
        if logger:
            logger.exception(f"Failed to fetch appointments: {str(e)}")
        return [] 