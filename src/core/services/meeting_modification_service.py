import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from core.models.appointment import Appointment

logger = logging.getLogger(__name__)


class MeetingModificationService:
    """Service for processing meeting modification appointments."""

    # Modification type patterns for subject detection
    MODIFICATION_PATTERNS = {
        "extension": re.compile(r"^Extended$", re.IGNORECASE),  # Subject must be exactly "Extended"
        "shortened": re.compile(r"\bshortened\b", re.IGNORECASE),
        "early_start": re.compile(r"\bearly\s+start\b", re.IGNORECASE),
        "late_start": re.compile(r"\blate\s+start\b", re.IGNORECASE),
    }

    def detect_modification_type(self, subject: str) -> Optional[str]:
        """
        Detect modification type from subject.

        Args:
            subject: The appointment subject to analyze

        Returns:
            'extension', 'shortened', 'early_start', 'late_start', or None if no match
        """
        if not subject:
            return None

        for mod_type, pattern in self.MODIFICATION_PATTERNS.items():
            if pattern.search(subject):
                return mod_type

        return None

    def process_modifications(
        self, appointments: List[Appointment]
    ) -> List[Appointment]:
        """
        Process all modifications and merge with original appointments.

        Args:
            appointments: List of all appointments including modifications

        Returns:
            List of processed appointments with modifications applied
        """
        if not appointments:
            return []

        # Separate modification appointments from regular appointments
        modifications = []
        regular_appointments = []

        for appt in appointments:
            mod_type = self.detect_modification_type(getattr(appt, "subject", ""))
            if mod_type:
                modifications.append((mod_type, appt))
            else:
                regular_appointments.append(appt)

        # Process each modification
        processed_appointments = regular_appointments.copy()
        modification_log = []

        for mod_type, modification in modifications:
            original = self.find_original_appointment(
                modification, regular_appointments
            )
            if original:
                try:
                    if mod_type == "extension":
                        modified_appt = self.merge_extension(original, modification)
                    elif mod_type == "shortened":
                        modified_appt = self.apply_shortening(original, modification)
                    elif mod_type in ["early_start", "late_start"]:
                        modified_appt = self.adjust_start_time(original, modification)
                    else:
                        logger.warning(f"Unknown modification type: {mod_type}")
                        continue

                    # Replace original with modified version
                    if original in processed_appointments:
                        idx = processed_appointments.index(original)
                        processed_appointments[idx] = modified_appt
                        modification_log.append(
                            f"Applied {mod_type} to appointment: {getattr(original, 'subject', 'Unknown')}"
                        )

                except Exception as e:
                    logger.error(f"Failed to apply {mod_type} modification: {e}")
                    modification_log.append(f"Failed to apply {mod_type}: {e}")
            else:
                logger.warning(
                    f"No original appointment found for {mod_type} modification: {getattr(modification, 'subject', 'Unknown')}"
                )
                modification_log.append(
                    f"Orphaned {mod_type} modification: {getattr(modification, 'subject', 'Unknown')}"
                )

        if modification_log:
            logger.info(
                f"Modification processing completed: {'; '.join(modification_log)}"
            )

        return processed_appointments

    def merge_extension(
        self, original: Appointment, extension: Appointment
    ) -> Appointment:
        """
        Merge extension appointment with original.

        Args:
            original: The original appointment
            extension: The extension appointment

        Returns:
            New appointment with extended end time
        """
        # Create a copy of the original appointment
        merged = self._copy_appointment(original)

        # Calculate extension duration
        extension_duration = getattr(extension, "end_time", None) - getattr(
            extension, "start_time", None
        )
        if extension_duration:
            # Extend the end time by the extension duration
            merged.end_time = getattr(original, "end_time", None) + extension_duration
            logger.debug(
                f"Extended appointment '{getattr(original, 'subject', 'Unknown')}' by {extension_duration}"
            )

        return merged

    def apply_shortening(
        self, original: Appointment, shortening: Appointment
    ) -> Appointment:
        """
        Apply shortening to original appointment.

        Args:
            original: The original appointment
            shortening: The shortening appointment

        Returns:
            New appointment with reduced end time
        """
        # Create a copy of the original appointment
        shortened = self._copy_appointment(original)

        # Calculate shortening duration
        shortening_duration = getattr(shortening, "end_time", None) - getattr(
            shortening, "start_time", None
        )
        if shortening_duration:
            # Reduce the end time by the shortening duration
            shortened.end_time = (
                getattr(original, "end_time", None) - shortening_duration
            )

            # Ensure end time doesn't go before start time
            if shortened.end_time <= getattr(original, "start_time", None):
                shortened.end_time = getattr(original, "start_time", None) + timedelta(
                    minutes=1
                )
                logger.warning(
                    f"Shortening would make appointment negative duration, set to 1 minute minimum"
                )

            logger.debug(
                f"Shortened appointment '{getattr(original, 'subject', 'Unknown')}' by {shortening_duration}"
            )

        return shortened

    def adjust_start_time(
        self, original: Appointment, timing_adjustment: Appointment
    ) -> Appointment:
        """
        Adjust start time for early/late start.

        Args:
            original: The original appointment
            timing_adjustment: The timing adjustment appointment

        Returns:
            New appointment with adjusted start time
        """
        # Create a copy of the original appointment
        adjusted = self._copy_appointment(original)

        mod_type = self.detect_modification_type(
            getattr(timing_adjustment, "subject", "")
        )

        if mod_type == "early_start":
            # For early start, the adjustment appointment starts before the original
            # Move the original start time to match the adjustment start time
            adjusted.start_time = getattr(timing_adjustment, "start_time", None)
            logger.debug(
                f"Moved start time earlier for '{getattr(original, 'subject', 'Unknown')}'"
            )

        elif mod_type == "late_start":
            # For late start, calculate the delay and adjust start time
            delay_duration = getattr(timing_adjustment, "end_time", None) - getattr(
                timing_adjustment, "start_time", None
            )
            if delay_duration:
                adjusted.start_time = (
                    getattr(original, "start_time", None) + delay_duration
                )

                # Ensure start time doesn't go past end time
                if adjusted.start_time >= getattr(original, "end_time", None):
                    adjusted.start_time = getattr(
                        original, "end_time", None
                    ) - timedelta(minutes=1)
                    logger.warning(
                        f"Late start would make appointment negative duration, adjusted to 1 minute minimum"
                    )

                logger.debug(
                    f"Delayed start time by {delay_duration} for '{getattr(original, 'subject', 'Unknown')}'"
                )

        return adjusted

    def find_original_appointment(
        self, modification: Appointment, appointments: List[Appointment]
    ) -> Optional[Appointment]:
        """
        Find the original appointment for a modification.

        Args:
            modification: The modification appointment
            appointments: List of potential original appointments

        Returns:
            The original appointment if found, None otherwise
        """
        if not appointments:
            return None

        mod_start = getattr(modification, "start_time", None)
        mod_end = getattr(modification, "end_time", None)
        mod_categories = getattr(modification, "categories", None)

        if not mod_start or not mod_end:
            return None

        # Look for appointments that could be the original
        candidates = []

        for appt in appointments:
            # Skip if this is also a modification
            if self.detect_modification_type(getattr(appt, "subject", "")):
                continue

            appt_start = getattr(appt, "start_time", None)
            appt_end = getattr(appt, "end_time", None)
            appt_categories = getattr(appt, "categories", None)

            if not appt_start or not appt_end:
                continue

            # Check if categories match (if both have categories)
            if mod_categories and appt_categories:
                if mod_categories != appt_categories:
                    continue

            # Check time proximity based on modification type
            mod_type = self.detect_modification_type(
                getattr(modification, "subject", "")
            )

            if mod_type == "extension":
                # Extension should start at or near the original end time
                time_diff = abs((mod_start - appt_end).total_seconds())
                if time_diff <= 300:  # Within 5 minutes
                    candidates.append((time_diff, appt))

            elif mod_type == "shortened":
                # Shortening should overlap with the original appointment
                if (mod_start >= appt_start and mod_start < appt_end) or (
                    mod_end > appt_start and mod_end <= appt_end
                ):
                    # Calculate overlap score (higher is better)
                    overlap_start = max(mod_start, appt_start)
                    overlap_end = min(mod_end, appt_end)
                    overlap_duration = (overlap_end - overlap_start).total_seconds()
                    candidates.append((-overlap_duration, appt))  # Negative for sorting

            elif mod_type == "early_start":
                # Early start should be before the original start time
                if mod_start <= appt_start and mod_end <= appt_end:
                    time_diff = abs((mod_end - appt_start).total_seconds())
                    if time_diff <= 300:  # Within 5 minutes
                        candidates.append((time_diff, appt))

            elif mod_type == "late_start":
                # Late start should begin at or near the original start time
                time_diff = abs((mod_start - appt_start).total_seconds())
                if time_diff <= 300:  # Within 5 minutes
                    candidates.append((time_diff, appt))

        # Return the best candidate (lowest score)
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

        return None

    def _copy_appointment(self, appointment: Appointment) -> Appointment:
        """
        Create a copy of an appointment for modification.

        Args:
            appointment: The appointment to copy

        Returns:
            A new Appointment instance with copied attributes
        """
        # Create a new appointment instance
        new_appt = Appointment()

        # Copy all relevant attributes
        for attr in [
            "user_id",
            "start_time",
            "end_time",
            "subject",
            "location_id",
            "category_id",
            "timesheet_id",
            "recurrence",
            "ms_event_data",
            "show_as",
            "sensitivity",
            "location",
            "categories",
            "importance",
        ]:
            if hasattr(appointment, attr):
                value = getattr(appointment, attr)
                setattr(new_appt, attr, value)

        # Don't copy the ID or ms_event_id as this is a new appointment
        new_appt.id = None
        new_appt.ms_event_id = None

        return new_appt
