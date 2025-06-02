"""
Privacy Automation Service

This service handles automated privacy flag management for appointments.
It determines which appointments should be marked as private based on
business rules and applies privacy settings automatically.

Key Features:
- Automatic privacy detection for personal appointments
- Bulk privacy rule application
- Privacy statistics and reporting
- Integration with category processing
"""

from typing import Any, Dict, List, Optional

from core.models.appointment import Appointment
from core.services.category_processing_service import CategoryProcessingService


class PrivacyAutomationService:
    """Service for automated privacy flag management."""

    def __init__(self, category_service: Optional[CategoryProcessingService] = None):
        """
        Initialize the privacy automation service.

        Args:
            category_service: Optional CategoryProcessingService instance.
                            If not provided, creates a new instance.
        """
        self.category_service = category_service or CategoryProcessingService()

    def should_mark_private(self, appointment: Appointment) -> bool:
        """
        Determine if appointment should be marked as private.

        This method uses the category processing service to determine if an
        appointment is personal (has no valid customer categories) and should
        therefore be marked as private.

        Args:
            appointment: Appointment model instance

        Returns:
            True if appointment should be marked as private, False otherwise
        """
        return self.category_service.should_mark_private(appointment)

    def is_personal_appointment(self, appointment: Appointment) -> bool:
        """
        Check if appointment is personal (no customer category).

        Args:
            appointment: Appointment model instance

        Returns:
            True if appointment is personal, False otherwise
        """
        customer_info = self.category_service.extract_customer_billing_info(appointment)
        return customer_info["is_personal"]

    def apply_privacy_rules(self, appointments: List[Appointment]) -> List[Appointment]:
        """
        Apply privacy rules to list of appointments.

        This method processes a list of appointments and updates their privacy
        flags according to the business rules. It preserves existing privacy
        settings for appointments that are already marked as private.

        Args:
            appointments: List of appointment model instances

        Returns:
            List of appointments with updated privacy flags
        """
        processed_appointments = []

        for appointment in appointments:
            # Create a copy to avoid modifying the original
            processed_appointment = appointment

            # Only update privacy if not already set to private
            if not appointment.is_private:
                if self.should_mark_private(appointment):
                    # Update the sensitivity field to mark as private
                    processed_appointment.sensitivity = "private"

            processed_appointments.append(processed_appointment)

        return processed_appointments

    def update_privacy_flags(self, appointments: List[Appointment]) -> Dict[str, int]:
        """
        Update privacy flags and return statistics.

        This method applies privacy rules to appointments and returns
        detailed statistics about the changes made.

        Args:
            appointments: List of appointment model instances

        Returns:
            Dictionary with privacy update statistics:
            - 'total_appointments': Total number of appointments processed
            - 'already_private': Number of appointments already marked private
            - 'marked_private': Number of appointments newly marked private
            - 'personal_appointments': Number of personal appointments found
            - 'work_appointments': Number of work appointments found
        """
        stats = {
            "total_appointments": len(appointments),
            "already_private": 0,
            "marked_private": 0,
            "personal_appointments": 0,
            "work_appointments": 0,
        }

        for appointment in appointments:
            # Check if already private
            if appointment.is_private:
                stats["already_private"] += 1

            # Check if personal appointment
            if self.is_personal_appointment(appointment):
                stats["personal_appointments"] += 1

                # Mark as private if not already
                if not appointment.is_private:
                    appointment.sensitivity = "private"
                    stats["marked_private"] += 1
            else:
                stats["work_appointments"] += 1

        return stats

    def get_privacy_statistics(self, appointments: List[Appointment]) -> Dict[str, Any]:
        """
        Generate detailed privacy statistics for appointments.

        Args:
            appointments: List of appointment model instances

        Returns:
            Dictionary with detailed privacy statistics
        """
        stats = {
            "total_appointments": len(appointments),
            "private_appointments": 0,
            "public_appointments": 0,
            "personal_appointments": 0,
            "work_appointments": 0,
            "privacy_breakdown": {
                "private": 0,
                "personal": 0,
                "confidential": 0,
                "normal": 0,
            },
        }

        for appointment in appointments:
            # Count privacy levels
            sensitivity = getattr(appointment, "sensitivity", "normal") or "normal"
            stats["privacy_breakdown"][sensitivity.lower()] = (
                stats["privacy_breakdown"].get(sensitivity.lower(), 0) + 1
            )

            # Count private vs public
            if appointment.is_private:
                stats["private_appointments"] += 1
            else:
                stats["public_appointments"] += 1

            # Count personal vs work
            if self.is_personal_appointment(appointment):
                stats["personal_appointments"] += 1
            else:
                stats["work_appointments"] += 1

        return stats
