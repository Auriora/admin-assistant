---
title: "HLD: User Notification of Issues"
id: "HLD-NOT-001"
type: [ hld, architecture, workflow ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [hld, notification, ux, workflow]
links:
  tooling: []
---

# High-Level Design: User Notification of Issues

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Audience**: [Developers, UX Designers, Product Managers]

## 1. Purpose

This document describes the high-level design for the user notification system. The objective is to notify users of missing or conflicting data, errors, or important system events via configurable channels (email, in-app/toast, or both). The system must support progress updates for long-running tasks, including state and percentage complete. Notifications must be updatable by a unique transaction ID, and the UI must allow users to manage their preferences.

## 2. Context

- **User Personas**: The primary user is a professional managing their own administrative tasks.
- **Preconditions**:
  - The user must be authenticated.
  - The system must detect an event or issue that requires user attention.

## 3. Details

### 3.1. Flow Diagram

```mermaid
@startuml
actor User
participant "Web UI" as UI
participant "Backend Service" as BE
participant "Notification Service" as Notify

BE -> Notify: Detects issue, triggers notification with transaction_id
Notify -> UI: In-app notification (e.g., Toast)
Notify -> User: Email notification (if configured)
User -> UI: Views notification, takes action
@enduml
```

### 3.2. Step-by-Step Flow

| Step # | Actor        | Action                                      | System Response                                      |
|--------|--------------|---------------------------------------------|------------------------------------------------------|
| 1      | System       | Detects an event, issue, or task progress.  | Triggers a notification via the configured channels. |
| 2      | Notification | Creates/updates a notification by `transaction_id`. | The user receives a notification with progress/state.|
| 3      | User         | Views the notification and its status.      | The system logs the user action.                     |
| 4      | User         | Marks the notification as read or takes action. | The system updates the notification state.           |
| 5      | User         | Changes their notification preferences.     | The system updates the delivery channel for future events. |

### 3.3. Error Scenarios

| Scenario             | Trigger                                     | System Response                                 |
|----------------------|---------------------------------------------|-------------------------------------------------|
| Notification Failure | The email or in-app notification fails to send. | The system logs the error and retries or uses a fallback channel. |
| Auth Expired         | The user's session or token has expired.    | The system prompts the user to re-authenticate. |

### 3.4. Design Considerations

- **UI Components**: The UI will include notification banners/modals, an email template, a notification settings page for user preferences, progress bars, state badges, and channel icons.
- **Accessibility**: All notifications must be accessible to screen readers, use sufficient color contrast, and provide clear, actionable content.
- **Performance**: Notifications should be delivered within a few seconds of an event. The UI must remain responsive.

# References

- **Related Requirements**: FR-NOT-001, UC-NOT-001
