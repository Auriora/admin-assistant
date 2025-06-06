#!/usr/bin/env python3
"""
Helper methods for the Appointment Restoration Service.

This file contains the remaining implementation methods for the restoration service
to keep the main service file manageable.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid

from core.models.appointment import Appointment
from core.models.calendar import Calendar
from core.models.restoration_configuration import RestorationConfiguration, DestinationType
from core.repositories.appointment_repository_sqlalchemy import SQLAlchemyAppointmentRepository


class AppointmentRestorationHelpers:
    """Helper methods for appointment restoration operations."""

    def __init__(self, restoration_service):
        self.service = restoration_service

    def apply_restoration_policies(
        self, appointments: List[Dict[str, Any]], config: RestorationConfiguration
    ) -> List[Dict[str, Any]]:
        """Apply restoration policies to filter and modify appointments."""
        policies = config.restoration_policy or {}
        
        # Apply date range filter
        if "date_range" in policies:
            appointments = self._apply_date_range_filter(appointments, policies["date_range"])
        
        # Apply duplicate detection
        if policies.get("skip_duplicates", True):
            appointments = self._apply_duplicate_detection(appointments, config)
        
        # Apply subject filters
        if "subject_filters" in policies:
            appointments = self._apply_subject_filters(appointments, policies["subject_filters"])
        
        # Apply category filters
        if "category_filters" in policies:
            appointments = self._apply_category_filters(appointments, policies["category_filters"])
        
        return appointments

    def _apply_date_range_filter(
        self, appointments: List[Dict[str, Any]], date_range: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Filter appointments by date range."""
        start_date = datetime.strptime(date_range.get("start", "1900-01-01"), "%Y-%m-%d").date()
        end_date = datetime.strptime(date_range.get("end", "2100-12-31"), "%Y-%m-%d").date()
        
        filtered = []
        for appt in appointments:
            appt_date = appt["start_time"].date() if appt.get("start_time") else None
            if appt_date and start_date <= appt_date <= end_date:
                filtered.append(appt)
        
        print(f"Date range filter: {len(appointments)} -> {len(filtered)} appointments")
        return filtered

    def _apply_duplicate_detection(
        self, appointments: List[Dict[str, Any]], config: RestorationConfiguration
    ) -> List[Dict[str, Any]]:
        """Remove duplicate appointments based on subject and time."""
        # Get existing appointments from destination to check for duplicates
        existing_appointments = self._get_existing_appointments_from_destination(config)
        
        filtered = []
        for appt in appointments:
            is_duplicate = False
            
            for existing in existing_appointments:
                if (appt.get("subject") == existing.get("subject") and
                    appt.get("start_time") == existing.get("start_time")):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered.append(appt)
        
        duplicates_removed = len(appointments) - len(filtered)
        if duplicates_removed > 0:
            print(f"Duplicate detection: removed {duplicates_removed} duplicate appointments")
        
        return filtered

    def _apply_subject_filters(
        self, appointments: List[Dict[str, Any]], subject_filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter appointments by subject patterns."""
        include_patterns = subject_filters.get("include", [])
        exclude_patterns = subject_filters.get("exclude", [])
        
        filtered = []
        for appt in appointments:
            subject = appt.get("subject", "").lower()
            
            # Check include patterns
            if include_patterns:
                include_match = any(pattern.lower() in subject for pattern in include_patterns)
                if not include_match:
                    continue
            
            # Check exclude patterns
            if exclude_patterns:
                exclude_match = any(pattern.lower() in subject for pattern in exclude_patterns)
                if exclude_match:
                    continue
            
            filtered.append(appt)
        
        print(f"Subject filters: {len(appointments)} -> {len(filtered)} appointments")
        return filtered

    def _apply_category_filters(
        self, appointments: List[Dict[str, Any]], category_filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter appointments by category."""
        include_categories = category_filters.get("include", [])
        exclude_categories = category_filters.get("exclude", [])
        
        # Get category mappings
        categories = self.service.category_repo.list()
        category_map = {cat.id: cat.name for cat in categories}
        
        filtered = []
        for appt in appointments:
            category_id = appt.get("category_id")
            category_name = category_map.get(category_id, "")
            
            # Check include categories
            if include_categories:
                include_match = category_name in include_categories
                if not include_match:
                    continue
            
            # Check exclude categories
            if exclude_categories:
                exclude_match = category_name in exclude_categories
                if exclude_match:
                    continue
            
            filtered.append(appt)
        
        print(f"Category filters: {len(appointments)} -> {len(filtered)} appointments")
        return filtered

    def _get_existing_appointments_from_destination(
        self, config: RestorationConfiguration
    ) -> List[Dict[str, Any]]:
        """Get existing appointments from the destination to check for duplicates."""
        try:
            if config.destination_type == DestinationType.LOCAL_CALENDAR.value:
                calendar_name = config.destination_config.get("calendar_name")
                calendars = self.service.local_calendar_repo.list()
                
                for calendar in calendars:
                    if calendar.name == calendar_name:
                        appointment_repo = SQLAlchemyAppointmentRepository(
                            self.service.user, str(calendar.id), self.service.session
                        )
                        appointments = appointment_repo.list_for_user()
                        return [
                            {
                                "subject": appt.subject,
                                "start_time": appt.start_time,
                                "end_time": appt.end_time
                            }
                            for appt in appointments
                        ]
            
            # For other destination types, return empty list for now
            # TODO: Implement for MSGraph and export file destinations
            return []
            
        except Exception as e:
            print(f"Warning: Could not check for existing appointments: {e}")
            return []

    def restore_appointment_to_destination(
        self, appointment_data: Dict[str, Any], config: RestorationConfiguration
    ) -> Dict[str, Any]:
        """Restore a single appointment to the configured destination."""
        if config.destination_type == DestinationType.LOCAL_CALENDAR.value:
            return self._restore_to_local_calendar(appointment_data, config.destination_config)
        elif config.destination_type == DestinationType.MSGRAPH_CALENDAR.value:
            return self._restore_to_msgraph_calendar(appointment_data, config.destination_config)
        elif config.destination_type == DestinationType.EXPORT_FILE.value:
            return self._restore_to_export_file(appointment_data, config.destination_config)
        else:
            raise ValueError(f"Unsupported destination type: {config.destination_type}")

    def _restore_to_local_calendar(
        self, appointment_data: Dict[str, Any], destination_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Restore appointment to a local calendar."""
        calendar_name = destination_config.get("calendar_name")
        
        # Get or create the destination calendar
        destination_calendar = self._get_or_create_local_calendar(calendar_name)
        
        # Find or create appropriate category
        category_id = self._find_or_create_category(appointment_data)
        
        # Create the appointment
        appointment = Appointment(
            user_id=self.service.user.id,
            subject=appointment_data.get("subject", "Restored Appointment"),
            start_time=appointment_data.get("start_time"),
            end_time=appointment_data.get("end_time"),
            calendar_id=str(destination_calendar.id),
            category_id=category_id,
            is_archived=False,
            body_content=appointment_data.get("body_content", ""),
            body_content_type=appointment_data.get("body_content_type", "text")
        )
        
        # Save the appointment
        appointment_repo = SQLAlchemyAppointmentRepository(
            self.service.user, str(destination_calendar.id), self.service.session
        )
        appointment_repo.add(appointment)
        
        # Log the restoration
        self.service.audit_service.log_operation(
            user_id=self.service.user.id,
            action_type="restore",
            operation="appointment_restore",
            status="success",
            message=f"Restored appointment: {appointment.subject}",
            resource_type="appointment",
            resource_id=str(appointment.id),
            details={
                "source_type": appointment_data.get("source_type"),
                "destination_calendar": calendar_name,
                "restoration_method": "generic_restoration_service"
            }
        )
        
        return {
            "appointment_id": appointment.id,
            "subject": appointment.subject,
            "calendar_name": calendar_name,
            "status": "restored"
        }

    def _get_or_create_local_calendar(self, calendar_name: str) -> Calendar:
        """Get or create a local calendar with the specified name."""
        # Check if calendar already exists
        calendars = self.service.local_calendar_repo.list()
        for cal in calendars:
            if cal.name == calendar_name:
                return cal
        
        # Create new calendar
        calendar = Calendar(
            user_id=self.service.user.id,
            name=calendar_name,
            description=f"Calendar for restored appointments: {calendar_name}",
            calendar_type="restoration",
            is_primary=False,
            is_active=True
        )
        
        self.service.local_calendar_repo.add(calendar)
        print(f"Created new calendar: {calendar_name}")
        return calendar

    def _find_or_create_category(self, appointment_data: Dict[str, Any]) -> Optional[int]:
        """Find or create an appropriate category for the appointment."""
        # Try to use existing category if available
        if appointment_data.get("category_id"):
            return appointment_data["category_id"]
        
        # Create a default category for restored appointments
        categories = self.service.category_repo.list()
        for cat in categories:
            if cat.name == "Restored":
                return cat.id
        
        # Create the "Restored" category if it doesn't exist
        try:
            from core.models.category import Category
            restored_category = Category(
                user_id=self.service.user.id,
                name="Restored",
                color="#4CAF50"  # Green color
            )
            self.service.category_repo.add(restored_category)
            return restored_category.id
        except Exception as e:
            print(f"Warning: Could not create category: {e}")
            return None
