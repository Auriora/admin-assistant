import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm.attributes import InstrumentedAttribute

from core.exceptions import CalendarServiceException
from core.models.appointment import Appointment
from core.utilities.calendar_overlap_utility import detect_overlaps, merge_duplicates
from core.utilities.calendar_recurrence_utility import expand_recurring_events_range
from core.utilities.time_utility import to_utc

# OpenTelemetry imports
try:
    from opentelemetry import metrics, trace
    from opentelemetry.trace import Status, StatusCode

    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)

    # Create metrics
    appointment_preparation_counter = meter.create_counter(
        "appointment_preparation_total",
        description="Total number of appointment preparation operations",
        unit="1",
    )
    appointments_processed_counter = meter.create_counter(
        "appointments_processed_total",
        description="Total number of appointments processed for archiving",
        unit="1",
    )
    overlap_detection_counter = meter.create_counter(
        "overlap_detection_total",
        description="Total number of overlap detections",
        unit="1",
    )
    OTEL_AVAILABLE = True
except ImportError:
    tracer = None
    meter = None
    OTEL_AVAILABLE = False

logger = logging.getLogger(__name__)


def prepare_appointments_for_archive(
    appointments: List[Appointment],
    start_date: date,
    end_date: date,
    user=None,
    session=None,
    logger=None,
    action_log_repository: "Optional[Any]" = None,  # Kept for backward compatibility, but not used
    allow_overlaps: bool = False,
) -> Dict[str, Any]:
    """
    Process a list of Appointment model instances to prepare them for archiving.
    Handles time zones, recurring events, overlaps, and duplicates.

    Args:
        appointments: List of Appointment model instances to process
        start_date: Start date for the archiving period
        end_date: End date for the archiving period
        user: User model instance (optional)
        session: Database session (optional)
        logger: Logger instance (optional)
        action_log_repository: Kept for backward compatibility, but not used
        allow_overlaps: If True, archive appointments even when overlaps are detected

    Returns:
        Dict with keys:
        - 'appointments': processed list of appointments ready for archiving
        - 'status': 'ok', 'overlap', or 'ok_with_overlaps'
        - 'conflicts': list of conflicts if overlaps detected
        - 'errors': list of error messages

    Note: This function no longer logs overlaps or writes to the DB. It only returns the detected overlaps.
    When allow_overlaps=True, overlapping appointments are included in archiving but conflicts are still reported.
    """
    if OTEL_AVAILABLE and tracer:
        with tracer.start_as_current_span(
            "calendar_archive_service.prepare_appointments_for_archive",
            attributes={
                "input.appointment_count": len(appointments),
                "input.start_date": start_date.isoformat(),
                "input.end_date": end_date.isoformat(),
                "input.allow_overlaps": allow_overlaps,
                "user.id": str(getattr(user, "id", "")) if user else "",
            },
        ) as span:
            return _prepare_appointments_for_archive_impl(
                appointments, start_date, end_date, user, session, logger, span, allow_overlaps
            )
    else:
        return _prepare_appointments_for_archive_impl(
            appointments, start_date, end_date, user, session, logger, None, allow_overlaps
        )


def _prepare_appointments_for_archive_impl(
    appointments: List[Appointment],
    start_date: date,
    end_date: date,
    user=None,
    session=None,
    logger=None,
    span=None,
    allow_overlaps: bool = False,
) -> Dict[str, Any]:
    """Implementation of prepare_appointments_for_archive with OpenTelemetry support."""
    result = {"appointments": [], "status": "ok", "conflicts": [], "errors": []}
    try:
        appts = expand_recurring_events_range(appointments, start_date, end_date)
        appts = merge_duplicates(appts)
        overlap_groups = detect_overlaps(appts)
        overlapping_appts = set()

        # Handle overlap detection and status determination
        if overlap_groups:
            if allow_overlaps:
                result["status"] = "ok_with_overlaps"
                if logger:
                    logger.info(
                        f"Found {len(overlap_groups)} overlap groups but proceeding with archiving due to allow_overlaps=True"
                    )
            else:
                result["status"] = "overlap"
                if logger:
                    logger.warning(
                        f"Found {len(overlap_groups)} overlap groups, excluding overlapping appointments from archiving"
                    )

            # Always populate conflicts for transparency
            result["conflicts"] = [
                [
                    {
                        "subject": appt.subject,
                        "start": (
                            appt.start_time.isoformat()
                            if isinstance(appt.start_time, datetime)
                            else None
                        ),
                        "end": (
                            appt.end_time.isoformat()
                            if isinstance(appt.end_time, datetime)
                            else None
                        ),
                    }
                    for appt in group
                ]
                for group in overlap_groups
            ]

            # Only exclude overlapping appointments if allow_overlaps=False
            if not allow_overlaps:
                for group in overlap_groups:
                    for appt in group:
                        overlapping_appts.add(appt)
        # Process appointments for archiving
        skipped_overlaps = 0
        skipped_invalid = 0
        skipped_non_appointments = 0

        for appt in appts:
            if not isinstance(appt, Appointment):
                skipped_non_appointments += 1
                continue

            if appt in overlapping_appts:
                skipped_overlaps += 1
                continue  # Skip archiving overlapping events when allow_overlaps=False

            # Ensure times are UTC, but only if not a Column object
            start_time = getattr(appt, "start_time", None)
            end_time = getattr(appt, "end_time", None)
            if isinstance(start_time, datetime):
                setattr(appt, "start_time", to_utc(start_time))
            if isinstance(end_time, datetime):
                setattr(appt, "end_time", to_utc(end_time))

            # Only allow if both are real datetimes
            if not (
                isinstance(start_time, datetime) and isinstance(end_time, datetime)
            ):
                skipped_invalid += 1
                result["errors"].append(
                    f"Skipped appointment with missing start or end time: {getattr(appt, 'subject', 'Unknown')}"
                )
                continue

            # Always use setattr for is_archived
            setattr(appt, "is_archived", True)  # type: ignore
            result["appointments"].append(appt)

        # Log archiving decisions
        if logger:
            total_processed = len(result["appointments"])
            logger.info(
                f"Archive preparation complete: {total_processed} appointments ready for archiving, "
                f"{skipped_overlaps} skipped due to overlaps, {skipped_invalid} skipped due to invalid times, "
                f"{skipped_non_appointments} skipped as non-appointment objects"
            )

        # Record metrics and span attributes
        if OTEL_AVAILABLE:
            appointment_preparation_counter.add(
                1,
                {
                    "status": result["status"],
                    "user_id": str(getattr(user, "id", "")) if user else "",
                },
            )
            appointments_processed_counter.add(
                len(result["appointments"]),
                {"user_id": str(getattr(user, "id", "")) if user else ""},
            )
            if overlap_groups:
                overlap_detection_counter.add(
                    len(overlap_groups),
                    {"user_id": str(getattr(user, "id", "")) if user else ""},
                )

            if span:
                span.set_attributes(
                    {
                        "output.processed_count": len(result["appointments"]),
                        "output.overlap_count": len(overlap_groups),
                        "output.error_count": len(result["errors"]),
                        "output.status": result["status"],
                        "input.allow_overlaps": allow_overlaps,
                        "output.skipped_overlaps": skipped_overlaps,
                        "output.skipped_invalid": skipped_invalid,
                        "output.skipped_non_appointments": skipped_non_appointments,
                    }
                )
                span.set_status(Status(StatusCode.OK))

    except Exception as e:
        if logger:
            logger.exception(
                f"Archiving preparation failed for range {start_date} to {end_date}: {str(e)}"
            )

        # Record error metrics and span status
        if OTEL_AVAILABLE:
            appointment_preparation_counter.add(
                1,
                {
                    "status": "error",
                    "user_id": str(getattr(user, "id", "")) if user else "",
                },
            )

            if span:
                span.set_attributes(
                    {"error.type": type(e).__name__, "error.message": str(e)}
                )
                span.set_status(Status(StatusCode.ERROR, str(e)))

        if hasattr(e, "add_note"):
            e.add_note(
                f"Error in prepare_appointments_for_archive for range {start_date} to {end_date}"
            )
        raise CalendarServiceException(
            f"Archiving preparation failed for range {start_date} to {end_date}"
        ) from e
    return result


def make_appointments_immutable(appointments: List[Appointment], db_session):
    """
    Mark archived appointments as immutable (except for user).
    This function properly sets the is_archived flag to True, making the appointments
    immutable for all users except the owner.

    Args:
        appointments: List of Appointment instances to mark as archived
        db_session: Database session for committing changes
    """
    if OTEL_AVAILABLE and tracer:
        with tracer.start_as_current_span(
            "calendar_archive_service.make_appointments_immutable",
            attributes={"appointment_count": len(appointments)},
        ) as span:
            try:
                for appt in appointments:
                    # Set the is_archived flag to True to make the appointment immutable
                    setattr(appt, "is_archived", True)  # type: ignore

                # Commit the changes to the database
                db_session.commit()

                span.set_attributes(
                    {
                        "operation.status": "success",
                        "appointments_marked_immutable": len(appointments),
                    }
                )
                span.set_status(Status(StatusCode.OK))

                logger.info(
                    f"Marked {len(appointments)} appointments as immutable (archived)"
                )
            except Exception as e:
                span.set_attributes(
                    {
                        "operation.status": "error",
                        "error.type": type(e).__name__,
                        "error.message": str(e),
                    }
                )
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    else:
        for appt in appointments:
            # Set the is_archived flag to True to make the appointment immutable
            setattr(appt, "is_archived", True)  # type: ignore

        # Commit the changes to the database
        db_session.commit()

        logger.info(f"Marked {len(appointments)} appointments as immutable (archived)")
