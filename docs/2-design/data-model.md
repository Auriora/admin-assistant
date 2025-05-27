# Admin Assistant Data Model

This document describes the main entities and relationships for the Admin Assistant system, and clarifies the separation between the Flask (web) and core databases. The system uses two distinct databases to support modularity, security, and integration with external services.

## Database Separation

- **Core Database**: Manages business-critical, backend-agnostic entities. Migrated and versioned via Alembic in `core/migrations`.
- **Flask (Web) Database**: Manages user-facing, web-specific, and integration-related entities. Migrated via Flask-Migrate/Alembic in `web/migrations`.

### Entities by Database

| Entity                  | Core DB | Flask/Web DB |
|------------------------|:-------:|:------------:|
| User                   |   ✓     |      ✓       |
| Appointment            |   ✓     |      ✓       |
| Location               |   ✓     |      ✓       |
| Category               |   ✓     |      ✓       |
| Timesheet              |   ✓     |      ✓       |
| AuditLog               |         |      ✓       |
| Rule                   |         |      ✓       |
| Notification           |         |      ✓       |
| NotificationClass      |         |      ✓       |
| NotificationPreference |         |      ✓       |
| ArchivePreference      |         |      ✓       |

## Core Database Entities (latest Alembic schema)

- **User**: Represents a system user. Has many appointments, locations, categories, and timesheets.
- **Appointment**: Calendar event, linked to a user, location, and category. Fields include:
  - `ms_event_id`: Original MS Graph event id (nullable string)
  - `recurrence`: RFC 5545 RRULE string for recurring events (nullable)
  - `ms_event_data`: Full original MS Graph event as JSON (nullable)
  - `is_private`, `is_archived`, `is_out_of_office`, `created_at`, `updated_at`, etc.
- **Location**: User-defined or system-recommended locations for appointments.
- **Category**: Billing or classification category for appointments.
- **Timesheet**: Represents a generated timesheet for a user and date range, with export paths and upload status.

## Flask (Web) Database Entities

- **AuditLog**: Records all critical actions for compliance and troubleshooting.
- **Rule**: User-defined rules/guidelines for automation and recommendations.
- **Notification**: In-app or email notifications for user issues, errors, or events.
- **NotificationClass**: Defines types of notifications.
- **NotificationPreference**: User preferences for notification channels.
- **ArchivePreference**: User preferences for archiving calendar data.

## Relationships

- A user owns all their data (appointments, locations, categories, timesheets, etc.).
- Appointments reference a location and a category.
- Timesheets aggregate appointments for a period.
- Audit logs, rules, notifications, and preferences are linked to users and reference actions on other entities (Flask DB only).

## Diagram

See `data-model.puml` for the PlantUML ERD diagram. Entities present in both databases are shown; those only in the Flask DB are marked accordingly in the table above.

## Rationale for Database Separation

- **Security**: Sensitive tokens and user-facing data are isolated in the web database, while core business data is kept separate.
- **Modularity**: Enables independent migration/versioning and supports multiple backends (e.g., SQLAlchemy, MS Graph API) for core entities.
- **Integration**: Facilitates integration with external APIs and services without exposing core business data.
- **Maintainability**: Allows for clear separation of concerns and easier testing, migration, and extension of each layer. 