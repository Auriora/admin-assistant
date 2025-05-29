# Admin Assistant Data Model

This document describes the main entities and relationships for the Admin Assistant system, and clarifies the separation between the Flask (web) and core databases. The system uses two distinct databases to support modularity, security, and integration with external services.

## Database Separation

- **Core Database**: Manages business-critical, backend-agnostic entities. Migrated and versioned via Alembic in `core/migrations`.
- **Flask (Web) Database**: Manages user-facing, web-specific, and integration-related entities. Migrated via Flask-Migrate/Alembic in `web/migrations`.

### Entities by Database

| Entity                  | Core DB | Flask/Web DB |
|------------------------|:-------:|:------------:|
| User                   |   ✓     |      ✓       |
| Appointment            |   ✓     |              |
| Location               |   ✓     |              |
| Category               |   ✓     |              |
| Timesheet              |   ✓     |              |
| AuditLog               |   ✓     |              |
| Rule                   |   ✓     |              |
| Notification           |   ✓     |              |
| NotificationClass      |   ✓     |              |
| NotificationPreference |   ✓     |              |
| ArchivePreference      |   ✓     |              |
| VirtualCalendar        |   ✓     |              |
| ChatSession/AIInteraction |  ✓      |              |

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

## VirtualCalendar and ChatSession/AIInteraction

- **VirtualCalendar**: Represents a group of overlapping appointments requiring user resolution. Stores the full details of all appointments in the group, and is referenced by ActionLog entries for overlap resolution actions. Can be implemented as a dedicated table or as a JSON field, but should integrate with repository/service logic for CRUD operations.
- **ChatSession/AIInteraction**: Stores persistent chat history and AI suggestions for each overlap resolution (and other future features). Linked to the relevant VirtualCalendar and user. Enables both synchronous and asynchronous user interaction with AI-powered features.

## Generic Entity Association Table

- **entity_association**: A generic mapping table to associate any entity (calendar, appointment, chat session, action log, etc.) with any other entity. This supports extensibility and reduces the need for multiple mapping tables.
  - `id`: PK
  - `source_type`: str (e.g., 'action_log', 'calendar', 'chat_session', etc.)
  - `source_id`: int
  - `target_type`: str (e.g., 'calendar', 'appointment', 'chat_session', etc.)
  - `target_id`: int
  - `association_type`: str (e.g., 'resolves', 'relates_to', 'has_chat', etc.)
  - `created_at`: datetime

## Prompt Table

- **Prompt**: Stores system, user, and action-specific prompts for AI functionality.
  - `id`: PK
  - `prompt_type`: str (system, user, action-specific)
  - `user_id`: int (nullable, for user-specific prompts)
  - `action_type`: str (nullable, for action/task-specific prompts)
  - `content`: str
  - `created_at`, `updated_at`: datetime

## ActionLog (Updated)

- **ActionLog**: Central task/action list for user attention and audit. Now includes:
  - `id`, `user_id`, `event_type`, `state` (open, resolved, etc.), `description`, `details`, `created_at`, `updated_at`
  - `recommendations`: JSON field to store serialized AI recommendations for the relevant action/task, with metadata (timestamp, prompt, result, accepted, etc.)
  - Linked to other entities (calendar, appointment, chat session, etc.) via `entity_association`.

## ChatSession (Updated)

- **ChatSession**: Persistent chat history and AI suggestions, mapped to actions/tasks or other entities via `entity_association`.
  - `id`, `user_id`, `messages` (JSON), `status` (open, closed), `created_at`, `updated_at`

## Calendar (Clarification)

- **Calendar**: Includes both real and virtual calendars. Virtual calendars are used for grouping overlapping appointments for resolution and are mapped to actions/tasks via `entity_association`.

## Extensibility & Auditability

- The `entity_association` table allows any entity to be linked to any action/task, chat session, or other entity, supporting future features and reducing schema complexity.
- All AI recommendations and user/AI chat interactions are logged in ActionLog and ChatSession, providing a full audit trail for compliance and analytics.
- Prompts can be customized per user, per action, or system-wide, supporting advanced AI integration and user personalization. 