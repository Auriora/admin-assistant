from typing import List, Optional
from datetime import datetime, date
from flask import current_app
from app.services.msgraph import get_authenticated_session_for_user
from sqlalchemy.exc import NoResultFound
import pytz
from dateutil.rrule import rrulestr

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
    def fetch_appointments_from_ms365(user, for_date: date) -> List[dict]:
        """
        Fetch appointments for the given user and date from Microsoft 365 via Graph API.
        Returns a list of appointment dicts.
        """
        try:
            session = get_authenticated_session_for_user(user)
            # TODO: Implement actual Graph API call for events on for_date
            # Placeholder: return []
            current_app.logger.info(f"Fetched appointments for {user.email} on {for_date}")
            return []
        except Exception as e:
            current_app.logger.exception(f"Failed to fetch appointments: {str(e)}")
            return []

    @staticmethod
    def archive_appointments(user, appointments: List[dict], archive_date: Optional[date] = None) -> dict:
        """
        Archive the given appointments to the archive calendar.
        Handles time zones, recurring, overlaps, and duplicates.
        Returns a result dict with status and errors.
        """
        result = {"archived": 0, "errors": []}
        try:
            from app.models import db, Appointment
            archive_date = archive_date or datetime.utcnow().date()
            # 1. Expand recurring events
            appointments = CalendarService.expand_recurring_events(appointments, archive_date)
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
                    archived = Appointment(
                        user_id=user.id,
                        subject=appt['subject'],
                        start_time=appt['start'],
                        end_time=appt['end'],
                        is_archived=True,
                        # Map additional fields here if needed (e.g., location_id, category_id)
                    )  # type: ignore
                    db.session.add(archived)
                except Exception as e:
                    result["errors"].append(f"Failed to archive {appt['subject']}: {str(e)}")
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
    def expand_recurring_events(appointments: List[dict], archive_date: date) -> List[dict]:
        """
        Expand recurring events to non-recurring for the archive day.
        """
        expanded = []
        for appt in appointments:
            if appt.get('recurrence'):
                if CalendarService.occurs_on_date(appt, archive_date):
                    expanded.append(CalendarService.create_non_recurring_instance(appt, archive_date))
            else:
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
    today = datetime.utcnow().date()
    appointments = CalendarService.fetch_appointments_from_ms365(user, today)
    result = CalendarService.archive_appointments(user, appointments)
    if result["errors"]:
        current_app.logger.error(f"Scheduled archive job errors: {result['errors']}")
    else:
        current_app.logger.info(f"Scheduled archive job completed for {user.email}") 