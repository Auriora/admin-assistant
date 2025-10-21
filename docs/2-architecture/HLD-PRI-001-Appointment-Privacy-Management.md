---
title: "HLD: Appointment Privacy Management"
id: "HLD-PRI-001"
type: [ hld, architecture, workflow ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [hld, privacy, automation, ux]
links:
  tooling: []
---

# High-Level Design: Appointment Privacy Management

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Audience**: [Developers, UX Designers, Product Managers]

## 1. Purpose

This document describes the high-level design for managing appointment privacy. The objective is to automatically mark personal and travel appointments as private, exclude them from timesheet exports, and maintain a log of all privacy changes with the ability to roll back individual changes. This ensures user privacy and supports compliance requirements.

## 2. Context

- **User Personas**: The primary user is a professional who needs to separate personal and billable time.
- **Preconditions**:
  - The user must be authenticated.
  - Appointments must exist in the user's calendar or archive.

## 3. Details

### 3.1. Flow Diagram

```mermaid
@startuml
actor User
participant "Web UI" as UI
participant "Backend Service" as BE
database "Archive Calendar" as Archive
database "Privacy Log" as Log

User -> UI: Views appointment or timesheet
UI -> BE: Check if appointment is personal/travel
BE -> Archive: Identify personal/travel appointments
BE -> Archive: Mark as private
BE -> Log: Record privacy change
BE -> UI: Show privacy status
User -> UI: Reviews privacy status, can roll back
UI -> BE: Request rollback (if needed)
BE -> Archive: Revert privacy status
BE -> Log: Update log
BE -> UI: Confirm update, show status
@enduml
```

### 3.2. Step-by-Step Flow

| Step # | Actor        | Action                                      | System Response                                      |
|--------|--------------|---------------------------------------------|------------------------------------------------------|
| 1      | User/System  | A personal or travel appointment is identified. | The system automatically marks it as private.        |
| 2      | Backend      | Records the privacy change in a log.        | The privacy log is updated with the change details.  |
| 3      | Backend      | Excludes private appointments from exports. | Timesheets and other exports omit private events.    |
| 4      | User         | Reviews the privacy status and can roll back.| The system provides a rollback option in the UI.     |
| 5      | Backend      | Reverts the privacy status if requested.    | Updates the appointment and the privacy log.         |

### 3.3. Error Scenarios

| Scenario         | Trigger                                     | System Response                                 |
|------------------|---------------------------------------------|-------------------------------------------------|
| Log Failure      | A privacy log or database error occurs.     | An error message is shown, allowing a retry.    |
| Rollback Failure | An error occurs while reverting the status. | An error message is shown, allowing a retry.    |
| Save Failure     | A backend or database error occurs.         | An error message is shown, allowing a retry.    |

### 3.4. Design Considerations

- **UI Components**: The UI will include a privacy indicator on appointments, a privacy log/history panel, and a rollback button for each change.
- **Auditability**: All privacy-related actions, whether automated or user-initiated, must be logged for a complete audit trail.

# References

- **Related Requirements**: FR-PRI-001, FR-PRI-002, FR-PRI-003, UC-PRI-001
- **Related Flows**:
  - [Timesheet Generation and Export](./HLD-BIL-001-Timesheet-Generation-and-Export.md)
  - [Appointment Categorization](./HLD-CAT-001-Appointment-Categorization.md)