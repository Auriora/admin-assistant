---
title: "HLD: Appointment Categorization"
id: "HLD-CAT-001"
type: [ hld, architecture, workflow ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [hld, categorization, ai, ux]
links:
  tooling: []
---

# High-Level Design: Appointment Categorization

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Audience**: [Developers, UX Designers, Product Managers]

## 1. Purpose

This document describes the high-level design for the appointment categorization feature. The objective is to enable users to categorize appointments for billing and reporting, using AI-powered recommendations based on subject, attendees, and location, while allowing users to review and override any suggestions. This flow is designed to ensure accurate billing and reduce manual effort.

## 2. Context

- **User Personas**: The primary user is a professional managing their own calendar and billing.
- **Preconditions**:
  - The user must be authenticated.
  - Appointments must exist in the user's calendar or archive.
  - The application must have the necessary permissions to modify appointments.

## 3. Details

### 3.1. Flow Diagram

```mermaid
@startuml
actor User
participant "Web UI" as UI
participant "Backend Service" as BE
database "Archive Calendar" as Archive
participant "OpenAI API" as AI

User -> UI: Views appointment or timesheet
UI -> BE: Request category recommendation
BE -> AI: Analyze subject, attendees, location
AI --> BE: Return recommended category
BE -> UI: Show recommended category
User -> UI: Accepts or overrides category
UI -> BE: Save category to appointment
BE -> Archive: Update appointment
BE -> UI: Confirm update, show status
@enduml
```

### 3.2. Step-by-Step Flow

| Step # | Actor        | Action                                      | System Response                                      |
|--------|--------------|---------------------------------------------|------------------------------------------------------|
| 1      | User/System  | An appointment needs categorization.        | The system prompts the user with a recommended category. |
| 2      | Backend      | Requests a category recommendation from AI. | Returns the recommended category to the UI.          |
| 3      | User         | Accepts or overrides the category.          | Sends the final selection to the backend.            |
| 4      | Backend      | Saves the category to the appointment.      | Updates the appointment in the archive/calendar.     |
| 5      | Backend      | Confirms the update to the UI.              | Displays a success or error message.                 |

### 3.3. Error Scenarios

| Scenario           | Trigger                                     | System Response                                 | User Recovery Action          |
|--------------------|---------------------------------------------|-------------------------------------------------|-------------------------------|
| AI Unavailable     | The OpenAI API is down or returns an error. | Notifies the user and allows manual entry.      | User selects a category manually. |
| Ambiguous Category | The AI cannot determine a category.         | Prompts the user for manual input.              | User selects a category.      |
| Save Failure       | A backend or database error occurs.         | Shows an error message and allows a retry.      | Retry the save operation.     |

### 3.4. Design Considerations

- **UI Components**: The UI will include a category field within the appointment details, a recommendation display, and accept/override buttons.
- **Accessibility**: All controls will be fully accessible via keyboard and screen readers.
- **Performance**: Category recommendations should appear within a second. The UI must remain responsive during all backend operations.

# References

- **Related Requirements**: FR-CAT-001, FR-CAT-002, FR-BIL-002, FR-BIL-005, UC-CAT-001
- **Related Flows**:
  - [Timesheet Generation and Export](./HLD-BIL-001-Timesheet-Generation-and-Export.md)
  - [Daily Calendar Archiving](./HLD-CAL-001-Daily-Calendar-Archiving.md)