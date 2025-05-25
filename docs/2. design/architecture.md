# Admin Assistant System Architecture

## 1. High-Level Overview

Admin Assistant is a modular, service-oriented web application designed to automate and streamline calendar management, timesheet extraction, billing, and travel calculation for professionals using Microsoft 365 Calendar. The system is built for single-user operation initially, with provisions for future multi-user and role-based support. It integrates with Microsoft 365 Calendar, OneDrive, Xero, Google Directions API, and OpenAI.

---

## 2. Architectural Principles
- **Separation of Concerns:** Clear separation between UI, business logic, data access, and integrations.
- **Extensibility:** Modular design for future features (multi-user, roles, new integrations).
- **Security:** OAuth2/OpenID Connect, encrypted data, secure API handling.
- **Resilience:** Graceful error handling, retries, and user notifications for all external integrations.
- **Auditability:** Centralized, secure logging of all critical actions and changes.

---

## 3. Component Diagram

```mermaid
graph TD
    A[User] --> B[Flask Web App]
    B --> C[UI (Bootstrap/Jinja2)]
    B --> D[Business Logic Services]
    D --> E[Calendar Service]
    D --> F[Timesheet Service]
    D --> G[Travel Service]
    D --> H[Rules/AI Service]
    D --> I[Privacy/Categorization]
    D --> J[Notification Service]
    D --> K[Audit/Logging]
    D --> L[Background Jobs]
    D --> M[Database]
    D --> N[API Integrations]
    N --> O[Microsoft Graph]
    N --> P[OneDrive/Xero]
    N --> Q[Google Directions]
    N --> R[OpenAI]
```

---

## 3.1 System Architecture Diagram

```mermaid
graph LR
    subgraph User Environment
        U[User (Browser)]
    end
    subgraph Application Server
        FW[Flask Web App]
        UI[UI Layer (Jinja2/Bootstrap)]
        BL[Business Logic Layer]
        BG[Background Jobs]
        DB[(Database)]
        AUD[Audit/Logging]
    end
    subgraph Integrations
        MS[Microsoft Graph API]
        OD[OneDrive API]
        XR[Xero API]
        GD[Google Directions API]
        OA[OpenAI API]
    end

    U --> FW
    FW --> UI
    FW --> BL
    FW --> AUD
    FW --> DB
    BL --> DB
    BL --> BG
    BL --> AUD
    BL --> MS
    BL --> OD
    BL --> XR
    BL --> GD
    BL --> OA
    BG --> DB
    BG --> MS
    BG --> OD
    BG --> XR
    BG --> GD
    BG --> OA
    AUD --> DB
```

---

## 4. Component Breakdown

### A. Presentation Layer (UI)
- **Flask + Jinja2 Templates:** Responsive web UI using Bootstrap.
- **Views/Controllers:** For calendar, timesheet, travel, rules, and admin.
- **Authentication:** Microsoft OAuth2/OpenID Connect (Flask extension).

### B. Business Logic Layer
- **Service Modules:**
  - **Calendar Service:** Archiving, overlap resolution, time zone logic.
  - **Timesheet Service:** Extraction, categorization (AI-assisted), PDF/CSV/Excel export.
  - **Travel Service:** Location recommendation, travel time calculation, Google Directions API integration.
  - **Rules Engine:** User-editable rules, OpenAI integration for recommendations.
  - **Privacy & Categorization Service:** Privacy marking, category assignment, user overrides.
  - **Notification Service:** Email and in-app notifications.

### C. Data Layer
- **Database:** Relational (PostgreSQL or SQLite for MVP), storing user profiles, archived appointments, rules, audit logs, configuration, etc.
- **ORM:** SQLAlchemy or Flask-SQLAlchemy for data access.

### D. Integration Layer
- **Microsoft Graph API:** Calendar access, authentication.
- **OneDrive/Xero APIs:** File upload, billing integration.
- **Google Directions API:** Travel time estimation.
- **OpenAI API:** Recommendations, categorization.
- **API Client Modules:** Each integration encapsulated in its own module/service.

### E. Audit & Logging
- **Centralized Logging:** All critical actions, errors, and API calls.
- **Audit Trail:** For automated changes, privacy actions, and user overrides.
- **Log Management:** Pruning/archiving old logs.

### F. Background Processing
- **Task Queue:** For long-running or scheduled jobs (e.g., Celery with Redis/RQ, or Flask background jobs).
- **Examples:** Daily archiving, retrying failed API calls, backup jobs.

---

## 5. Technology Choices

| Layer                | Technology/Tooling                |
|----------------------|-----------------------------------|
| Web Framework        | Flask (Python)                    |
| UI                   | Bootstrap, Jinja2                 |
| Auth                 | Flask-OAuthlib, MSAL, Flask-Login |
| DB                   | PostgreSQL/SQLite + SQLAlchemy    |
| Background Jobs      | Celery, RQ, or Flask-APScheduler  |
| Logging/Audit        | Python logging, DB audit table    |
| API Integrations     | Requests, msal, custom clients    |
| Testing              | Pytest, coverage                  |
| Containerization     | Docker, docker-compose            |

---

## 6. Security & Compliance
- **OAuth2/OpenID Connect:** Microsoft authentication for all users.
- **Role/Permission System:** Designed for future multi-user/role support.
- **Data Encryption:** At rest and in transit (HTTPS).
- **Secrets Management:** Environment variables or secure vault for API keys.
- **Input Sanitization:** Especially for AI and external API calls.
- **Compliance:** GDPR, API ToS, auditability, and user consent.

---

## 7. Extensibility & Maintainability
- **Modular Codebase:** Each service/integration is a separate module.
- **Configurable Settings:** All environment-specific settings externalized.
- **API-First:** Consider exposing core features via REST API for future mobile or third-party integrations.
- **Testing:** Unit and integration tests for all modules, especially for business logic and integrations.

---

## 8. Deployment
- **Containerization:** Docker for consistent deployment.
- **Cloud/On-Premise Ready:** Can be deployed on any standard infrastructure.
- **CI/CD Pipeline:** Automated testing, linting, and deployment.

---

## 9. Future-Proofing
- **Multi-user/Role Support:** Design DB and services with user/role fields, even if only one user for MVP.
- **Plug-in Integrations:** Abstract integration logic for easy addition of new APIs/services.
- **Scalability:** Stateless app servers, scalable DB, and background workers.

---

## 10. Summary

This architecture meets all functional and non-functional requirements, is modular, secure, and extensible for future needs, and supports robust error handling, auditability, and compliance. It is well-suited for a Python/Flask-based web application with multiple third-party integrations. 