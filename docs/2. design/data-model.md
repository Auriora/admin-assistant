# Admin Assistant Data Model

This document describes the main entities and relationships for the Admin Assistant system, suitable for implementation in SQLite with SQLAlchemy.

## Key Entities and Relationships

- **User**: Represents a system user (single-user for MVP, multi-user for future). Has many appointments, locations, categories, timesheets, audit logs, rules, and notifications.
- **Appointment**: Calendar event, linked to a user, location, and category. Can be marked as private, archived, or out-of-office.
- **Location**: User-defined or system-recommended locations for appointments.
- **Category**: Billing or classification category for appointments (e.g., Billable, Non-billable, Travel).
- **Timesheet**: Represents a generated timesheet for a user and date range, with export paths and upload status.
- **AuditLog**: Records all critical actions for compliance and troubleshooting.
- **Rule**: User-defined rules/guidelines for automation and recommendations.
- **Notification**: In-app or email notifications for user issues, errors, or events.

### Relationships

- A user owns all their data (appointments, locations, categories, etc.).
- Appointments reference a location and a category.
- Timesheets aggregate appointments for a period.
- Audit logs and notifications are linked to users and reference actions on other entities.

## Diagram

See `data-model.puml` for the PlantUML ERD diagram. 