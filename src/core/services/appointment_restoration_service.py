#!/usr/bin/env python3
"""
Generic Appointment Restoration Service

This service provides a unified interface for restoring appointments from various sources
(audit logs, backup calendars, export files) to various destinations (local calendars,
MSGraph calendars, export files).

The service supports:
- Multiple restoration sources and destinations
- Configurable restoration policies
- Comprehensive audit logging
- Dry-run capabilities
- Conflict resolution strategies
"""

import json
import csv
import os
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from enum import Enum

from core.db import get_session
from core.models.user import User
from core.models.appointment import Appointment
from core.models.calendar import Calendar
from core.models.restoration_configuration import (
    RestorationConfiguration, 
    RestorationType, 
    DestinationType
)
from core.repositories.restoration_configuration_repository import RestorationConfigurationRepository
from core.repositories.audit_log_repository import AuditLogRepository
from core.repositories.calendar_repository_sqlalchemy import SQLAlchemyCalendarRepository
from core.repositories.appointment_repository_sqlalchemy import SQLAlchemyAppointmentRepository
from core.repositories.calendar_repository_msgraph import MSGraphCalendarRepository
from core.repositories.appointment_repository_msgraph import MSGraphAppointmentRepository
from core.repositories.category_repository import SQLAlchemyCategoryRepository
from core.services.audit_log_service import AuditLogService
from core.utilities.graph_utility import get_graph_client


class ConflictResolutionStrategy(Enum):
    """Strategies for handling conflicts during restoration."""
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"
    MERGE = "merge"


class RestorationResult:
    """Result of a restoration operation."""
    
    def __init__(self):
        self.total_found = 0
        self.restored = 0
        self.failed = 0
        self.skipped = 0
        self.restored_appointments = []
        self.failed_restorations = []
        self.skipped_appointments = []
        self.errors = []
        self.warnings = []
        self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            'total_found': self.total_found,
            'restored': self.restored,
            'failed': self.failed,
            'skipped': self.skipped,
            'restored_appointments': self.restored_appointments,
            'failed_restorations': self.failed_restorations,
            'skipped_appointments': self.skipped_appointments,
            'errors': self.errors,
            'warnings': self.warnings,
            'metadata': self.metadata
        }


class AppointmentRestorationService:
    """
    Generic service for restoring appointments from various sources to various destinations.
    """

    def __init__(self, user_id: int = 1, session=None):
        self.session = session or get_session()
        self.user = self.session.get(User, user_id)
        if not self.user:
            raise ValueError(f"User with ID {user_id} not found")

        # Initialize repositories
        self.restoration_config_repo = RestorationConfigurationRepository(self.session)
        self.audit_repo = AuditLogRepository(self.session)
        self.audit_service = AuditLogService(self.audit_repo)
        self.local_calendar_repo = SQLAlchemyCalendarRepository(self.user, self.session)
        self.category_repo = SQLAlchemyCategoryRepository(self.user, self.session)

        # MSGraph repositories (initialized when needed)
        self._msgraph_calendar_repo = None
        self._msgraph_appointment_repo = None

    @property
    def msgraph_calendar_repo(self):
        """Lazy initialization of MSGraph calendar repository."""
        if self._msgraph_calendar_repo is None:
            graph_client = get_graph_client()
            self._msgraph_calendar_repo = MSGraphCalendarRepository(self.user, graph_client)
        return self._msgraph_calendar_repo

    @property
    def msgraph_appointment_repo(self):
        """Lazy initialization of MSGraph appointment repository."""
        if self._msgraph_appointment_repo is None:
            graph_client = get_graph_client()
            self._msgraph_appointment_repo = MSGraphAppointmentRepository(
                self.user, None, graph_client
            )
        return self._msgraph_appointment_repo

    def restore_from_configuration(
        self, 
        config: RestorationConfiguration, 
        dry_run: bool = False
    ) -> RestorationResult:
        """
        Restore appointments using a restoration configuration.
        
        Args:
            config: RestorationConfiguration defining the restoration operation
            dry_run: If True, perform analysis without actually restoring appointments
            
        Returns:
            RestorationResult with details of the restoration operation
        """
        if not config.is_valid():
            raise ValueError(f"Invalid restoration configuration: {config.name}")

        print(f"Starting restoration using configuration: {config.name}")
        print(f"Source: {config.source_type} -> Destination: {config.destination_type}")
        if dry_run:
            print("DRY RUN MODE - No appointments will be actually restored")
        print("=" * 80)

        # Get appointments from source
        appointments = self._get_appointments_from_source(config)
        
        result = RestorationResult()
        result.total_found = len(appointments)
        result.metadata['configuration_name'] = config.name
        result.metadata['source_type'] = config.source_type
        result.metadata['destination_type'] = config.destination_type
        result.metadata['dry_run'] = dry_run

        if not appointments:
            print("No appointments found to restore.")
            return result

        print(f"Found {len(appointments)} appointments to restore")

        # Apply restoration policies
        filtered_appointments = self._apply_restoration_policies(appointments, config)
        result.skipped = len(appointments) - len(filtered_appointments)
        
        if result.skipped > 0:
            print(f"Skipped {result.skipped} appointments due to restoration policies")

        # Restore appointments to destination
        if not dry_run:
            for appointment_data in filtered_appointments:
                try:
                    restored_appointment = self._restore_appointment_to_destination(
                        appointment_data, config
                    )
                    result.restored_appointments.append(restored_appointment)
                    result.restored += 1
                except Exception as e:
                    error_msg = f"Failed to restore appointment {appointment_data.get('subject', 'Unknown')}: {str(e)}"
                    result.failed_restorations.append({
                        'appointment': appointment_data,
                        'error': error_msg
                    })
                    result.failed += 1
                    result.errors.append(error_msg)
        else:
            # In dry run mode, just count what would be restored
            result.restored = len(filtered_appointments)
            result.restored_appointments = [
                {'subject': appt.get('subject', 'Unknown'), 'dry_run': True}
                for appt in filtered_appointments
            ]

        # Log the restoration operation
        self._log_restoration_operation(config, result)

        return result

    def _get_appointments_from_source(
        self, config: RestorationConfiguration
    ) -> List[Dict[str, Any]]:
        """Get appointments from the configured source."""
        if config.source_type == RestorationType.AUDIT_LOG.value:
            return self._get_appointments_from_audit_log(config.source_config)
        elif config.source_type == RestorationType.BACKUP_CALENDAR.value:
            return self._get_appointments_from_backup_calendar(config.source_config)
        elif config.source_type == RestorationType.EXPORT_FILE.value:
            return self._get_appointments_from_export_file(config.source_config)
        else:
            raise ValueError(f"Unsupported source type: {config.source_type}")

    def _get_appointments_from_audit_log(
        self, source_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract appointments from audit logs."""
        action_types = source_config.get("action_types", ["archive", "restore"])
        date_range = source_config.get("date_range", {})
        status_filter = source_config.get("status", "failure")

        start_date = datetime.strptime(date_range.get("start", "2025-05-29"), "%Y-%m-%d").date()
        end_date = datetime.strptime(date_range.get("end", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d").date()

        print(f"Extracting appointments from audit logs...")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Action types: {action_types}")
        print(f"Status filter: {status_filter}")

        # Get audit logs for the specified criteria
        filters = {
            "user_id": self.user.id,
            "start_date": start_date,
            "end_date": end_date,
            "status": status_filter
        }

        audit_logs = self.audit_repo.search(filters)

        appointments = []
        for log in audit_logs:
            if log.action_type in action_types and log.resource_type == "appointment":
                # Extract appointment details from audit log
                appointment_info = self._extract_appointment_from_audit_log(log)
                if appointment_info:
                    appointments.append(appointment_info)

        print(f"Found {len(appointments)} appointments in audit logs")
        return appointments

    def _extract_appointment_from_audit_log(self, audit_log) -> Optional[Dict[str, Any]]:
        """Extract appointment information from an audit log entry."""
        try:
            details = audit_log.details or {}
            request_data = audit_log.request_data or {}

            # Try to extract appointment details from various fields
            subject = (
                details.get("subject") or
                request_data.get("subject") or
                audit_log.message or
                "Recovered Appointment"
            )

            # Extract or estimate appointment times
            start_time = None
            end_time = None

            if "start_time" in details:
                start_time = datetime.fromisoformat(details["start_time"])
            elif "start_date" in details:
                start_time = datetime.combine(
                    datetime.strptime(details["start_date"], "%Y-%m-%d").date(),
                    datetime.min.time().replace(hour=9)  # Default to 9 AM
                )

            if "end_time" in details:
                end_time = datetime.fromisoformat(details["end_time"])
            elif start_time:
                end_time = start_time + timedelta(hours=1)  # Default 1-hour duration

            if not start_time:
                # Use audit log creation time as fallback
                start_time = audit_log.created_at.replace(hour=9, minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(hours=1)

            return {
                "subject": subject,
                "start_time": start_time,
                "end_time": end_time,
                "body_content": f"Restored from audit log {audit_log.id}. Original error: {audit_log.message}",
                "body_content_type": "text",
                "log_id": audit_log.id,
                "error": audit_log.message,
                "source_type": "audit_log",
                "original_resource_id": audit_log.resource_id
            }
        except Exception as e:
            print(f"Failed to extract appointment from audit log {audit_log.id}: {e}")
            return None

    def _get_appointments_from_backup_calendar(
        self, source_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get appointments from backup calendars."""
        calendar_names = source_config.get("calendar_names", [])
        date_range = source_config.get("date_range", {})

        print(f"Retrieving appointments from backup calendars: {calendar_names}")

        appointments = []
        local_calendars = self.local_calendar_repo.list()

        for calendar in local_calendars:
            if calendar.name in calendar_names:
                print(f"Processing calendar: {calendar.name}")

                appointment_repo = SQLAlchemyAppointmentRepository(
                    self.user, str(calendar.id), self.session
                )

                calendar_appointments = appointment_repo.list_for_user()

                # Apply date range filter if specified
                if date_range:
                    start_date = datetime.strptime(date_range.get("start", "1900-01-01"), "%Y-%m-%d").date()
                    end_date = datetime.strptime(date_range.get("end", "2100-12-31"), "%Y-%m-%d").date()

                    calendar_appointments = [
                        appt for appt in calendar_appointments
                        if appt.start_time and start_date <= appt.start_time.date() <= end_date
                    ]

                for appt in calendar_appointments:
                    appointments.append({
                        "subject": appt.subject,
                        "start_time": appt.start_time,
                        "end_time": appt.end_time,
                        "body_content": appt.body_content,
                        "body_content_type": appt.body_content_type,
                        "category_id": appt.category_id,
                        "source_type": "backup_calendar",
                        "source_calendar": calendar.name,
                        "source_calendar_id": calendar.id,
                        "original_appointment": appt
                    })

                print(f"Found {len(calendar_appointments)} appointments in '{calendar.name}'")

        print(f"Total appointments from backup calendars: {len(appointments)}")
        return appointments

    def _get_appointments_from_export_file(
        self, source_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get appointments from export files (CSV, JSON, etc.)."""
        file_path = source_config.get("file_path")
        file_format = source_config.get("file_format", "csv")

        if not file_path or not os.path.exists(file_path):
            raise ValueError(f"Export file not found: {file_path}")

        print(f"Reading appointments from export file: {file_path} (format: {file_format})")

        appointments = []

        if file_format.lower() == "csv":
            appointments = self._read_appointments_from_csv(file_path)
        elif file_format.lower() == "json":
            appointments = self._read_appointments_from_json(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

        print(f"Found {len(appointments)} appointments in export file")
        return appointments

    def _read_appointments_from_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """Read appointments from CSV file."""
        appointments = []

        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    # Parse datetime fields
                    start_time = datetime.fromisoformat(row.get('start_time', ''))
                    end_time = datetime.fromisoformat(row.get('end_time', ''))

                    appointments.append({
                        "subject": row.get('subject', 'Imported Appointment'),
                        "start_time": start_time,
                        "end_time": end_time,
                        "body_content": row.get('body_content', ''),
                        "body_content_type": row.get('body_content_type', 'text'),
                        "source_type": "export_file",
                        "source_file": file_path,
                        "original_row": row
                    })
                except Exception as e:
                    print(f"Failed to parse CSV row: {row}. Error: {e}")

        return appointments

    def _read_appointments_from_json(self, file_path: str) -> List[Dict[str, Any]]:
        """Read appointments from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)

        appointments = []

        # Handle different JSON structures
        if isinstance(data, list):
            appointment_list = data
        elif isinstance(data, dict) and 'appointments' in data:
            appointment_list = data['appointments']
        else:
            raise ValueError("Unsupported JSON structure")

        for item in appointment_list:
            try:
                # Parse datetime fields
                start_time = datetime.fromisoformat(item.get('start_time', ''))
                end_time = datetime.fromisoformat(item.get('end_time', ''))

                appointments.append({
                    "subject": item.get('subject', 'Imported Appointment'),
                    "start_time": start_time,
                    "end_time": end_time,
                    "body_content": item.get('body_content', ''),
                    "body_content_type": item.get('body_content_type', 'text'),
                    "source_type": "export_file",
                    "source_file": file_path,
                    "original_item": item
                })
            except Exception as e:
                print(f"Failed to parse JSON item: {item}. Error: {e}")

        return appointments

    def _apply_restoration_policies(
        self, appointments: List[Dict[str, Any]], config: RestorationConfiguration
    ) -> List[Dict[str, Any]]:
        """Apply restoration policies to filter and modify appointments."""
        from core.services.appointment_restoration_service_helpers import AppointmentRestorationHelpers
        helpers = AppointmentRestorationHelpers(self)
        return helpers.apply_restoration_policies(appointments, config)

    def _restore_appointment_to_destination(
        self, appointment_data: Dict[str, Any], config: RestorationConfiguration
    ) -> Dict[str, Any]:
        """Restore a single appointment to the configured destination."""
        from core.services.appointment_restoration_service_helpers import AppointmentRestorationHelpers
        helpers = AppointmentRestorationHelpers(self)
        return helpers.restore_appointment_to_destination(appointment_data, config)

    def _log_restoration_operation(
        self, config: RestorationConfiguration, result
    ) -> None:
        """Log the restoration operation for audit purposes."""
        self.audit_service.log_operation(
            user_id=self.user.id,
            action_type="restore",
            operation="bulk_appointment_restore",
            status="success" if result.failed == 0 else "partial",
            message=f"Restored {result.restored} appointments using configuration '{config.name}'",
            resource_type="appointment",
            resource_id=str(config.id),
            details={
                "configuration_name": config.name,
                "source_type": config.source_type,
                "destination_type": config.destination_type,
                "total_found": result.total_found,
                "restored": result.restored,
                "failed": result.failed,
                "skipped": result.skipped,
                "errors": result.errors[:10]  # Limit errors in audit log
            }
        )

    def create_configuration(
        self,
        name: str,
        source_type: str,
        source_config: Dict[str, Any],
        destination_type: str,
        destination_config: Dict[str, Any],
        restoration_policy: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> RestorationConfiguration:
        """Create a new restoration configuration."""
        config = RestorationConfiguration(
            user_id=self.user.id,
            name=name,
            description=description,
            source_type=source_type,
            source_config=source_config,
            destination_type=destination_type,
            destination_config=destination_config,
            restoration_policy=restoration_policy or {},
            is_active=True
        )

        if not config.is_valid():
            raise ValueError(f"Invalid restoration configuration: {config}")

        return self.restoration_config_repo.add(config)

    def list_configurations(self) -> List[RestorationConfiguration]:
        """List all restoration configurations for the current user."""
        return self.restoration_config_repo.list_for_user(self.user.id)

    def get_configuration(self, config_id: int) -> Optional[RestorationConfiguration]:
        """Get a restoration configuration by ID."""
        return self.restoration_config_repo.get_by_id(config_id)

    def delete_configuration(self, config_id: int) -> bool:
        """Delete a restoration configuration."""
        return self.restoration_config_repo.delete(config_id)

    def restore_from_audit_logs(
        self,
        start_date: date,
        end_date: date,
        destination_calendar: str = "Recovered",
        action_types: List[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Convenience method to restore appointments from audit logs.

        This method creates a temporary configuration and performs the restoration.
        """
        if action_types is None:
            action_types = ["archive", "restore"]

        # Create temporary configuration
        config = RestorationConfiguration(
            user_id=self.user.id,
            name=f"Temp Audit Log Restoration {datetime.now().isoformat()}",
            source_type=RestorationType.AUDIT_LOG.value,
            source_config={
                "action_types": action_types,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "status": "failure"
            },
            destination_type=DestinationType.LOCAL_CALENDAR.value,
            destination_config={
                "calendar_name": destination_calendar
            },
            restoration_policy={
                "skip_duplicates": True,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
        )

        result = self.restore_from_configuration(config, dry_run)
        return result.to_dict()

    def restore_from_backup_calendars(
        self,
        calendar_names: List[str],
        destination_calendar: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Convenience method to restore appointments from backup calendars.
        """
        date_range = {}
        if start_date:
            date_range["start"] = start_date.isoformat()
        if end_date:
            date_range["end"] = end_date.isoformat()

        # Create temporary configuration
        config = RestorationConfiguration(
            user_id=self.user.id,
            name=f"Temp Backup Calendar Restoration {datetime.now().isoformat()}",
            source_type=RestorationType.BACKUP_CALENDAR.value,
            source_config={
                "calendar_names": calendar_names,
                "date_range": date_range
            },
            destination_type=DestinationType.LOCAL_CALENDAR.value,
            destination_config={
                "calendar_name": destination_calendar
            },
            restoration_policy={
                "skip_duplicates": True
            }
        )

        result = self.restore_from_configuration(config, dry_run)
        return result.to_dict()
