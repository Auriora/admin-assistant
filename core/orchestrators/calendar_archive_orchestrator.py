from datetime import date
from typing import Any, Optional, Dict
import time
from core.models.appointment import Appointment
from core.models.action_log import ActionLog
from core.models.entity_association import EntityAssociation
from core.repositories.appointment_repository_msgraph import MSGraphAppointmentRepository
from core.repositories.action_log_repository import ActionLogRepository
from core.repositories.entity_association_repository import EntityAssociationHelper
from core.utilities.calendar_recurrence_utility import expand_recurring_events_range
from core.utilities.calendar_overlap_utility import merge_duplicates, detect_overlaps
from core.services.category_processing_service import CategoryProcessingService
from core.services.enhanced_overlap_resolution_service import EnhancedOverlapResolutionService
from core.services.meeting_modification_service import MeetingModificationService
from core.services.calendar_archive_service import make_appointments_immutable
from core.services.audit_log_service import AuditLogService
from core.utilities.audit_logging_utility import AuditContext, AuditLogHelper
from sqlalchemy.orm import Session
import logging

# OpenTelemetry imports
try:
    from opentelemetry import trace, metrics
    from opentelemetry.trace import Status, StatusCode
    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)

    # Create metrics
    archive_operations_counter = meter.create_counter(
        "archive_operations_total",
        description="Total number of archive operations",
        unit="1"
    )
    archive_duration_histogram = meter.create_histogram(
        "archive_operation_duration_seconds",
        description="Duration of archive operations",
        unit="s"
    )
    archived_appointments_counter = meter.create_counter(
        "archived_appointments_total",
        description="Total number of appointments archived",
        unit="1"
    )
    overlap_conflicts_counter = meter.create_counter(
        "overlap_conflicts_total",
        description="Total number of overlap conflicts detected",
        unit="1"
    )
    OTEL_AVAILABLE = True
except ImportError:
    tracer = None
    meter = None
    OTEL_AVAILABLE = False

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
        For plain IDs without scheme, returns the ID as-is.
        """
        if not uri:
            return ""
        if not uri.startswith("msgraph://"):
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
        operation_start_time = time.time()

        # Initialize audit logging
        audit_service = AuditLogService()
        correlation_id = audit_service.generate_correlation_id()

        # Start OpenTelemetry span
        if OTEL_AVAILABLE and tracer:
            with tracer.start_as_current_span(
                "calendar_archive_orchestrator.archive_user_appointments",
                attributes={
                    "user.id": str(user.id),
                    "user.email": getattr(user, 'email', ''),
                    "source_calendar_uri": source_calendar_uri,
                    "archive_calendar_id": archive_calendar_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "correlation_id": correlation_id
                }
            ) as span:
                return self._archive_user_appointments_impl(
                    user, msgraph_client, source_calendar_uri, archive_calendar_id,
                    start_date, end_date, db_session, logger, audit_service,
                    correlation_id, operation_start_time, span
                )
        else:
            return self._archive_user_appointments_impl(
                user, msgraph_client, source_calendar_uri, archive_calendar_id,
                start_date, end_date, db_session, logger, audit_service,
                correlation_id, operation_start_time, None
            )

    def _archive_user_appointments_impl(
        self, user, msgraph_client, source_calendar_uri, archive_calendar_id,
        start_date, end_date, db_session, logger, audit_service,
        correlation_id, operation_start_time, span
    ) -> Dict[str, Any]:
        """Implementation of archive_user_appointments with OpenTelemetry support."""

        # Create audit context for the entire archiving operation
        with AuditContext(
            audit_service=audit_service,
            user_id=user.id,
            action_type='archive',
            operation='calendar_archive',
            resource_type='calendar',
            resource_id=source_calendar_uri,
            correlation_id=correlation_id
        ) as audit_ctx:

            # Add operation parameters to audit log
            audit_ctx.set_request_data({
                'source_calendar_uri': source_calendar_uri,
                'archive_calendar_id': archive_calendar_id,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            })

            try:
                print("[DEBUG] Parsing calendar URIs...")
                source_calendar_id = self.extract_msgraph_calendar_id(source_calendar_uri)
                archive_calendar_id = self.extract_msgraph_calendar_id(archive_calendar_id)
                print(f"[DEBUG] Source calendar URI: {source_calendar_uri}, Archive calendar URI: {archive_calendar_id}")

                # Log the start of the operation
                audit_ctx.add_detail('phase', 'initialization')
                audit_ctx.add_detail('source_calendar_id', source_calendar_id)
                audit_ctx.add_detail('archive_calendar_id', archive_calendar_id)
                # 1. Fetch appointments from MS Graph (source calendar)
                print("[DEBUG] Fetching appointments from MS Graph...")
                audit_ctx.add_detail('phase', 'fetching_appointments')

                source_repo = MSGraphAppointmentRepository(msgraph_client, user, source_calendar_id)
                appointments = source_repo.list_for_user(start_date, end_date)
                print(f"[DEBUG] Fetched {len(appointments)} appointments.")

                audit_ctx.add_detail('initial_appointment_count', len(appointments))

                # 2. Process: expand recurrences, deduplicate, detect overlaps
                print("[DEBUG] Expanding recurring events...")
                audit_ctx.add_detail('phase', 'processing_appointments')

                expanded = expand_recurring_events_range(appointments, start_date, end_date)
                print(f"[DEBUG] Expanded to {len(expanded)} events.")

                audit_ctx.add_detail('expanded_appointment_count', len(expanded))

                # 2a. Process categories and apply privacy automation
                print("[DEBUG] Processing categories and applying privacy automation...")
                category_service = CategoryProcessingService()
                category_stats = category_service.get_category_statistics(expanded)
                print(f"[DEBUG] Category stats: {category_stats['valid_categories']} valid, {category_stats['invalid_categories']} invalid, {category_stats['personal_appointments']} personal")

                audit_ctx.add_detail('category_stats', category_stats)

                # Apply privacy flags to personal appointments
                privacy_applied_count = 0
                for appt in expanded:
                    if category_service.should_mark_private(appt):
                        # Set sensitivity to Private for personal appointments
                        if hasattr(appt, 'sensitivity'):
                            appt.sensitivity = 'Private'
                            privacy_applied_count += 1

                audit_ctx.add_detail('privacy_applied_count', privacy_applied_count)

                # 2b. Process meeting modifications
                print("[DEBUG] Processing meeting modifications...")
                modification_service = MeetingModificationService()
                processed_appointments = modification_service.process_modifications(expanded)
                modification_count = len(expanded) - len(processed_appointments)
                print(f"[DEBUG] Processed {modification_count} modification appointments, resulting in {len(processed_appointments)} appointments")

                audit_ctx.add_detail('modification_count', modification_count)
                audit_ctx.add_detail('processed_appointment_count', len(processed_appointments))

                print("[DEBUG] Deduplicating events...")
                deduped = merge_duplicates(processed_appointments)
                print(f"[DEBUG] Deduped to {len(deduped)} events.")

                audit_ctx.add_detail('deduped_appointment_count', len(deduped))

                print("[DEBUG] Detecting overlaps...")
                overlap_groups = detect_overlaps(deduped)
                print(f"[DEBUG] Found {len(overlap_groups)} initial overlap groups.")

                audit_ctx.add_detail('initial_overlap_groups', len(overlap_groups))

                # Apply enhanced overlap resolution
                print("[DEBUG] Applying enhanced overlap resolution...")
                audit_ctx.add_detail('phase', 'overlap_resolution')

                overlap_service = EnhancedOverlapResolutionService()
                auto_resolved_appointments = []
                remaining_conflicts = []
                resolution_stats = {
                    'total_overlaps': len(overlap_groups),
                    'auto_resolved': 0,
                    'remaining_conflicts': 0,
                    'filtered_appointments': 0
                }

                for group in overlap_groups:
                    resolution_result = overlap_service.apply_automatic_resolution_rules(group)

                    # Add resolved appointments to archive list
                    auto_resolved_appointments.extend(resolution_result['resolved'])

                    # Track remaining conflicts that need manual resolution
                    if resolution_result['conflicts']:
                        remaining_conflicts.append(resolution_result['conflicts'])

                    # Update stats
                    if resolution_result['resolved']:
                        resolution_stats['auto_resolved'] += 1
                    if resolution_result['conflicts']:
                        resolution_stats['remaining_conflicts'] += 1
                    resolution_stats['filtered_appointments'] += len(resolution_result['filtered'])

                    # Log resolution details
                    if resolution_result['resolution_log']:
                        print(f"[DEBUG] Overlap resolution: {'; '.join(resolution_result['resolution_log'])}")

                # Combine non-overlapping appointments with auto-resolved ones
                overlapping_appts = set(a for group in overlap_groups for a in group)
                non_overlapping = [a for a in deduped if a not in overlapping_appts]
                appointments_to_archive = non_overlapping + auto_resolved_appointments

                print(f"[DEBUG] Resolution complete: {len(non_overlapping)} non-overlapping + {len(auto_resolved_appointments)} auto-resolved = {len(appointments_to_archive)} total to archive.")
                print(f"[DEBUG] Remaining conflicts: {len(remaining_conflicts)} groups need manual resolution.")

                audit_ctx.add_detail('resolution_stats', resolution_stats)
                audit_ctx.add_detail('appointments_to_archive_count', len(appointments_to_archive))
                audit_ctx.add_detail('remaining_conflicts_count', len(remaining_conflicts))

                # 3. Write non-overlapping to archive calendar (MS Graph)
                print("[DEBUG] Selecting archive repository based on URI...")
                audit_ctx.add_detail('phase', 'archiving')

                if archive_calendar_id.startswith("local://"):
                    from core.repositories.appointment_repository_sqlalchemy import SQLAlchemyAppointmentRepository
                    # Extract local calendar ID or name from URI
                    local_cal_id = archive_calendar_id[len("local://"):]
                    archive_repo = SQLAlchemyAppointmentRepository(user, local_cal_id, session=db_session)
                    print(f"[DEBUG] Using SQLAlchemyAppointmentRepository for local calendar: {local_cal_id}")
                    audit_ctx.add_detail('archive_repository_type', 'SQLAlchemy')
                elif archive_calendar_id == "" or archive_calendar_id.startswith("msgraph://"):
                    # For msgraph://calendar (primary) or msgraph://<id>
                    msgraph_cal_id = self.extract_msgraph_calendar_id(archive_calendar_id)
                    archive_repo = MSGraphAppointmentRepository(msgraph_client, user, msgraph_cal_id)
                    print(f"[DEBUG] Using MSGraphAppointmentRepository for MS Graph calendar: {msgraph_cal_id}")
                    audit_ctx.add_detail('archive_repository_type', 'MSGraph')
                else:
                    # Default: treat as plain MS Graph calendar ID
                    archive_repo = MSGraphAppointmentRepository(msgraph_client, user, archive_calendar_id)
                    print(f"[DEBUG] Using MSGraphAppointmentRepository for plain calendar ID: {archive_calendar_id}")
                    audit_ctx.add_detail('archive_repository_type', 'MSGraph')

                archived_count = 0
                archive_errors = []

                for appt in appointments_to_archive:
                    try:
                        archive_repo.add(appt)
                        archived_count += 1
                    except Exception as e:
                        archive_errors.append(f"Failed to archive appointment {getattr(appt, 'subject', 'Unknown')}: {str(e)}")

                print(f"[DEBUG] Archived {archived_count} events.")
                audit_ctx.add_detail('archived_count', archived_count)
                audit_ctx.add_detail('archive_errors', archive_errors)

                # 3a. Mark archived appointments as immutable
                print("[DEBUG] Marking archived appointments as immutable...")
                if appointments_to_archive and archive_calendar_id.startswith("local://"):
                    # Only mark as immutable for local storage (SQLAlchemy)
                    # MS Graph appointments are inherently immutable once archived
                    make_appointments_immutable(appointments_to_archive, db_session)
                    print(f"[DEBUG] Marked {len(appointments_to_archive)} appointments as immutable.")
                    audit_ctx.add_detail('immutable_marked', True)
                    audit_ctx.add_detail('immutable_count', len(appointments_to_archive))
                else:
                    print("[DEBUG] Skipping immutability marking for MS Graph storage (inherently immutable).")
                    audit_ctx.add_detail('immutable_marked', False)
                    audit_ctx.add_detail('immutable_reason', 'MS Graph storage inherently immutable')

                # 4. Log overlaps and category issues in local DB
                print("[DEBUG] Logging overlaps and category issues...")
                audit_ctx.add_detail('phase', 'logging_issues')

                action_log_repo = ActionLogRepository(db_session)
                assoc_helper = EntityAssociationHelper()
                overlap_count = 0

                # Log only remaining conflicts that need manual resolution
                for conflict_group in remaining_conflicts:
                    for appt in conflict_group:
                        log = ActionLog(
                            user_id=user.id,
                            event_type='overlap',
                            state='needs_user_action',
                            description=f"Overlapping event (manual resolution needed): {getattr(appt, 'subject', None)}",
                            details={
                                'ms_event_id': getattr(appt, 'ms_event_id', None),
                                'subject': getattr(appt, 'subject', None),
                                'start_time': str(getattr(appt, 'start_time', None)),
                                'end_time': str(getattr(appt, 'end_time', None)),
                                'show_as': getattr(appt, 'show_as', None),
                                'importance': getattr(appt, 'importance', None),
                                'resolution_status': 'auto_resolution_failed',
                                'correlation_id': correlation_id  # Link to audit trail
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
                                'total_issues': len(category_stats['issues']),
                                'correlation_id': correlation_id  # Link to audit trail
                            }
                        )
                        action_log_repo.add(log)
                        category_issue_count += 1

                print(f"[DEBUG] Logged {overlap_count} overlaps and {category_issue_count} category issues. Committing to DB...")
                db_session.commit()
                print("[DEBUG] DB commit complete.")

                # Set final audit details and response data
                audit_ctx.add_detail('overlap_count', overlap_count)
                audit_ctx.add_detail('category_issue_count', category_issue_count)
                audit_ctx.add_detail('phase', 'completed')

                result = {
                    'archived_count': archived_count,
                    'overlap_count': overlap_count,
                    'category_stats': category_stats,
                    'category_issue_count': category_issue_count,
                    'resolution_stats': resolution_stats,
                    'modification_count': modification_count,
                    'errors': archive_errors,
                    'correlation_id': correlation_id  # Include correlation ID in response
                }

                # Record metrics and span attributes
                operation_duration = time.time() - operation_start_time
                if OTEL_AVAILABLE:
                    # Record metrics
                    archive_operations_counter.add(1, {
                        "status": "success" if not archive_errors else "partial",
                        "user_id": str(user.id)
                    })
                    archive_duration_histogram.record(operation_duration, {
                        "status": "success" if not archive_errors else "partial",
                        "user_id": str(user.id)
                    })
                    archived_appointments_counter.add(archived_count, {
                        "user_id": str(user.id)
                    })
                    overlap_conflicts_counter.add(overlap_count, {
                        "user_id": str(user.id)
                    })

                    # Update span attributes
                    if span:
                        span.set_attributes({
                            "operation.duration_seconds": operation_duration,
                            "operation.archived_count": archived_count,
                            "operation.overlap_count": overlap_count,
                            "operation.category_issue_count": category_issue_count,
                            "operation.modification_count": modification_count,
                            "operation.error_count": len(archive_errors),
                            "operation.status": "success" if not archive_errors else "partial"
                        })
                        span.set_status(Status(StatusCode.OK))

                audit_ctx.set_response_data(result)
                return result

            except Exception as e:
                print(f"[DEBUG] Exception occurred: {e}")
                if logger:
                    logger.exception(f"Orchestration failed for user {getattr(user, 'email', None)} from {start_date} to {end_date}: {str(e)}")

                # Record error metrics and span status
                operation_duration = time.time() - operation_start_time
                if OTEL_AVAILABLE:
                    # Record error metrics
                    archive_operations_counter.add(1, {
                        "status": "error",
                        "user_id": str(user.id)
                    })
                    archive_duration_histogram.record(operation_duration, {
                        "status": "error",
                        "user_id": str(user.id)
                    })

                    # Update span with error
                    if span:
                        span.set_attributes({
                            "operation.duration_seconds": operation_duration,
                            "operation.status": "error",
                            "error.type": type(e).__name__,
                            "error.message": str(e)
                        })
                        span.set_status(Status(StatusCode.ERROR, str(e)))

                # The AuditContext will automatically log the failure
                return {
                    'archived_count': 0,
                    'overlap_count': 0,
                    'errors': [str(e)],
                    'correlation_id': correlation_id
                }