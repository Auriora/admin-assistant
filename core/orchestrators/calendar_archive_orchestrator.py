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
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class CalendarArchiveOrchestrator:
    """
    Orchestrator for archiving user appointments from MS Graph to an archive calendar,
    and logging overlaps and resolution tasks in the local database.
    """
    def archive_user_appointments(
        self,
        user: Any,
        msgraph_client: Any,
        source_calendar_id: str,
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
            source_calendar_id: Source calendar ID (MS Graph).
            archive_calendar_id: Archive calendar ID (MS Graph).
            start_date: Start of the period.
            end_date: End of the period.
            db_session: SQLAlchemy session for local DB.
            logger: Optional logger.
        Returns:
            dict: Summary of the operation (archived_count, overlap_count, errors).
        """
        try:
            # 1. Fetch appointments from MS Graph (source calendar)
            source_repo = MSGraphAppointmentRepository(msgraph_client, user, source_calendar_id)
            appointments = source_repo.list_for_user(start_date, end_date)

            # 2. Process: expand recurrences, deduplicate, detect overlaps
            expanded = expand_recurring_events_range(appointments, start_date, end_date)
            deduped = merge_duplicates(expanded)
            overlap_groups = detect_overlaps(deduped)
            overlapping_appts = set(a for group in overlap_groups for a in group)
            non_overlapping = [a for a in deduped if a not in overlapping_appts]

            # 3. Write non-overlapping to archive calendar (MS Graph)
            archive_repo = MSGraphAppointmentRepository(msgraph_client, user, archive_calendar_id)
            archived_count = 0
            for appt in non_overlapping:
                archive_repo.add(appt)
                archived_count += 1

            # 4. Log overlaps and create resolution tasks in local DB
            action_log_repo = ActionLogRepository(db_session)
            assoc_helper = EntityAssociationHelper()
            overlap_count = 0
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
            db_session.commit()
            return {
                'archived_count': archived_count,
                'overlap_count': overlap_count,
                'errors': []
            }
        except Exception as e:
            if logger:
                logger.exception(f"Orchestration failed for user {getattr(user, 'email', None)} from {start_date} to {end_date}: {str(e)}")
            return {
                'archived_count': 0,
                'overlap_count': 0,
                'errors': [str(e)]
            } 