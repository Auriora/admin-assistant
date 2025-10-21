---
title: "HLD: Daily Calendar Archiving"
id: "HLD-CAL-001"
type: [ hld, architecture, workflow ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [hld, calendar, archiving, ux]
links:
  tooling: []
---

# High-Level Design: Daily Calendar Archiving

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Audience**: [Developers, UX Designers, Product Managers]

## 1. Purpose

This document describes the high-level design and user flow for the daily calendar archiving feature. The objective is to enable users to reliably archive all appointments from their main calendar to an archive calendar, either automatically at the end of the day or manually on demand. This creates a secure, immutable record of calendar data for compliance, billing, and historical reference.

## 2. Context

- **User Personas**: The primary user is a professional managing their own administrative tasks.
- **Preconditions**:
  - The user must be authenticated via their Microsoft account.
  - The main and archive calendars must exist and be accessible.
  - The application must have the necessary permissions.

## 3. Details

### 3.1. Flow Diagram

```mermaid
@startuml
actor User
participant "Web UI" as UI
participant "Backend Service" as BE
participant "Microsoft 365 Calendar API" as MSAPI
database "Archive Calendar" as Archive

== Manual Trigger ==
User -> UI: Click "Archive Now" button
UI -> BE: Send archive request
BE -> MSAPI: Fetch today's appointments
MSAPI --> BE: Return appointments
BE -> Archive: Copy appointments
Archive --> BE: Confirm archive
BE -> UI: Show success/failure message

== Automatic (Scheduled) ==
BE -> MSAPI: Scheduled fetch at end of day
MSAPI --> BE: Return appointments
BE -> Archive: Copy appointments
Archive --> BE: Confirm archive
BE -> UI: Notify user (if error)

@enduml
```

### 3.2. Step-by-Step Flow

| Step # | Actor   | Action                                      | System Response                                      |
|--------|---------|---------------------------------------------|------------------------------------------------------|
| 1      | User    | Navigates to the dashboard or calendar page.| Loads the current calendar and archive status.       |
| 2      | User    | Clicks the "Archive Now" button.            | Sends an archive request to the backend.             |
| 3      | Backend | Fetches appointments from Microsoft 365.    | Receives appointment data from the Graph API.        |
| 4      | Backend | Copies appointments to the archive calendar.| Confirms archive success or failure.                 |
| 5      | Backend | Returns the result to the UI.               | Displays a success or error message.                 |
| 6      | System  | (If scheduled) Triggers archive at EOD.     | Notifies the user only if an error occurs.           |

### 3.3. Error Scenarios

| Scenario           | Trigger                                     | System Response                                                    |
|--------------------|---------------------------------------------|--------------------------------------------------------------------|
| API Rate Limit     | Too many requests to the MS Graph API.      | Retries with backoff and notifies the user.                        |
| Partial Failure    | Some appointments fail to archive.          | Notifies the user and provides a retry option.                     |
| Duplicate Archive  | An archive process is already running.      | Prevents a duplicate process and shows the current status.         |
| Auth Expired       | The user's session or token has expired.    | Prompts the user to re-authenticate.                               |
| Overlap Detected   | Overlapping appointments are found.         | Logs the overlap in the ActionLog for manual user resolution.      |

### 3.4. Design Considerations

- **UI Components**: The UI will include an "Archive Now" button, a status indicator, and success/error notifications. A loading spinner will show progress.
- **Real-time Feedback**: When a manual archive is triggered, a notification will appear showing "Archive started." This same notification will update to "Archive complete" or "Archive failed" upon completion.
- **Overlap Resolution**: Overlaps are not resolved during the archiving process. They are logged for the user to resolve manually in a separate, dedicated flow (see `HLD-OVL-001`).

# References

- **Related Requirements**: FR-CAL-001 to FR-CAL-009, UC-CAL-001
- **Related Flows**:
  - [Manual Overlap Resolution](./HLD-OVL-001-Manual-Overlap-Resolution-and-Chat.md)
  - [Timesheet Generation and Export](./HLD-BIL-001-Timesheet-Generation-and-Export.md)