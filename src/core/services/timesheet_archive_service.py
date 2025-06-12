"""
Timesheet Archive Service

This service provides category-filtered archiving specifically for timesheet and billing purposes.
It filters appointments to include only business categories (billable, non-billable, travel),
applies automatic overlap resolution, and excludes personal appointments and 'Free' status appointments.

Key Features:
- Filter appointments for business categories only
- Automatic overlap resolution using existing rules (Free → Tentative → Priority)
- Travel appointment detection by subject keywords
- Integration with CategoryProcessingService
- Clean, billing-ready data output with comprehensive statistics
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from core.models.appointment import Appointment
from core.services.category_processing_service import CategoryProcessingService
from core.services.enhanced_overlap_resolution_service import EnhancedOverlapResolutionService
from core.utilities.calendar_overlap_utility import detect_overlaps

logger = logging.getLogger(__name__)


class TimesheetArchiveService:
    """Service for category-filtered archiving for timesheet and billing purposes."""

    # Business categories for timesheet purposes
    TIMESHEET_CATEGORIES = {
        "billable",
        "non-billable", 
        "travel"
    }

    # Travel keywords for subject detection
    TRAVEL_KEYWORDS = {
        "travel", "drive", "driving", "flight", "flying", "commute", "commuting",
        "transit", "transport", "journey", "trip", "departure", "arrival",
        "airport", "station", "highway", "route"
    }

    def __init__(self):
        """Initialize the timesheet archive service."""
        self.logger = logger
        self.category_service = CategoryProcessingService()
        self.overlap_service = EnhancedOverlapResolutionService()
        self._closed = False

    def filter_appointments_for_timesheet(
        self, 
        appointments: List[Appointment],
        include_travel: bool = True
    ) -> Dict[str, Any]:
        """
        Filter appointments for timesheet archiving with automatic overlap resolution.

        Args:
            appointments: List of appointment model instances to filter
            include_travel: Whether to include travel appointments (default: True)

        Returns:
            Dictionary with keys:
            - 'filtered_appointments': List of business appointments ready for timesheet
            - 'excluded_appointments': List of appointments that were excluded
            - 'overlap_resolutions': List of overlap resolution results
            - 'statistics': Dictionary with filtering and resolution statistics
            - 'issues': List of any issues encountered during processing
        """
        if not appointments:
            return {
                "filtered_appointments": [],
                "excluded_appointments": [],
                "overlap_resolutions": [],
                "statistics": self._get_empty_statistics(),
                "issues": []
            }

        result = {
            "filtered_appointments": [],
            "excluded_appointments": [],
            "overlap_resolutions": [],
            "statistics": {},
            "issues": []
        }

        try:
            # Step 1: Filter for business appointments
            business_appointments, excluded_appointments = self._filter_business_appointments(
                appointments, include_travel
            )
            result["excluded_appointments"] = excluded_appointments

            # Step 2: Detect and resolve overlaps automatically
            if business_appointments:
                resolved_appointments, overlap_resolutions = self._resolve_overlaps_automatically(
                    business_appointments
                )
                result["filtered_appointments"] = resolved_appointments
                result["overlap_resolutions"] = overlap_resolutions
            else:
                result["filtered_appointments"] = []
                result["overlap_resolutions"] = []

            # Step 3: Generate statistics
            result["statistics"] = self._generate_statistics(
                appointments, 
                business_appointments, 
                excluded_appointments,
                result["overlap_resolutions"]
            )

        except Exception as e:
            self.logger.exception(f"Error filtering appointments for timesheet: {e}")
            result["issues"].append(f"Processing error: {str(e)}")

        return result

    def _filter_business_appointments(
        self, 
        appointments: List[Appointment], 
        include_travel: bool = True
    ) -> Tuple[List[Appointment], List[Appointment]]:
        """
        Filter appointments to include only business categories.

        Args:
            appointments: List of appointments to filter
            include_travel: Whether to include travel appointments

        Returns:
            Tuple of (business_appointments, excluded_appointments)
        """
        business_appointments = []
        excluded_appointments = []

        for appointment in appointments:
            # Skip 'Free' status appointments
            if self._is_free_status_appointment(appointment):
                excluded_appointments.append(appointment)
                continue

            # Check for travel appointments by subject
            if include_travel and self._detect_travel_appointment(appointment):
                business_appointments.append(appointment)
                continue

            # Check categories using CategoryProcessingService
            customer_info = self.category_service.extract_customer_billing_info(appointment)

            # Exclude personal appointments (no valid categories)
            if customer_info["is_personal"]:
                excluded_appointments.append(appointment)
                continue

            # Include appointments with valid business billing types
            if customer_info["billing_type"] in self.TIMESHEET_CATEGORIES:
                business_appointments.append(appointment)
            else:
                excluded_appointments.append(appointment)

        return business_appointments, excluded_appointments

    def _resolve_overlaps_automatically(
        self, 
        appointments: List[Appointment]
    ) -> Tuple[List[Appointment], List[Dict[str, Any]]]:
        """
        Resolve overlaps automatically using EnhancedOverlapResolutionService.

        Args:
            appointments: List of appointments to check for overlaps

        Returns:
            Tuple of (resolved_appointments, overlap_resolution_results)
        """
        if not appointments:
            return [], []

        # Detect overlaps
        overlap_groups = detect_overlaps(appointments)

        if not overlap_groups:
            # No overlaps found
            return appointments, []

        resolved_appointments = []
        overlap_resolutions = []

        # Process each overlap group
        for group in overlap_groups:
            resolution_result = self.overlap_service.apply_automatic_resolution_rules(group)
            overlap_resolutions.append(resolution_result)

            # Add resolved appointments
            resolved_appointments.extend(resolution_result["resolved"])

        # Add non-overlapping appointments
        overlapping_appointment_ids = set()
        for group in overlap_groups:
            for appt in group:
                overlapping_appointment_ids.add(id(appt))

        for appointment in appointments:
            if id(appointment) not in overlapping_appointment_ids:
                resolved_appointments.append(appointment)

        return resolved_appointments, overlap_resolutions

    def _detect_travel_appointment(self, appointment: Appointment) -> bool:
        """
        Detect if an appointment is travel-related by subject keywords.

        Args:
            appointment: Appointment to check

        Returns:
            True if appointment appears to be travel-related
        """
        subject = getattr(appointment, "subject", "") or ""
        subject_lower = subject.lower()

        # Check for travel keywords in subject
        for keyword in self.TRAVEL_KEYWORDS:
            if keyword in subject_lower:
                return True

        return False

    def _is_free_status_appointment(self, appointment: Appointment) -> bool:
        """
        Check if appointment has 'Free' status.

        Args:
            appointment: Appointment to check

        Returns:
            True if appointment has 'Free' status
        """
        show_as = getattr(appointment, "show_as", None)
        return show_as and str(show_as).lower() == "free"

    def _generate_statistics(
        self,
        original_appointments: List[Appointment],
        business_appointments: List[Appointment],
        excluded_appointments: List[Appointment],
        overlap_resolutions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate comprehensive statistics about the filtering process."""
        total_count = len(original_appointments)
        business_count = len(business_appointments)
        excluded_count = len(excluded_appointments)

        stats = {
            "total_appointments": total_count,
            "business_appointments": business_count,
            "excluded_appointments": excluded_count,
            "overlap_groups_processed": len(overlap_resolutions),
            "appointments_resolved_by_overlap": 0,
            "appointments_filtered_by_overlap": 0,
            "appointments_still_conflicted": 0,
            "exclusion_reasons": {
                "personal": 0,
                "free_status": 0,
                "invalid_category": 0
            },
            "category_breakdown": {}
        }

        # Add rate calculations
        if total_count > 0:
            stats["exclusion_rate"] = excluded_count / total_count
            stats["business_rate"] = business_count / total_count
        else:
            stats["exclusion_rate"] = 0.0
            stats["business_rate"] = 0.0

        # Count overlap resolution statistics
        for resolution in overlap_resolutions:
            stats["appointments_resolved_by_overlap"] += len(resolution["resolved"])
            stats["appointments_filtered_by_overlap"] += len(resolution["filtered"])
            stats["appointments_still_conflicted"] += len(resolution["conflicts"])

        # Analyze exclusion reasons
        for appointment in excluded_appointments:
            if self._is_free_status_appointment(appointment):
                stats["exclusion_reasons"]["free_status"] += 1
            else:
                customer_info = self.category_service.extract_customer_billing_info(appointment)
                if customer_info["is_personal"]:
                    stats["exclusion_reasons"]["personal"] += 1
                else:
                    stats["exclusion_reasons"]["invalid_category"] += 1

        # Generate category breakdown for business appointments
        for appointment in business_appointments:
            if self._detect_travel_appointment(appointment):
                category = "travel"
            else:
                customer_info = self.category_service.extract_customer_billing_info(appointment)
                category = customer_info.get("billing_type", "unknown")

            stats["category_breakdown"][category] = stats["category_breakdown"].get(category, 0) + 1

        return stats

    def _get_empty_statistics(self) -> Dict[str, Any]:
        """Return empty statistics structure."""
        return {
            "total_appointments": 0,
            "business_appointments": 0,
            "excluded_appointments": 0,
            "overlap_groups_processed": 0,
            "appointments_resolved_by_overlap": 0,
            "appointments_filtered_by_overlap": 0,
            "appointments_still_conflicted": 0,
            "exclusion_reasons": {
                "personal": 0,
                "free_status": 0,
                "invalid_category": 0
            },
            "category_breakdown": {}
        }

    def get_timesheet_statistics(self, appointments: List[Appointment]) -> Dict[str, Any]:
        """
        Get comprehensive timesheet statistics without filtering.

        Args:
            appointments: List of appointments to analyze

        Returns:
            Dictionary with timesheet-relevant statistics
        """
        result = self.filter_appointments_for_timesheet(appointments, include_travel=True)
        return result["statistics"]

    def process_appointments_for_timesheet(
        self,
        appointments: List[Appointment],
        include_travel: bool = True
    ) -> Dict[str, Any]:
        """
        Alias for filter_appointments_for_timesheet for backward compatibility.

        This method provides the same functionality as filter_appointments_for_timesheet
        but with the method name expected by some tests.

        Args:
            appointments: List of appointment model instances to filter
            include_travel: Whether to include travel appointments (default: True)

        Returns:
            Dictionary with keys:
            - 'filtered_appointments': List of business appointments ready for timesheet
            - 'excluded_appointments': List of appointments that were excluded
            - 'overlap_resolutions': List of overlap resolution results
            - 'statistics': Dictionary with filtering and resolution statistics
            - 'issues': List of any issues encountered during processing
        """
        return self.filter_appointments_for_timesheet(appointments, include_travel)

    def close(self):
        """
        Close the service and clean up resources.

        This method ensures that any resources used by the service are properly
        cleaned up when the service is no longer needed.
        """
        if self._closed:
            return

        # Clean up any resources here
        self._closed = True

    def __del__(self):
        """Ensure resources are cleaned up when the service is garbage collected."""
        try:
            self.close()
        except:
            # Ignore errors during garbage collection
            pass
