#!/usr/bin/env python3
"""
Calendar Backup Service

This service provides functionality for backing up calendars and appointments
to various destinations (local calendars, files, cloud storage).

This is designed to work with the appointment restoration service to provide
a complete backup and restore solution.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from enum import Enum

if TYPE_CHECKING:
    from core.models.user import User
    from core.models.appointment import Appointment
    from core.models.calendar import Calendar
    from core.services.audit_log_service import AuditLogService as _AuditSvc
    from core.repositories.audit_log_repository import AuditLogRepository as _AuditRepo
    from core.repositories.calendar_repository_sqlalchemy import SQLAlchemyCalendarRepository as _LocalCalRepo
    from core.repositories.appointment_repository_sqlalchemy import SQLAlchemyAppointmentRepository as _LocalApptRepo
    from core.repositories.calendar_repository_msgraph import MSGraphCalendarRepository as _GraphCalRepo
    from core.repositories.appointment_repository_msgraph import MSGraphAppointmentRepository as _GraphApptRepo
else:  # pragma: no cover - runtime fallback for optional typing helpers
    User = Appointment = Calendar = Any  # type: ignore
    _AuditSvc = Any  # type: ignore
    _AuditRepo = Any  # type: ignore
    _LocalCalRepo = Any  # type: ignore
    _LocalApptRepo = Any  # type: ignore
    _GraphCalRepo = Any  # type: ignore
    _GraphApptRepo = Any  # type: ignore


class BackupFormat(Enum):
    """Supported backup formats."""
    CSV = "csv"
    JSON = "json"
    ICS = "ics"
    LOCAL_CALENDAR = "local_calendar"


class BackupResult:
    """Result of a backup operation."""
    
    def __init__(self):
        self.total_appointments = 0
        self.backed_up = 0
        self.failed = 0
        self.backup_location = ""
        self.backup_format = ""
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.metadata: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            'total_appointments': self.total_appointments,
            'backed_up': self.backed_up,
            'failed': self.failed,
            'backup_location': self.backup_location,
            'backup_format': self.backup_format,
            'errors': self.errors,
            'warnings': self.warnings,
            'metadata': self.metadata
        }


class CalendarBackupService:
    """
    Service for backing up calendars and appointments to various destinations.
    """

    def __init__(self, user_id: int = 1, session=None):
        from core.db import get_session
        from core.models.user import User as _User
        from core.repositories.audit_log_repository import AuditLogRepository as _AuditRepo
        from core.services.audit_log_service import AuditLogService as _AuditSvc
        from core.repositories.calendar_repository_sqlalchemy import SQLAlchemyCalendarRepository as _LocalCalRepo

        self.session = session or get_session()
        self.user: User = self.session.get(_User, user_id)
        if not self.user:
            raise ValueError(f"User with ID {user_id} not found")

        # Initialize repositories/services (local calendar and audit)
        self.audit_repo: _AuditRepo = _AuditRepo(self.session)
        self.audit_service: _AuditSvc = _AuditSvc(self.audit_repo)
        self.local_calendar_repo: _LocalCalRepo = _LocalCalRepo(self.user, self.session)

        # MSGraph repositories (initialized when needed)
        self._msgraph_calendar_repo: _GraphCalRepo | None = None
        self._msgraph_appointment_repo: _GraphApptRepo | None = None

    @property
    def msgraph_calendar_repo(self) -> _GraphCalRepo:
        """Lazy initialization of MSGraph calendar repository."""
        if self._msgraph_calendar_repo is None:
            from core.utilities.graph_utility import get_graph_client
            from core.repositories.calendar_repository_msgraph import MSGraphCalendarRepository as _GraphCalRepo

            graph_client = get_graph_client()
            self._msgraph_calendar_repo = _GraphCalRepo(self.user, graph_client)
        return self._msgraph_calendar_repo

    def backup_calendar_to_file(
        self,
        calendar_name: str,
        backup_path: str,
        backup_format: BackupFormat,
        start_date: date | None = None,
        end_date: date | None = None,
        include_metadata: bool = True
    ) -> BackupResult:
        """
        Backup a calendar to a file.
        
        Args:
            calendar_name: Name of the calendar to backup
            backup_path: Path where the backup file will be saved
            backup_format: Format for the backup (CSV, JSON, ICS)
            start_date: Optional start date for filtering appointments
            end_date: Optional end date for filtering appointments
            include_metadata: Whether to include metadata in the backup
            
        Returns:
            BackupResult with details of the backup operation
        """
        print(f"Starting backup of calendar '{calendar_name}' to {backup_path}")
        print(f"Format: {backup_format.value}")
        if start_date and end_date:
            print(f"Date range: {start_date} to {end_date}")
        print("=" * 80)

        result = BackupResult()
        result.backup_location = backup_path
        result.backup_format = backup_format.value

        # Find the calendar
        calendar = self._find_calendar_by_name(calendar_name)
        if not calendar:
            raise ValueError(f"Calendar '{calendar_name}' not found")

        # Get appointments from the calendar
        appointments = self._get_appointments_from_calendar(calendar, start_date, end_date)
        result.total_appointments = len(appointments)

        if not appointments:
            print("No appointments found to backup.")
            return result

        print(f"Found {len(appointments)} appointments to backup")

        # Create backup directory if it doesn't exist
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)

        # Backup appointments based on format
        try:
            if backup_format == BackupFormat.CSV:
                self._backup_to_csv(appointments, backup_path, include_metadata)
            elif backup_format == BackupFormat.JSON:
                self._backup_to_json(appointments, backup_path, include_metadata)
            elif backup_format == BackupFormat.ICS:
                self._backup_to_ics(appointments, backup_path, include_metadata)
            else:
                raise ValueError(f"Unsupported backup format: {backup_format}")

            result.backed_up = len(appointments)
            print(f"Successfully backed up {result.backed_up} appointments to {backup_path}")

        except Exception as e:
            error_msg = f"Failed to backup calendar: {str(e)}"
            result.errors.append(error_msg)
            result.failed = len(appointments)
            raise

        # Log the backup operation
        self._log_backup_operation(calendar_name, result)

        return result

    def backup_calendar_to_local_calendar(
        self,
        source_calendar_name: str,
        backup_calendar_name: str,
        start_date: date | None = None,
        end_date: date | None = None
    ) -> BackupResult:
        """
        Backup a calendar to another local calendar.
        
        Args:
            source_calendar_name: Name of the source calendar
            backup_calendar_name: Name of the backup calendar (will be created if needed)
            start_date: Optional start date for filtering appointments
            end_date: Optional end date for filtering appointments
            
        Returns:
            BackupResult with details of the backup operation
        """
        print(f"Starting backup of calendar '{source_calendar_name}' to '{backup_calendar_name}'")
        if start_date and end_date:
            print(f"Date range: {start_date} to {end_date}")
        print("=" * 80)

        result = BackupResult()
        result.backup_location = backup_calendar_name
        result.backup_format = BackupFormat.LOCAL_CALENDAR.value

        # Find the source calendar
        source_calendar = self._find_calendar_by_name(source_calendar_name)
        if not source_calendar:
            raise ValueError(f"Source calendar '{source_calendar_name}' not found")

        # Get or create the backup calendar
        backup_calendar = self._get_or_create_backup_calendar(backup_calendar_name)

        # Get appointments from the source calendar
        appointments = self._get_appointments_from_calendar(source_calendar, start_date, end_date)
        result.total_appointments = len(appointments)

        if not appointments:
            print("No appointments found to backup.")
            return result

        print(f"Found {len(appointments)} appointments to backup")

        # Copy appointments to backup calendar
        from core.repositories.appointment_repository_sqlalchemy import (
            SQLAlchemyAppointmentRepository as _LocalApptRepo,
        )
        from core.models.appointment import Appointment as _Appointment

        backup_appointment_repo = _LocalApptRepo(
            self.user, str(backup_calendar.id), self.session
        )

        for appt in appointments:
            try:
                # Create a copy of the appointment
                backup_appointment = _Appointment(
                    user_id=self.user.id,
                    subject=f"[BACKUP] {appt.subject}",
                    start_time=appt.start_time,
                    end_time=appt.end_time,
                    calendar_id=str(backup_calendar.id),
                    category_id=appt.category_id,
                    is_archived=False,
                    body_content=f"Backup of appointment from '{source_calendar_name}'. Original: {appt.body_content}",
                    body_content_type=appt.body_content_type
                )

                backup_appointment_repo.add(backup_appointment)
                result.backed_up += 1

            except Exception as e:
                error_msg = f"Failed to backup appointment '{appt.subject}': {str(e)}"
                result.errors.append(error_msg)
                result.failed += 1

        print(f"Successfully backed up {result.backed_up} appointments to '{backup_calendar_name}'")

        # Log the backup operation
        self._log_backup_operation(source_calendar_name, result)

        return result

    def _find_calendar_by_name(self, calendar_name: str) -> Calendar | None:
        """Find a calendar by name."""
        calendars = self.local_calendar_repo.list()
        for calendar in calendars:
            if calendar.name == calendar_name:
                return calendar
        return None

    def _get_appointments_from_calendar(
        self,
        calendar: Calendar,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Appointment]:
        """Get appointments from a calendar with optional date filtering."""
        from core.repositories.appointment_repository_sqlalchemy import (
            SQLAlchemyAppointmentRepository as _LocalApptRepo,
        )

        appointment_repo = _LocalApptRepo(
            self.user, str(calendar.id), self.session
        )
        
        appointments = appointment_repo.list_for_user()
        
        # Apply date filtering if specified
        if start_date or end_date:
            filtered_appointments = []
            for appt in appointments:
                if appt.start_time:
                    appt_date = appt.start_time.date()
                    if start_date and appt_date < start_date:
                        continue
                    if end_date and appt_date > end_date:
                        continue
                    filtered_appointments.append(appt)
            appointments = filtered_appointments
        
        return appointments

    def _get_or_create_backup_calendar(self, calendar_name: str) -> Calendar:
        """Get or create a backup calendar."""
        # Check if calendar already exists
        calendar = self._find_calendar_by_name(calendar_name)
        if calendar:
            return calendar
        
        # Create new backup calendar
        from core.models.calendar import Calendar as _Calendar
        backup_calendar = _Calendar(
            user_id=self.user.id,
            name=calendar_name,
            description=f"Backup calendar: {calendar_name}",
            calendar_type="backup",
            is_primary=False,
            is_active=True
        )
        
        self.local_calendar_repo.add(backup_calendar)
        print(f"Created new backup calendar: {calendar_name}")
        return backup_calendar

    def _backup_to_csv(
        self, appointments: list[Appointment], backup_path: str, include_metadata: bool
    ) -> None:
        """Backup appointments to CSV format."""
        with open(backup_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'id', 'subject', 'start_time', 'end_time', 'body_content',
                'body_content_type', 'category_id', 'is_archived'
            ]

            if include_metadata:
                fieldnames.extend(['calendar_id', 'user_id', 'created_at', 'updated_at'])

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for appt in appointments:
                row = {
                    'id': appt.id,
                    'subject': appt.subject,
                    'start_time': appt.start_time.isoformat() if appt.start_time else '',
                    'end_time': appt.end_time.isoformat() if appt.end_time else '',
                    'body_content': appt.body_content or '',
                    'body_content_type': appt.body_content_type or 'text',
                    'category_id': appt.category_id,
                    'is_archived': appt.is_archived
                }

                if include_metadata:
                    row.update({
                        'calendar_id': appt.calendar_id,
                        'user_id': appt.user_id,
                        'created_at': appt.created_at.isoformat() if hasattr(appt, 'created_at') and appt.created_at else '',
                        'updated_at': appt.updated_at.isoformat() if hasattr(appt, 'updated_at') and appt.updated_at else ''
                    })

                writer.writerow(row)

    def _backup_to_json(
        self, appointments: list[Appointment], backup_path: str, include_metadata: bool
    ) -> None:
        """Backup appointments to JSON format."""
        backup_data = {
            'backup_info': {
                'created_at': datetime.now().isoformat(),
                'user_id': self.user.id,
                'user_email': self.user.email,
                'total_appointments': len(appointments)
            },
            'appointments': []
        }

        for appt in appointments:
            appt_data = {
                'id': appt.id,
                'subject': appt.subject,
                'start_time': appt.start_time.isoformat() if appt.start_time else None,
                'end_time': appt.end_time.isoformat() if appt.end_time else None,
                'body_content': appt.body_content,
                'body_content_type': appt.body_content_type,
                'category_id': appt.category_id,
                'is_archived': appt.is_archived
            }

            if include_metadata:
                appt_data.update({
                    'calendar_id': appt.calendar_id,
                    'user_id': appt.user_id,
                    'created_at': appt.created_at.isoformat() if hasattr(appt, 'created_at') and appt.created_at else None,
                    'updated_at': appt.updated_at.isoformat() if hasattr(appt, 'updated_at') and appt.updated_at else None
                })

            backup_data['appointments'].append(appt_data)

        with open(backup_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(backup_data, jsonfile, indent=2, ensure_ascii=False)

    def _backup_to_ics(
        self, appointments: list[Appointment], backup_path: str, include_metadata: bool
    ) -> None:
        """Backup appointments to ICS (iCalendar) format."""
        with open(backup_path, 'w', encoding='utf-8') as icsfile:
            # Write ICS header
            icsfile.write("BEGIN:VCALENDAR\n")
            icsfile.write("VERSION:2.0\n")
            icsfile.write("PRODID:-//Admin Assistant//Calendar Backup//EN\n")
            icsfile.write("CALSCALE:GREGORIAN\n")

            for appt in appointments:
                # Write event
                icsfile.write("BEGIN:VEVENT\n")
                icsfile.write(f"UID:{appt.id}@admin-assistant\n")

                if appt.start_time:
                    start_str = appt.start_time.strftime("%Y%m%dT%H%M%SZ")
                    icsfile.write(f"DTSTART:{start_str}\n")

                if appt.end_time:
                    end_str = appt.end_time.strftime("%Y%m%dT%H%M%SZ")
                    icsfile.write(f"DTEND:{end_str}\n")

                if appt.subject:
                    # Escape special characters in ICS format
                    subject = appt.subject.replace(',', '\\,').replace(';', '\\;').replace('\n', '\\n')
                    icsfile.write(f"SUMMARY:{subject}\n")

                if appt.body_content:
                    # Escape special characters in ICS format
                    description = appt.body_content.replace(',', '\\,').replace(';', '\\;').replace('\n', '\\n')
                    icsfile.write(f"DESCRIPTION:{description}\n")

                # Add metadata as custom properties if requested
                if include_metadata:
                    icsfile.write(f"X-ADMIN-ASSISTANT-ID:{appt.id}\n")
                    icsfile.write(f"X-ADMIN-ASSISTANT-CALENDAR-ID:{appt.calendar_id}\n")
                    if appt.category_id:
                        icsfile.write(f"X-ADMIN-ASSISTANT-CATEGORY-ID:{appt.category_id}\n")

                icsfile.write("END:VEVENT\n")

            # Write ICS footer
            icsfile.write("END:VCALENDAR\n")

    def _log_backup_operation(self, calendar_name: str, result: BackupResult) -> None:
        """Log the backup operation for audit purposes."""
        self.audit_service.log_operation(
            user_id=self.user.id,
            action_type="backup",
            operation="calendar_backup",
            status="success" if result.failed == 0 else "partial",
            message=f"Backed up {result.backed_up} appointments from calendar '{calendar_name}'",
            resource_type="calendar",
            resource_id=calendar_name,
            details={
                "calendar_name": calendar_name,
                "backup_location": result.backup_location,
                "backup_format": result.backup_format,
                "total_appointments": result.total_appointments,
                "backed_up": result.backed_up,
                "failed": result.failed,
                "errors": result.errors[:10]  # Limit errors in audit log
            }
        )

    def list_backup_files(self, backup_directory: str) -> list[dict[str, Any]]:
        """List available backup files in a directory."""
        if not os.path.exists(backup_directory):
            return []

        backup_files = []
        for filename in os.listdir(backup_directory):
            file_path = os.path.join(backup_directory, filename)
            if os.path.isfile(file_path):
                file_info = {
                    'filename': filename,
                    'path': file_path,
                    'size': os.path.getsize(file_path),
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                    'format': self._detect_backup_format(filename)
                }
                backup_files.append(file_info)

        return sorted(backup_files, key=lambda x: x['modified'], reverse=True)

    def _detect_backup_format(self, filename: str) -> str:
        """Detect backup format from filename extension."""
        if filename.lower().endswith('.csv'):
            return BackupFormat.CSV.value
        elif filename.lower().endswith('.json'):
            return BackupFormat.JSON.value
        elif filename.lower().endswith('.ics'):
            return BackupFormat.ICS.value
        else:
            return 'unknown'
