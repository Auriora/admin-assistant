from datetime import date
from typing import Any, Optional, Dict
from core.models.appointment import Appointment
from core.models.action_log import ActionLog
from core.models.entity_association import EntityAssociation
from core.repositories.appointment_repository_msgraph import MSGraphAppointmentRepository
from core.repositories.action_log_repository import ActionLogRepository
from core.repositories.entity_association_repository import EntityAssociationHelper
from core.utilities.calendar_recurrence_utility import expand_recurring_events_range
from core.utilities.calendar_overlap_utility import merge_duplicates, detect_overlaps
from core.services.category_processing_service import CategoryProcessingService
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class CalendarArchiveOrchestrator:
    """
    Orchestrator for archiving user appointments from MS Graph to an archive calendar,
    and logging overlaps and resolution tasks in the local database.
    """
    def extract_msgraph_calendar_id(self, uri: str) -> str:
        """
        Extract the MS Graph calendar ID from a URI of the form 'msgraph://calendar' (primary) or 'msgraph://<id>'.
        Returns an empty string for the primary calendar, or the calendar ID for others.
        """
        if not uri or not uri.startswith("msgraph://"):
            return uri  # fallback: treat as raw ID
        suffix = uri[len("msgraph://"):]
        if suffix == "calendar":
            return ""  # primary calendar
        return suffix

    def archive_user_appointments(
        self,
        user: Any,
        msgraph_client: Any,
        source_calendar_uri: str,
        archive_calendar_id: str,
        start_date: date,
        end_date: date,
        db_session: Session,
        logger: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Archive appointments from a user's MS Graph calendar to an archive calendar, logging overlaps locally.
        Args:
            user: User model instance.
            msgraph_client: Authenticated MS Graph client.
            source_calendar_uri: Source calendar URI (with backend context).
            archive_calendar_id: Archive calendar ID (MS Graph).
            start_date: Start of the period.
            end_date: End of the period.
            db_session: SQLAlchemy session for local DB.
            logger: Optional logger.
        Returns:
            dict: Summary of the operation (archived_count, overlap_count, errors).
        """
        try:
            print("[DEBUG] Parsing calendar URIs...")
            source_calendar_id = self.extract_msgraph_calendar_id(source_calendar_uri)
            archive_calendar_id = self.extract_msgraph_calendar_id(archive_calendar_id)
            print(f"[DEBUG] Source calendar URI: {source_calendar_uri}, Archive calendar URI: {archive_calendar_id}")
            # 1. Fetch appointments from MS Graph (source calendar)
            print("[DEBUG] Fetching appointments from MS Graph...")
            source_repo = MSGraphAppointmentRepository(msgraph_client, user, source_calendar_id)
            appointments = source_repo.list_for_user(start_date, end_date)
            print(f"[DEBUG] Fetched {len(appointments)} appointments.")

            # 2. Process: expand recurrences, deduplicate, detect overlaps
            print("[DEBUG] Expanding recurring events...")
            expanded = expand_recurring_events_range(appointments, start_date, end_date)
            print(f"[DEBUG] Expanded to {len(expanded)} events.")

            # 2a. Process categories and apply privacy automation
            print("[DEBUG] Processing categories and applying privacy automation...")
            category_service = CategoryProcessingService()
            category_stats = category_service.get_category_statistics(expanded)
            print(f"[DEBUG] Category stats: {category_stats['valid_categories']} valid, {category_stats['invalid_categories']} invalid, {category_stats['personal_appointments']} personal")

            # Apply privacy flags to personal appointments
            for appt in expanded:
                if category_service.should_mark_private(appt):
                    # Set sensitivity to Private for personal appointments
                    if hasattr(appt, 'sensitivity'):
                        appt.sensitivity = 'Private'

            print("[DEBUG] Deduplicating events...")
            deduped = merge_duplicates(expanded)
            print(f"[DEBUG] Deduped to {len(deduped)} events.")
            print("[DEBUG] Detecting overlaps...")
            overlap_groups = detect_overlaps(deduped)
            overlapping_appts = set(a for group in overlap_groups for a in group)
            non_overlapping = [a for a in deduped if a not in overlapping_appts]
            print(f"[DEBUG] Found {len(overlap_groups)} overlap groups, {len(non_overlapping)} non-overlapping events.")

            # 3. Write non-overlapping to archive calendar (MS Graph)
            print("[DEBUG] Selecting archive repository based on URI...")
            if archive_calendar_id.startswith("local://"):
                from core.repositories.appointment_repository_sqlalchemy import SQLAlchemyAppointmentRepository
                # Extract local calendar ID or name from URI
                local_cal_id = archive_calendar_id[len("local://"):]
                archive_repo = SQLAlchemyAppointmentRepository(user, local_cal_id, session=db_session)
                print(f"[DEBUG] Using SQLAlchemyAppointmentRepository for local calendar: {local_cal_id}")
            elif archive_calendar_id == "" or archive_calendar_id.startswith("msgraph://"):
                # For msgraph://calendar (primary) or msgraph://<id>
                msgraph_cal_id = self.extract_msgraph_calendar_id(archive_calendar_id)
                archive_repo = MSGraphAppointmentRepository(msgraph_client, user, msgraph_cal_id)
                print(f"[DEBUG] Using MSGraphAppointmentRepository for MS Graph calendar: {msgraph_cal_id}")
            else:
                raise ValueError(f"Unsupported archive calendar URI scheme: {archive_calendar_id}")
            archived_count = 0
            for appt in non_overlapping:
                archive_repo.add(appt)
                archived_count += 1
            print(f"[DEBUG] Archived {archived_count} events.")

            # 4. Log overlaps and category issues in local DB
            print("[DEBUG] Logging overlaps and category issues...")
            action_log_repo = ActionLogRepository(db_session)
            assoc_helper = EntityAssociationHelper()
            overlap_count = 0

            # Log overlaps
            for group in overlap_groups:
                for appt in group:
                    log = ActionLog(
                        user_id=user.id,
                        event_type='overlap',
                        state='needs_user_action',
                        description=f"Overlapping event: {getattr(appt, 'subject', None)}",
                        details={
                            'ms_event_id': getattr(appt, 'ms_event_id', None),
                            'subject': getattr(appt, 'subject', None),
                            'start_time': str(getattr(appt, 'start_time', None)),
                            'end_time': str(getattr(appt, 'end_time', None)),
                        }
                    )
                    action_log_repo.add(log)
                    assoc = EntityAssociation(
                        source_type='action_log',
                        source_id=log.id,
                        target_type='appointment',
                        target_id=getattr(appt, 'id', None) or getattr(appt, 'ms_event_id', None),
                        association_type='overlap'
                    )
                    assoc_helper.add(db_session, assoc)
                    overlap_count += 1

            # Log category validation issues
            category_issue_count = 0
            if category_stats['issues']:
                for issue in category_stats['issues'][:10]:  # Limit to first 10 issues
                    log = ActionLog(
                        user_id=user.id,
                        event_type='category_validation',
                        state='needs_user_action',
                        description=f"Category validation issue: {issue}",
                        details={
                            'issue_type': 'category_format',
                            'issue_description': issue,
                            'date_range': f"{start_date} to {end_date}",
                            'total_issues': len(category_stats['issues'])
                        }
                    )
                    action_log_repo.add(log)
                    category_issue_count += 1

            print(f"[DEBUG] Logged {overlap_count} overlaps and {category_issue_count} category issues. Committing to DB...")
            db_session.commit()
            print("[DEBUG] DB commit complete.")
            return {
                'archived_count': archived_count,
                'overlap_count': overlap_count,
                'category_stats': category_stats,
                'category_issue_count': category_issue_count,
                'errors': []
            }
        except Exception as e:
            print(f"[DEBUG] Exception occurred: {e}")
            if logger:
                logger.exception(f"Orchestration failed for user {getattr(user, 'email', None)} from {start_date} to {end_date}: {str(e)}")
            return {
                'archived_count': 0,
                'overlap_count': 0,
                'errors': [str(e)]
            } 