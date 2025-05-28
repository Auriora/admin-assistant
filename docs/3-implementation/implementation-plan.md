# Implementation Plan for Admin Assistant

This document outlines a detailed, step-by-step technical implementation plan for the Admin Assistant project. The plan is strictly sequential and dependency-aware, based on the SRS, design, and test documentation. It does not include time schedules or people resources.

---

## 1. Project Foundation & Core Infrastructure

### 1.1 Repository and Environment Setup
- Initialize the codebase structure as per `docs/GPT_AI_GUIDELINES.md`.
- Set up Python virtual environment and install dependencies from `requirements.txt`.
- Configure `.env` files for development, testing, and production.
- Set up logging and observability as per `docs/2-design/observability.md` and `docs/guidelines/observability.md`.
- Initialize the Flask app using the application factory pattern (`app/__init__.py`).
- Set up configuration management (`app/config.py`).

### 1.2 Database and Models
- Implement SQLAlchemy models in `app/models.py` based on `docs/2-design/data-model.md` and `data-model.puml`.
- Set up Alembic/Flask-Migrate for database migrations.
- Create initial migration and apply to development database.

### 1.3 Authentication & Authorization
- Integrate Microsoft OAuth2/OpenID Connect for authentication (Flask-OAuthlib/MSAL).
- Implement user session management and role scaffolding (single-user for MVP, but DB and code ready for multi-user/roles).
- Secure all routes and services to require authentication.

---

## 2. Core Functional Services and Business Logic

### 2.1 Calendar Archiving (FR-CAL-001 to FR-CAL-009)

**Implementation Tasks & Tracking:**

- [ ] **Archive Configuration Table, Repository, and Service**
    - [X] Design and create a database table to store archive configuration (source calendar, destination calendar, user-specific settings, name, is_active).
    - [X] Implement `ArchiveConfigurationRepository` in `core/repositories/` for CRUD operations.
    - [X] Implement `ArchiveConfigurationService` in `core/services/` for business logic and validation.
    - [ ] Integrate configuration loading into the archiving logic (read from DB, not static files/env).

- [ ] **ActionLogRepository Refactor**
    - [ ] Refactor all action logging to use a dedicated `ActionLogRepository` for consistency and maintainability.

- [ ] **UserRepository**
    - [ ] Implement a `UserRepository` for user data access, supporting future multi-user and role-based features.

- [ ] **Core Archiving Service Logic**
    - [ ] Implement/extend the Calendar Archiving Service to:
        - [ ] Fetch appointments from the configured source calendar.
        - [ ] Copy appointments to the configured archive calendar.
        - [ ] Handle time zones, recurring events, and duplicates.
        - [ ] Enforce immutability of archived appointments (except for the user).

- [ ] **Re-Archiving (Replacement) Logic**
    - [ ] Add logic and a service method to allow re-archiving (replacement) of appointments for a specified period, ensuring idempotency and safe replacement.

- [ ] **Overlap Resolution Orchestrator/Service**
    - [ ] Implement an orchestrator/service to detect and resolve overlapping appointments during archiving.
    - [ ] Support user-configurable or default rules for overlap resolution.
    - [ ] Log all overlap resolutions in the ActionLog.

- [ ] **Background Job Management (Scheduled/Manual Triggers)**
    - [ ] Implement background job logic (using Flask-APScheduler or similar) to run archiving at scheduled intervals.
    - [ ] Add manual trigger support (route and service method).

- [ ] **Audit Logging and Traceability**
    - [ ] Ensure all archiving actions, overlap resolutions, and re-archiving operations are logged for traceability and compliance.

- [ ] **Testing and Observability**
    - [ ] Add unit and integration tests for all new repositories, services, and archiving flows.
    - [ ] Add OpenTelemetry tracing and metrics for archiving operations.

- [ ] **Job Configuration Table, Repository, and Service**
    - [ ] Design and create a database table to store job scheduling parameters (e.g., archive_window_days, schedule, archive_configuration_id as FK).
    - [ ] Implement `JobConfigurationRepository` in `core/repositories/` for CRUD operations.
    - [ ] Implement `JobConfigurationService` in `core/services/` for business logic and validation.
    - [ ] Integrate job configuration into background job scheduling and archiving logic.
    
**Parked for future implementation:**
- Notifications (to be handled in a separate module)
- API Rate Limiting (to be revisited after core functionality is stable)

### 2.2 Timesheet Extraction and Billing (FR-BIL-001 to FR-BIL-008)
- Implement Timesheet Service in `app/services/timesheet_service.py`:
  - Extract and categorize appointments from archive.
  - Integrate AI/rules for categorization (see below).
  - Generate PDF (using template or default), CSV, and Excel exports.
  - Integrate with OneDrive and Xero APIs for file upload.
  - Lock archive after billing, handle missed appointments.
  - Handle API failures and user notifications.

### 2.3 Location Recommendation (FR-LOC-001 to FR-LOC-004)
- Implement Location Service in `app/services/location_service.py`:
  - Recommend locations from fixed list and past data.
  - Allow user to add/auto-create locations.
  - Handle conflicts and prompt user as needed.

### 2.4 Travel Calculation (FR-TRV-001 to FR-TRV-008)
- Implement Travel Service in `app/services/travel_service.py`:
  - Calculate travel needs between appointments.
  - Integrate with Google Directions API (traffic, fallback, quota handling).
  - Add travel appointments to calendar/archive.
  - Notify user of issues (unreachable, insufficient time, etc.).

### 2.5 Categorization and Privacy (FR-CAT-001, FR-CAT-002, FR-PRI-001 to FR-PRI-003)
- Implement Categorization Service in `app/services/categorization_service.py`:
  - Use AI/rules for category recommendations.
  - Allow user override.
- Implement Privacy Service in `app/services/privacy_service.py`:
  - Automatically mark personal/travel as private.
  - Exclude private from exports.
  - Maintain privacy log and rollback via UI.

### 2.6 Out-of-Office Automation (FR-OOO-001)
- Implement OOO Service in `app/services/ooo_service.py`:
  - Mark appointments as OOO for selected period.
  - UI for OOO period selection and status.

### 2.7 Rules and Guidelines (FR-RUL-001 to FR-RUL-003)
- Implement Rules Service in `app/services/rules_service.py`:
  - CRUD for user-specific rules via UI.
  - Use rules in recommendations and automation.
  - Integrate with OpenAI for complex recommendations.

### 2.8 Audit Logging (FR-AUD-001, NFR-AUD-001 to NFR-AUD-003)
- Implement AuditLog model and service.
- Log all critical actions (archiving, export, API calls, errors, privacy, OOO, rules changes).
- UI for audit log viewing, searching, and exporting.

### 2.9 Notification Service (FR-NOT-001)
- Implement Notification Service in `app/services/notification_service.py`:
  - In-app and email notifications for errors, conflicts, and important events.
  - Configurable notification methods.

---

## 3. AI Integration (OpenAI) and Advanced Features

### 3.1 OpenAI Integration (FR-AI-001 to FR-AI-006)
- Implement AI Service in `app/services/ai_service.py`:
  - Sanitize and anonymize data before sending to OpenAI.
  - Use for categorization, rules, and recommendations.
  - Allow user to review/override AI output.
  - Handle API downtime, retries, and input sanitization.

### 3.2 Export Functionality (FR-EXP-001, FR-EXP-002)
- Implement export logic for CSV, Excel, and PDF (with special character and large dataset handling).
- UI for export options and download links.

### 3.3 Multi-user and Role Provisions (FR-MUL-001, FR-ROL-001, NFR-MUL-001, NFR-ROL-001/002)
- Add user/role fields to all models and services (already in DB).
- Enforce strict data isolation and role checks in all queries and business logic.
- UI for user/role management (admin only, for future).

---

## 4. User Interface Implementation

### 4.1 UI Foundation
- Set up Bootstrap and Jinja2 templates.
- Implement base layout, navigation, and authentication flows.

### 4.2 Feature-Specific UI
- **Dashboard:** Archive status, quick actions, notifications.
- **Calendar View:** Main and archive calendars, OOO status, privacy indicators.
- **Timesheet/Export Page:** Date picker, export options, category override prompts, upload status.
- **Location Management:** Location assignment, recommendations, conflict resolution.
- **Travel Appointments:** Travel calculation trigger, travel appointment list/alerts.
- **Rules/Guidelines Management:** CRUD UI for rules.
- **Audit Log:** Table with paging, search, export.
- **Notification Panel:** In-app notifications, settings.
- **Privacy Log:** Privacy status, rollback controls.

### 4.3 Accessibility and Responsiveness
- Ensure all UI components are accessible (keyboard, screen reader, color contrast).
- Make all pages responsive for mobile and desktop.

---

## 5. Testing Implementation

### 5.1 Unit Tests
- Write unit tests for all services, models, and utility functions using pytest.
- Mock external APIs for isolated testing.

### 5.2 Integration Tests
- Test route handlers, database interactions, and service integration.
- Use Flask test client and test database.

### 5.3 Functional/End-to-End Tests
- Implement tests for all major user flows as per `docs/4-testing/` (e.g., TC-CAL-001, TC-BIL-001, etc.).
- Cover both success and error scenarios.

### 5.4 Manual and Exploratory Testing
- Validate UI rendering, accessibility, and edge cases.
- Test notification delivery, export downloads, and error handling.

### 5.5 Observability and Logging Tests
- Verify logs are written as per guidelines.
- Check OpenTelemetry traces for all key flows.

---

## 6. Deployment and Extensibility

### 6.1 Containerization
- Add Dockerfile and docker-compose for local and production deployment.

### 6.2 Configuration and Secrets
- Ensure all environment-specific settings are externalized.
- Use environment variables for API keys and secrets.

### 6.3 CI/CD Pipeline
- Set up automated testing, linting, and deployment pipeline.

---

## 7. Documentation and Compliance

- Update and maintain code and API documentation.
- Ensure all code, tests, and documentation align with SRS and design docs.
- Review for GDPR and API ToS compliance.

---

**This plan ensures a logical, dependency-aware sequence for building the Admin Assistant, from core infrastructure to advanced features, UI, and testing, in full alignment with requirements and design.** 