import logging
import time
from datetime import date
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from core.models.action_log import ActionLog
from core.models.appointment import Appointment
from core.models.archive_configuration import ArchiveConfiguration
from core.models.entity_association import EntityAssociation
from core.repositories.action_log_repository import ActionLogRepository
from core.repositories.appointment_repository_msgraph import (
    MSGraphAppointmentRepository,
)
from core.repositories.entity_association_repository import EntityAssociationHelper
from core.services.audit_log_service import AuditLogService
from core.services.calendar_archive_service import make_appointments_immutable
from core.services.category_processing_service import CategoryProcessingService
from core.services.enhanced_overlap_resolution_service import (
    EnhancedOverlapResolutionService,
)
from core.services.meeting_modification_service import MeetingModificationService
from core.services.timesheet_archive_service import TimesheetArchiveService
from core.utilities.audit_logging_utility import AuditContext, AuditLogHelper
from core.utilities.calendar_overlap_utility import detect_overlaps, merge_duplicates
from core.utilities.calendar_recurrence_utility import expand_recurring_events_range

# OpenTelemetry imports
try:
    from opentelemetry import metrics, trace
    from opentelemetry.trace import Status, StatusCode

    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)

    # Create metrics
    archive_operations_counter = meter.create_counter(
        "archive_operations_total",
        description="Total number of archive operations",
        unit="1",
    )
    archive_duration_histogram = meter.create_histogram(
        "archive_operation_duration_seconds",
        description="Duration of archive operations",
        unit="s",
    )
    archived_appointments_counter = meter.create_counter(
        "archived_appointments_total",
        description="Total number of appointments archived",
        unit="1",
    )
    overlap_conflicts_counter = meter.create_counter(
        "overlap_conflicts_total",
        description="Total number of overlap conflicts detected",
        unit="1",
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

    def resolve_calendar_uri(self, uri: str, user) -> str:
        """
        Resolve a calendar URI to the actual calendar ID using the new URI resolution system.

        Args:
            uri: Calendar URI to resolve (new or legacy format)
            user: User object

        Returns:
            Resolved calendar ID
        """
        try:
            from core.utilities.calendar_resolver import resolve_calendar_uri
            from core.utilities.auth_utility import get_cached_access_token

            access_token = get_cached_access_token()
            resolved_id = resolve_calendar_uri(uri, user, access_token)

            print(f"[DEBUG] Resolved calendar URI '{uri}' to ID: {resolved_id}")
            return resolved_id

        except Exception as e:
            print(f"[WARNING] Failed to resolve calendar URI '{uri}': {e}")
            # Fall back to legacy resolution for backward compatibility
            return self._legacy_resolve_msgraph_calendar_id(uri, user)

    def _legacy_resolve_msgraph_calendar_id(self, uri: str, user) -> str:
        """
        Legacy calendar resolution method for backward compatibility.
        """
        # Extract calendar ID using legacy logic
        if not uri:
            return ""
        if not uri.startswith("msgraph://"):
            return uri  # fallback: treat as raw ID
        suffix = uri[len("msgraph://") :]
        if suffix == "calendar":
            return ""  # primary calendar
        calendar_id = suffix

        # If it looks like a real MS Graph ID (long GUID), return as-is
        if len(calendar_id) > 50 and "=" in calendar_id:
            return calendar_id

        # Otherwise, it's probably a friendly name - look it up
        try:
            # Use direct MS Graph API call to avoid event loop issues
            import requests
            from core.utilities.auth_utility import get_cached_access_token

            access_token = get_cached_access_token()
            if not access_token:
                print(f"[WARNING] No access token available for calendar resolution")
                return calendar_id

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            # Make direct API call to list calendars
            url = f"https://graph.microsoft.com/v1.0/users/{user.email}/calendars?$select=id,name,isDefaultCalendar"
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                print(f"[WARNING] Failed to fetch calendars: {response.status_code} {response.text}")
                return calendar_id

            calendars_data = response.json()
            calendars = calendars_data.get('value', [])

            # Look for calendar by friendly name
            for cal_data in calendars:
                name_str = str(cal_data.get('name', ''))
                # Convert name to URI-safe format for comparison
                import re
                uri_safe_name = name_str.lower().strip()
                uri_safe_name = re.sub(r"\s+", "-", uri_safe_name)
                uri_safe_name = re.sub(r"[^a-z0-9\-_]", "", uri_safe_name)

                if uri_safe_name == calendar_id:
                    resolved_id = cal_data.get('id', '')
                    print(f"[DEBUG] Legacy resolved '{calendar_id}' to calendar ID: {resolved_id}")
                    return resolved_id

            # If not found by friendly name, return the original ID (might be a real ID)
            print(f"[WARNING] Calendar with friendly name '{calendar_id}' not found, using as-is")
            return calendar_id

        except Exception as e:
            print(f"[WARNING] Failed to resolve calendar ID '{calendar_id}': {e}")
            return calendar_id

    def archive_user_appointments_with_config(
        self,
        user: Any,
        msgraph_client: Any,
        archive_config: ArchiveConfiguration,
        start_date: date,
        end_date: date,
        db_session: Session,
        logger: Optional[Any] = None,
        audit_service: Optional[Any] = None,
        replace_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Archive appointments using an ArchiveConfiguration object with support for timesheet-specific archiving.

        Args:
            user: User model instance.
            msgraph_client: Authenticated MS Graph client.
            archive_config: ArchiveConfiguration object containing source/destination URIs and archive settings.
            start_date: Start of the period.
            end_date: End of the period.
            db_session: SQLAlchemy session for local DB.
            logger: Optional logger.
            audit_service: Optional audit service.
            replace_mode: Whether to replace existing appointments in the archive.

        Returns:
            Dict with archive results including status, counts, and any errors.
        """
        # Extract URIs from configuration
        source_calendar_uri = archive_config.source_calendar_uri
        archive_calendar_id = archive_config.destination_calendar_uri

        # Log archive type and configuration
        archive_purpose = getattr(archive_config, 'archive_purpose', 'general')
        allow_overlaps = getattr(archive_config, 'allow_overlaps', True)

        if logger:
            logger.info(f"Starting archive with purpose='{archive_purpose}', allow_overlaps={allow_overlaps}")

        # Route to appropriate archive processing based on purpose
        if archive_purpose == 'timesheet':
            return self._archive_with_timesheet_service(
                user=user,
                msgraph_client=msgraph_client,
                archive_config=archive_config,
                start_date=start_date,
                end_date=end_date,
                db_session=db_session,
                logger=logger,
                audit_service=audit_service,
                replace_mode=replace_mode,
            )
        else:
            # Use general archive logic with simplified overlap handling if configured
            return self._archive_with_general_logic(
                user=user,
                msgraph_client=msgraph_client,
                archive_config=archive_config,
                start_date=start_date,
                end_date=end_date,
                db_session=db_session,
                logger=logger,
                audit_service=audit_service,
                replace_mode=replace_mode,
                allow_overlaps=allow_overlaps,
            )

    def archive_user_appointments(
        self,
        user: Any,
        msgraph_client: Any,
        source_calendar_uri: str,
        archive_calendar_id: str,
        start_date: date,
        end_date: date,
        db_session: Session,
        logger: Optional[Any] = None,
        audit_service: Optional[Any] = None,
        replace_mode: bool = False,
        archive_purpose: str = 'general',
    ) -> Dict[str, Any]:
        """
        Archive appointments from a user's MS Graph calendar to an archive calendar, logging overlaps locally.

        This method maintains backward compatibility. For new implementations, use archive_user_appointments_with_config.

        Args:
            user: User model instance.
            msgraph_client: Authenticated MS Graph client.
            source_calendar_uri: Source calendar URI (with backend context).
            archive_calendar_id: Archive calendar ID (MS Graph).
            start_date: Start of the period.
            end_date: End of the period.
            db_session: SQLAlchemy session for local DB.
            logger: Optional logger.
            audit_service: Optional audit service.
            replace_mode: Whether to replace existing appointments in the archive.
            archive_purpose: Archive purpose ('general' or 'timesheet').

        Returns:
            dict: Summary of the operation (archived_count, overlap_count, errors).
        """
        # Create a temporary ArchiveConfiguration for backward compatibility
        temp_config = ArchiveConfiguration(
            user_id=user.id,
            name="Temporary Config (Legacy)",
            source_calendar_uri=source_calendar_uri,
            destination_calendar_uri=archive_calendar_id,
            is_active=True,
            timezone="UTC",  # Default timezone for legacy calls
            allow_overlaps=False,  # Default to excluding overlaps for backward compatibility
            archive_purpose=archive_purpose  # Use the provided archive purpose
        )

        if logger:
            logger.info("Using legacy archive method - consider migrating to archive_user_appointments_with_config")

        # Route based on archive purpose
        if archive_purpose == 'timesheet':
            return self._archive_with_timesheet_service(
                user=user,
                msgraph_client=msgraph_client,
                archive_config=temp_config,
                start_date=start_date,
                end_date=end_date,
                db_session=db_session,
                logger=logger,
                audit_service=audit_service,
                replace_mode=replace_mode,
            )
        else:
            # Delegate to the general implementation
            return self._archive_with_general_logic(
                user=user,
                msgraph_client=msgraph_client,
                archive_config=temp_config,
                start_date=start_date,
                end_date=end_date,
                db_session=db_session,
                logger=logger,
                audit_service=audit_service,
                replace_mode=replace_mode,
                allow_overlaps=False,
            )

    def _archive_with_timesheet_service(
        self,
        user: Any,
        msgraph_client: Any,
        archive_config: ArchiveConfiguration,
        start_date: date,
        end_date: date,
        db_session: Session,
        logger: Optional[Any] = None,
        audit_service: Optional[Any] = None,
        replace_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Archive appointments using TimesheetArchiveService for business category filtering.

        Args:
            user: User model instance.
            msgraph_client: Authenticated MS Graph client.
            archive_config: ArchiveConfiguration object.
            start_date: Start of the period.
            end_date: End of the period.
            db_session: SQLAlchemy session for local DB.
            logger: Optional logger.
            audit_service: Optional audit service.
            replace_mode: Whether to replace existing appointments in the archive.

        Returns:
            Dict with archive results including timesheet-specific statistics.
        """
        import uuid
        correlation_id = str(uuid.uuid4())
        operation_start_time = time.time()

        if logger:
            logger.info(f"Starting timesheet archive for user {user.id} with correlation_id {correlation_id}")

        # Create audit context for timesheet archiving
        with AuditContext(
            audit_service=audit_service,
            user_id=user.id,
            action_type="archive",
            operation="timesheet_archive",
            resource_type="calendar",
            resource_id=archive_config.source_calendar_uri,
            correlation_id=correlation_id,
        ) as audit_ctx:

            audit_ctx.set_request_data({
                "archive_purpose": "timesheet",
                "source_calendar_uri": archive_config.source_calendar_uri,
                "destination_calendar_uri": archive_config.destination_calendar_uri,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "allow_overlaps": archive_config.allow_overlaps,
            })

            try:
                # Initialize timesheet service
                timesheet_service = TimesheetArchiveService()
                audit_ctx.add_detail("phase", "initialization")
                audit_ctx.add_detail("service_type", "TimesheetArchiveService")

                # Fetch appointments from source calendar
                audit_ctx.add_detail("phase", "fetching_appointments")
                source_calendar_id = self.resolve_calendar_uri(archive_config.source_calendar_uri, user)
                source_repo = MSGraphAppointmentRepository(msgraph_client, user, source_calendar_id)
                appointments = source_repo.list_for_user(start_date, end_date)

                if logger:
                    logger.info(f"Fetched {len(appointments)} appointments for timesheet filtering")

                audit_ctx.add_detail("initial_appointment_count", len(appointments))

                # Process appointments with timesheet service
                audit_ctx.add_detail("phase", "timesheet_filtering")
                timesheet_result = timesheet_service.filter_appointments_for_timesheet(
                    appointments, include_travel=True
                )

                filtered_appointments = timesheet_result["filtered_appointments"]
                excluded_appointments = timesheet_result["excluded_appointments"]
                overlap_resolutions = timesheet_result["overlap_resolutions"]
                timesheet_stats = timesheet_result["statistics"]

                if logger:
                    logger.info(f"Timesheet filtering: {len(filtered_appointments)} business appointments, "
                              f"{len(excluded_appointments)} excluded")

                audit_ctx.add_detail("timesheet_statistics", timesheet_stats)
                audit_ctx.add_detail("filtered_appointment_count", len(filtered_appointments))
                audit_ctx.add_detail("excluded_appointment_count", len(excluded_appointments))
                audit_ctx.add_detail("overlap_resolutions", overlap_resolutions)

                # Archive the filtered appointments
                audit_ctx.add_detail("phase", "archiving_filtered_appointments")
                archive_result = self._archive_appointments_to_destination(
                    appointments=filtered_appointments,
                    archive_config=archive_config,
                    user=user,
                    msgraph_client=msgraph_client,
                    db_session=db_session,
                    replace_mode=replace_mode,
                    audit_ctx=audit_ctx,
                    logger=logger,
                )

                # Combine results
                result = {
                    "status": "success",
                    "archive_type": "timesheet",
                    "correlation_id": correlation_id,
                    "total_appointments_fetched": len(appointments),
                    "business_appointments_archived": len(filtered_appointments),
                    "personal_appointments_excluded": len(excluded_appointments),
                    "timesheet_statistics": timesheet_stats,
                    "overlap_resolutions": overlap_resolutions,
                    "archive_errors": archive_result.get("errors", []),
                    "archived_count": archive_result.get("archived_count", 0),
                    "operation_duration": time.time() - operation_start_time,
                }

                audit_ctx.add_detail("final_result", result)

                if logger:
                    logger.info(f"Timesheet archive completed: {result['archived_count']} appointments archived")

                return result

            except Exception as e:
                error_msg = f"Timesheet archive failed: {str(e)}"
                if logger:
                    logger.exception(error_msg)

                audit_ctx.add_detail("error", error_msg)
                audit_ctx.add_detail("phase", "error")

                return {
                    "status": "error",
                    "archive_type": "timesheet",
                    "correlation_id": correlation_id,
                    "error": error_msg,
                    "operation_duration": time.time() - operation_start_time,
                }

    def _archive_with_general_logic(
        self,
        user: Any,
        msgraph_client: Any,
        archive_config: ArchiveConfiguration,
        start_date: date,
        end_date: date,
        db_session: Session,
        logger: Optional[Any] = None,
        audit_service: Optional[Any] = None,
        replace_mode: bool = False,
        allow_overlaps: bool = True,
    ) -> Dict[str, Any]:
        """
        Archive appointments using general logic with optional simplified overlap handling.

        Args:
            user: User model instance.
            msgraph_client: Authenticated MS Graph client.
            archive_config: ArchiveConfiguration object.
            start_date: Start of the period.
            end_date: End of the period.
            db_session: SQLAlchemy session for local DB.
            logger: Optional logger.
            audit_service: Optional audit service.
            replace_mode: Whether to replace existing appointments in the archive.
            allow_overlaps: Whether to allow overlapping appointments in archive.

        Returns:
            Dict with archive results.
        """
        import uuid
        correlation_id = str(uuid.uuid4())
        operation_start_time = time.time()

        archive_purpose = getattr(archive_config, 'archive_purpose', 'general')

        if logger:
            logger.info(f"Starting general archive (purpose='{archive_purpose}') for user {user.id} "
                       f"with allow_overlaps={allow_overlaps}, correlation_id {correlation_id}")

        # Create audit context for general archiving
        with AuditContext(
            audit_service=audit_service,
            user_id=user.id,
            action_type="archive",
            operation="general_archive",
            resource_type="calendar",
            resource_id=archive_config.source_calendar_uri,
            correlation_id=correlation_id,
        ) as audit_ctx:

            audit_ctx.set_request_data({
                "archive_purpose": archive_purpose,
                "source_calendar_uri": archive_config.source_calendar_uri,
                "destination_calendar_uri": archive_config.destination_calendar_uri,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "allow_overlaps": allow_overlaps,
                "simplified_overlap_handling": allow_overlaps,
            })

            try:
                audit_ctx.add_detail("phase", "initialization")
                audit_ctx.add_detail("service_type", "GeneralArchive")
                audit_ctx.add_detail("overlap_handling", "simplified" if allow_overlaps else "full")

                # Fetch appointments from source calendar
                audit_ctx.add_detail("phase", "fetching_appointments")
                source_calendar_id = self.resolve_calendar_uri(archive_config.source_calendar_uri, user)
                source_repo = MSGraphAppointmentRepository(msgraph_client, user, source_calendar_id)
                appointments = source_repo.list_for_user(start_date, end_date)

                if logger:
                    logger.info(f"Fetched {len(appointments)} appointments for general archiving")

                audit_ctx.add_detail("initial_appointment_count", len(appointments))

                # Process appointments based on overlap handling preference
                if allow_overlaps:
                    # Simplified processing: expand recurrences, apply basic deduplication, but allow overlaps
                    processed_appointments = self._process_appointments_simplified(
                        appointments, start_date, end_date, audit_ctx, logger
                    )
                else:
                    # Full processing: expand recurrences, detect overlaps, apply resolution
                    processed_appointments = self._process_appointments_full(
                        appointments, start_date, end_date, audit_ctx, logger, db_session
                    )

                # Archive the processed appointments
                audit_ctx.add_detail("phase", "archiving_processed_appointments")
                archive_result = self._archive_appointments_to_destination(
                    appointments=processed_appointments["appointments"],
                    archive_config=archive_config,
                    user=user,
                    msgraph_client=msgraph_client,
                    db_session=db_session,
                    replace_mode=replace_mode,
                    audit_ctx=audit_ctx,
                    logger=logger,
                )

                # Calculate overlap count for backward compatibility
                processing_stats = processed_appointments.get("stats", {})
                overlap_count = 0
                if "overlap_groups" in processing_stats:
                    overlap_count = processing_stats["overlap_groups"]
                elif "overlapping_appointments" in processing_stats:
                    overlap_count = processing_stats["overlapping_appointments"]

                # Combine results
                result = {
                    "status": "success",
                    "archive_type": "general",
                    "archive_purpose": archive_purpose,
                    "correlation_id": correlation_id,
                    "total_appointments_fetched": len(appointments),
                    "appointments_archived": len(processed_appointments["appointments"]),
                    "allow_overlaps": allow_overlaps,
                    "overlap_handling": "simplified" if allow_overlaps else "full",
                    "processing_stats": processing_stats,
                    "conflicts": processed_appointments.get("conflicts", []),
                    "archive_errors": archive_result.get("errors", []),
                    "archived_count": archive_result.get("archived_count", 0),
                    "operation_duration": time.time() - operation_start_time,
                    # Backward compatibility keys
                    "overlap_count": overlap_count,
                    "errors": archive_result.get("errors", []),
                }

                audit_ctx.add_detail("final_result", result)

                if logger:
                    logger.info(f"General archive completed: {result['archived_count']} appointments archived")

                return result

            except Exception as e:
                error_msg = f"General archive failed: {str(e)}"
                if logger:
                    logger.exception(error_msg)

                audit_ctx.add_detail("error", error_msg)
                audit_ctx.add_detail("phase", "error")

                return {
                    "status": "error",
                    "archive_type": "general",
                    "archive_purpose": archive_purpose,
                    "correlation_id": correlation_id,
                    "error": error_msg,
                    "operation_duration": time.time() - operation_start_time,
                }

    def _process_appointments_simplified(
        self,
        appointments: list,
        start_date: date,
        end_date: date,
        audit_ctx: Any,
        logger: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Process appointments with simplified logic: expand recurrences and deduplicate, but allow overlaps.

        Args:
            appointments: List of appointments to process.
            start_date: Start date for processing.
            end_date: End date for processing.
            audit_ctx: Audit context for logging.
            logger: Optional logger.

        Returns:
            Dict with processed appointments and statistics.
        """
        if logger:
            logger.info("Processing appointments with simplified overlap handling")

        audit_ctx.add_detail("processing_mode", "simplified")

        # Expand recurring events
        expanded = expand_recurring_events_range(appointments, start_date, end_date)
        audit_ctx.add_detail("expanded_appointment_count", len(expanded))

        if logger:
            logger.info(f"Expanded {len(appointments)} to {len(expanded)} appointments")

        # Apply basic deduplication
        deduplicated = merge_duplicates(expanded)
        audit_ctx.add_detail("deduplicated_appointment_count", len(deduplicated))

        if logger:
            logger.info(f"Deduplicated to {len(deduplicated)} appointments")

        # Detect overlaps for reporting but don't filter them out
        overlap_groups = detect_overlaps(deduplicated)
        overlapping_count = sum(len(group) for group in overlap_groups)

        audit_ctx.add_detail("overlap_groups_detected", len(overlap_groups))
        audit_ctx.add_detail("overlapping_appointments_count", overlapping_count)

        if logger and overlap_groups:
            logger.info(f"Detected {len(overlap_groups)} overlap groups with {overlapping_count} appointments, "
                       "but allowing overlaps in archive")

        return {
            "appointments": deduplicated,
            "stats": {
                "original_count": len(appointments),
                "expanded_count": len(expanded),
                "deduplicated_count": len(deduplicated),
                "overlap_groups": len(overlap_groups),
                "overlapping_appointments": overlapping_count,
                "processing_mode": "simplified",
            },
            "conflicts": [],  # No conflicts since we allow overlaps
        }

    def _process_appointments_full(
        self,
        appointments: list,
        start_date: date,
        end_date: date,
        audit_ctx: Any,
        logger: Optional[Any] = None,
        db_session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Process appointments with full logic: expand recurrences, detect overlaps, and apply resolution.

        Args:
            appointments: List of appointments to process.
            start_date: Start date for processing.
            end_date: End date for processing.
            audit_ctx: Audit context for logging.
            logger: Optional logger.
            db_session: Database session for overlap logging.

        Returns:
            Dict with processed appointments and statistics.
        """
        if logger:
            logger.info("Processing appointments with full overlap resolution")

        audit_ctx.add_detail("processing_mode", "full")

        # Expand recurring events
        expanded = expand_recurring_events_range(appointments, start_date, end_date)
        audit_ctx.add_detail("expanded_appointment_count", len(expanded))

        # Apply category processing and privacy automation
        category_service = CategoryProcessingService()
        processed_appointments = category_service.process_appointments(expanded)
        audit_ctx.add_detail("category_processed_count", len(processed_appointments))

        # Apply meeting modifications
        modification_service = MeetingModificationService()
        modified_appointments = modification_service.process_modifications(processed_appointments)
        audit_ctx.add_detail("modification_processed_count", len(modified_appointments))

        # Deduplicate
        deduplicated = merge_duplicates(modified_appointments)
        audit_ctx.add_detail("deduplicated_appointment_count", len(deduplicated))

        # Detect and resolve overlaps
        overlap_groups = detect_overlaps(deduplicated)

        if overlap_groups:
            overlap_service = EnhancedOverlapResolutionService()
            resolution_stats = {"resolved": 0, "filtered": 0, "conflicts": 0}
            remaining_conflicts = []
            appointments_to_archive = []

            for group in overlap_groups:
                resolution_result = overlap_service.apply_automatic_resolution_rules(group)
                resolution_stats["resolved"] += len(resolution_result["resolved"])
                resolution_stats["filtered"] += len(resolution_result["filtered"])
                resolution_stats["conflicts"] += len(resolution_result["conflicts"])

                appointments_to_archive.extend(resolution_result["resolved"])
                remaining_conflicts.extend(resolution_result["conflicts"])

            # Add non-overlapping appointments
            overlapping_appointment_ids = set()
            for group in overlap_groups:
                for appt in group:
                    overlapping_appointment_ids.add(id(appt))

            for appointment in deduplicated:
                if id(appointment) not in overlapping_appointment_ids:
                    appointments_to_archive.append(appointment)

            audit_ctx.add_detail("overlap_resolution_stats", resolution_stats)
            audit_ctx.add_detail("remaining_conflicts_count", len(remaining_conflicts))

        else:
            appointments_to_archive = deduplicated
            remaining_conflicts = []
            resolution_stats = {"resolved": 0, "filtered": 0, "conflicts": 0}

        return {
            "appointments": appointments_to_archive,
            "stats": {
                "original_count": len(appointments),
                "expanded_count": len(expanded),
                "category_processed_count": len(processed_appointments),
                "modification_processed_count": len(modified_appointments),
                "deduplicated_count": len(deduplicated),
                "overlap_groups": len(overlap_groups),
                "resolution_stats": resolution_stats,
                "final_count": len(appointments_to_archive),
                "processing_mode": "full",
            },
            "conflicts": remaining_conflicts,
        }

    def _archive_appointments_to_destination(
        self,
        appointments: list,
        archive_config: ArchiveConfiguration,
        user: Any,
        msgraph_client: Any,
        db_session: Session,
        replace_mode: bool = False,
        audit_ctx: Optional[Any] = None,
        logger: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Archive appointments to the destination calendar.

        Args:
            appointments: List of appointments to archive.
            archive_config: Archive configuration.
            user: User model instance.
            msgraph_client: MS Graph client.
            db_session: Database session.
            replace_mode: Whether to replace existing appointments.
            audit_ctx: Audit context for logging.
            logger: Optional logger.

        Returns:
            Dict with archive results including counts and errors.
        """
        if not appointments:
            return {"archived_count": 0, "errors": []}

        archive_calendar_id = archive_config.destination_calendar_uri

        # Resolve archive calendar URI to determine repository type and ID
        try:
            from core.utilities.uri_utility import parse_resource_uri
            parsed_archive_uri = parse_resource_uri(archive_calendar_id)
            archive_scheme = parsed_archive_uri.scheme
        except Exception:
            # Fall back to legacy detection
            if archive_calendar_id.startswith("local://"):
                archive_scheme = "local"
            else:
                archive_scheme = "msgraph"

        if archive_scheme == "local":
            from core.repositories.appointment_repository_sqlalchemy import (
                SQLAlchemyAppointmentRepository,
            )

            # Resolve local calendar URI to ID
            local_cal_id = self.resolve_calendar_uri(archive_calendar_id, user)
            archive_repo = SQLAlchemyAppointmentRepository(
                user, local_cal_id, session=db_session
            )
            if logger:
                logger.info(f"Using SQLAlchemy repository for local calendar: {local_cal_id}")
            if audit_ctx:
                audit_ctx.add_detail("archive_repository_type", "SQLAlchemy")
        else:
            # For msgraph:// URIs (including new format)
            # Resolve to actual MS Graph calendar ID
            msgraph_cal_id = self.resolve_calendar_uri(archive_calendar_id, user)
            archive_repo = MSGraphAppointmentRepository(
                msgraph_client, user, msgraph_cal_id
            )
            if logger:
                logger.info(f"Using MSGraph repository for calendar: {msgraph_cal_id}")
            if audit_ctx:
                audit_ctx.add_detail("archive_repository_type", "MSGraph")
                audit_ctx.add_detail("resolved_calendar_id", msgraph_cal_id)

        # Handle replace mode or duplicate checking
        duplicate_count = 0
        deleted_appointments = []
        archive_errors = []
        archived_count = 0

        if replace_mode:
            if logger:
                logger.info("Replace mode enabled - deleting existing appointments in date range")

            # Delete existing appointments in the date range
            if hasattr(archive_repo, 'delete_for_period'):
                try:
                    # Extract date range from appointments
                    appointment_dates = []
                    for appt in appointments:
                        start_time = getattr(appt, 'start_time', None)
                        if start_time:
                            appointment_dates.append(start_time.date())

                    if appointment_dates:
                        range_start = min(appointment_dates)
                        range_end = max(appointment_dates)
                        deleted_appointments = archive_repo.delete_for_period(range_start, range_end)
                        if logger:
                            logger.info(f"Deleted {len(deleted_appointments)} existing appointments")
                        if audit_ctx:
                            audit_ctx.add_detail("deleted_count", len(deleted_appointments))
                            audit_ctx.add_detail("replace_mode", True)
                except Exception as e:
                    error_msg = f"Failed to delete existing appointments: {str(e)}"
                    archive_errors.append(error_msg)
                    if logger:
                        logger.error(error_msg)

        # Archive appointments
        if hasattr(archive_repo, 'add_bulk'):
            try:
                bulk_errors = archive_repo.add_bulk(appointments)
                archive_errors.extend(bulk_errors)
                archived_count = len(appointments) - len(bulk_errors)
            except Exception as e:
                # Fallback to individual operations if bulk fails
                if logger:
                    logger.warning(f"Bulk operation failed, falling back to individual operations: {e}")
                for appt in appointments:
                    try:
                        archive_repo.add(appt)
                        archived_count += 1
                    except Exception as individual_e:
                        archive_errors.append(
                            f"Failed to archive appointment {getattr(appt, 'subject', 'Unknown')}: {str(individual_e)}"
                        )
        else:
            # Repository doesn't support bulk operations, use individual operations
            for appt in appointments:
                try:
                    archive_repo.add(appt)
                    archived_count += 1
                except Exception as e:
                    archive_errors.append(
                        f"Failed to archive appointment {getattr(appt, 'subject', 'Unknown')}: {str(e)}"
                    )

        # Mark archived appointments as immutable for local storage
        if appointments and archive_calendar_id.startswith("local://"):
            try:
                make_appointments_immutable(appointments, db_session)
                if logger:
                    logger.info(f"Marked {len(appointments)} appointments as immutable")
                if audit_ctx:
                    audit_ctx.add_detail("immutable_marked", True)
                    audit_ctx.add_detail("immutable_count", len(appointments))
            except Exception as e:
                error_msg = f"Failed to mark appointments as immutable: {str(e)}"
                archive_errors.append(error_msg)
                if logger:
                    logger.error(error_msg)

        if audit_ctx:
            audit_ctx.add_detail("archived_count", archived_count)
            audit_ctx.add_detail("archive_errors", archive_errors)

        return {
            "archived_count": archived_count,
            "errors": archive_errors,
            "deleted_count": len(deleted_appointments),
        }
        operation_start_time = time.time()

        # Initialize audit logging
        if audit_service is None:
            from core.repositories.audit_log_repository import AuditLogRepository

            audit_repo = AuditLogRepository(session=db_session)
            audit_service = AuditLogService(repository=audit_repo)
        correlation_id = audit_service.generate_correlation_id()

        # Start OpenTelemetry span
        if OTEL_AVAILABLE and tracer:
            with tracer.start_as_current_span(
                "calendar_archive_orchestrator.archive_user_appointments",
                attributes={
                    "user.id": str(user.id),
                    "user.email": getattr(user, "email", ""),
                    "source_calendar_uri": source_calendar_uri,
                    "archive_calendar_id": archive_calendar_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "correlation_id": correlation_id,
                },
            ) as span:
                return self._archive_user_appointments_impl(
                    user,
                    msgraph_client,
                    source_calendar_uri,
                    archive_calendar_id,
                    start_date,
                    end_date,
                    db_session,
                    logger,
                    audit_service,
                    correlation_id,
                    operation_start_time,
                    span,
                    replace_mode,
                )
        else:
            return self._archive_user_appointments_impl(
                user,
                msgraph_client,
                source_calendar_uri,
                archive_calendar_id,
                start_date,
                end_date,
                db_session,
                logger,
                audit_service,
                correlation_id,
                operation_start_time,
                None,
                replace_mode,
            )

    def _archive_user_appointments_impl(
        self,
        user,
        msgraph_client,
        source_calendar_uri,
        archive_calendar_id,
        start_date,
        end_date,
        db_session,
        logger,
        audit_service,
        correlation_id,
        operation_start_time,
        span,
        replace_mode,
    ) -> Dict[str, Any]:
        """Implementation of archive_user_appointments with OpenTelemetry support."""
        # Create a temporary ArchiveConfiguration for the legacy implementation
        temp_config = ArchiveConfiguration(
            user_id=user.id,
            name="Legacy Implementation Config",
            source_calendar_uri=source_calendar_uri,
            destination_calendar_uri=archive_calendar_id,
            is_active=True,
            timezone="UTC",
            allow_overlaps=True,  # Default to allowing overlaps for backward compatibility
            archive_purpose='general'
        )

        # Delegate to the new general logic implementation
        return self._archive_with_general_logic(
            user=user,
            msgraph_client=msgraph_client,
            archive_config=temp_config,
            start_date=start_date,
            end_date=end_date,
            db_session=db_session,
            logger=logger,
            audit_service=audit_service,
            replace_mode=replace_mode,
            allow_overlaps=True,
        )
