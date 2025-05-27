from typing import List, Optional
from datetime import datetime, date, timedelta, UTC
from flask import current_app
from app.services.msgraph import get_authenticated_session_for_user
from sqlalchemy.exc import NoResultFound
import pytz
from dateutil.rrule import rrulestr
from dateutil import parser

class CalendarService:
    """
    Service for handling calendar archiving, fetching, and related business logic.
    Implements:
      - Fetching appointments from Microsoft 365
      - Archiving to the archive calendar
      - Overlap/duplicate detection
      - Immutability enforcement
      - Error handling and logging
    """

    @staticmethod
    def fetch_appointments_from_ms365(user, start_date: date, end_date: date) -> List[dict]:
        """
        Fetch appointments for the given user and date range (inclusive) from Microsoft 365 via Graph API.
        Returns a list of appointment dicts (all event fields).
        """
        try:
            session = get_authenticated_session_for_user(user)
            # Determine which calendar to use
            calendar_id = None
            if hasattr(user, 'archive_preference') and user.archive_preference and user.archive_preference.ms_calendar_id:
                calendar_id = user.archive_preference.ms_calendar_id
            user_email = user.email
            # Build endpoint
            if calendar_id:
                endpoint = f"https://graph.microsoft.com/v1.0/users/{user_email}/calendars/{calendar_id}/calendarView"
            else:
                endpoint = f"https://graph.microsoft.com/v1.0/users/{user_email}/calendarView"
            # Format datetimes in ISO 8601 with Z (UTC)
            start_str = datetime.combine(start_date, datetime.min.time()).isoformat() + 'Z'
            end_str = datetime.combine(end_date, datetime.max.time()).isoformat() + 'Z'
            params = {
                'startDateTime': start_str,
                'endDateTime': end_str,
                '$top': 1000  # adjust as needed
            }
            response = session.get(endpoint, params=params)
            response.raise_for_status()
            events = response.json().get('value', [])
            current_app.logger.info(f"Fetched {len(events)} appointments for {user.email} from {start_date} to {end_date}")
            return events
        except Exception as e:
            current_app.logger.exception(f"Failed to fetch appointments: {str(e)}")
            return []

    @staticmethod
    def _event_to_appointment_fields(event: dict, user_id: int) -> dict:
        """
        Map a Microsoft Graph event dict to Appointment model fields.
        Only fields that exist in the Appointment model are included.
        """
        # Required fields
        start = event.get('start', {})
        end = event.get('end', {})
        # Microsoft Graph returns dateTime and timeZone
        start_time = parser.parse(start.get('dateTime')) if start.get('dateTime') else None
        end_time = parser.parse(end.get('dateTime')) if end.get('dateTime') else None
        return {
            'user_id': user_id,
            'subject': event.get('subject'),
            'start_time': start_time,
            'end_time': end_time,
            'is_private': event.get('sensitivity', '').lower() == 'private',
            'is_out_of_office': event.get('showAs', '').lower() == 'oof',
            'is_archived': True,
            # location_id, category_id, timesheet_id are not mapped here
        }

    @staticmethod
    def archive_appointments(user, appointments: List[dict], start_date: date, end_date: date) -> dict:
        """
        Archive the given appointments to the archive calendar for the given date range (inclusive).
        Handles time zones, recurring, overlaps, and duplicates.
        Returns a result dict with status and errors.
        """
        result = {"archived": 0, "errors": []}
        try:
            from app.models import db, Appointment
            # 1. Expand recurring events for all days in the range
            appointments = CalendarService.expand_recurring_events_range(appointments, start_date, end_date)
            # 2. Merge duplicates
            appointments = CalendarService.merge_duplicates(appointments)
            # 3. Check for overlaps
            overlap_groups = CalendarService.detect_overlaps(appointments)
            if overlap_groups:
                return {
                    "status": "overlap",
                    "conflicts": [
                        [
                            {
                                "subject": appt["subject"],
                                "start": appt["start"].isoformat(),
                                "end": appt["end"].isoformat(),
                                # Add any other fields needed for the UI
                            }
                            for appt in group
                        ]
                        for group in overlap_groups
                    ]
                }
            # 4. Convert all times to UTC
            for appt in appointments:
                appt['start'] = CalendarService.to_utc(appt['start'])
                appt['end'] = CalendarService.to_utc(appt['end'])
            # 5. Save to DB
            for appt in appointments:
                try:
                    # Map event dict to Appointment model fields
                    appt_fields = CalendarService._event_to_appointment_fields(appt, user.id)
                    archived = Appointment(**appt_fields)
                    db.session.add(archived)
                except Exception as e:
                    result["errors"].append(f"Failed to archive {appt.get('subject', 'Unknown')}: {str(e)}")
            try:
                db.session.commit()
                result["archived"] = len(appointments)
            except Exception as e:
                db.session.rollback()
                result["errors"].append(f"DB commit failed: {str(e)}")
        except Exception as e:
            current_app.logger.exception(f"Archiving failed: {str(e)}")
            result["errors"].append(str(e))
        return result

    @staticmethod
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
                    if CalendarService.occurs_on_date(appt, day):
                        expanded.append(CalendarService.create_non_recurring_instance(appt, day))
            else:
                # Only include if the appointment falls within the range
                if appt['start'].date() >= start_date and appt['start'].date() <= end_date:
                    expanded.append(appt)
        return expanded

    @staticmethod
    def occurs_on_date(appt: dict, target_date: date) -> bool:
        """
        Returns True if the recurring event occurs on target_date.
        Assumes appt['recurrence'] is an RFC 5545 RRULE string.
        """
        if not appt.get('recurrence'):
            return False
        rule = rrulestr(appt['recurrence'], dtstart=appt['start'])
        occurrences = list(rule.between(
            datetime.combine(target_date, datetime.min.time()),
            datetime.combine(target_date, datetime.max.time()),
            inc=True
        ))
        return bool(occurrences)

    @staticmethod
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

    @staticmethod
    def merge_duplicates(appointments: List[dict]) -> List[dict]:
        """
        Merge duplicate appointments (same subject, start, end, attendees).
        """
        seen = {}
        for appt in appointments:
            key = (
                appt['subject'],
                appt['start'],
                appt['end'],
                tuple(sorted(appt.get('attendees', [])))
            )
            if key in seen:
                seen[key]['description'] += "\n---\n" + appt.get('description', '')
                seen[key]['attendees'] = list(set(seen[key]['attendees']) | set(appt.get('attendees', [])))
            else:
                seen[key] = appt
        return list(seen.values())

    @staticmethod
    def to_utc(dt):
        """
        Convert a datetime to UTC.
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=pytz.UTC)
        return dt.astimezone(pytz.UTC)

    @staticmethod
    def resolve_overlaps(appointments: List[dict]) -> List[dict]:
        """
        Detect and resolve overlapping appointments.
        Uses OpenAI for recommendations (stub).
        """
        # TODO: Implement overlap detection and call OpenAI if needed
        return appointments

    @staticmethod
    def make_appointments_immutable(appointments):
        """
        Mark archived appointments as immutable (except for user).
        """
        from app.models import db
        for appt in appointments:
            appt.is_archived = True
            # TODO: Enforce immutability in update/delete logic
        db.session.commit()

    @staticmethod
    def handle_api_rate_limits(error: Exception):
        """
        Handle Microsoft Graph API rate limits, log, and notify user.
        """
        current_app.logger.warning(f"API rate limit hit: {str(error)}")
        # TODO: Notify user via notification service

    @staticmethod
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


def scheduled_archive_job():
    """
    Function to be called by the scheduler for end-of-day archiving.
    """
    # Import models here to avoid circular import
    from app.models import User
    user = User.query.first()
    if not user:
        current_app.logger.warning("No user found for scheduled archive job.")
        return
    today = datetime.now(UTC).date()
    appointments = CalendarService.fetch_appointments_from_ms365(user, today, today)
    result = CalendarService.archive_appointments(user, appointments, today, today)
    if result["errors"]:
        current_app.logger.error(f"Scheduled archive job errors: {result['errors']}")
    else:
        current_app.logger.info(f"Scheduled archive job completed for {user.email}") 