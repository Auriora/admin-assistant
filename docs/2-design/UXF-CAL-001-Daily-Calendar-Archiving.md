# UX Flow Diagram and Description Template

## Flow Information
- **Flow ID**: UXF-CAL-001
- **Flow Name**: Daily Calendar Archiving
- **Created By**: [Your Name]
- **Creation Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Related Requirements**: FR-CAL-001, FR-CAL-002, FR-CAL-003, FR-CAL-004, FR-CAL-005, FR-CAL-006, FR-CAL-007, FR-CAL-008, FR-CAL-009; UC-CAL-001
- **Priority**: High

## Flow Objective
Enable users to reliably archive all appointments from their main calendar to an archive calendar, either automatically at the end of the day or manually on demand. This flow addresses the needs of single users who require a secure, immutable record of their calendar data for compliance, billing, and historical reference.

## User Personas
- Professional user (primary, single-user scenario)
- (Future) Admin or support user (for troubleshooting)

## Preconditions
- User is authenticated via Microsoft account
- Main and archive calendars exist and are accessible
- User has granted necessary permissions to the applicationnecxt 

## Flow Diagram
```
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

## Detailed Flow Description

### Entry Points
- User logs into the web application and navigates to the dashboard or calendar page.
- System triggers the archiving process automatically at the end of the day.
- User manually clicks the "Archive Now" button.

### Step-by-Step Flow

| Step # | Actor        | Action                                      | System Response                                      | UI Elements                | Notes                                  |
|--------|--------------|---------------------------------------------|------------------------------------------------------|----------------------------|----------------------------------------|
| 1      | User         | Navigates to dashboard/calendar page        | Loads current calendar and archive status             | Dashboard, Archive status  |                                        |
| 2      | User         | Clicks "Archive Now" button                 | Sends archive request to backend                      | "Archive Now" button       | Manual trigger; can also be scheduled  |
| 3      | Backend      | Fetches today's appointments from MS 365    | Receives appointment data                            | N/A                        | Uses Microsoft Graph API               |
| 4      | Backend      | Copies appointments to archive calendar     | Confirms archive success or failure                   | N/A                        | Handles duplicates, overlaps, errors   |
| 5      | Backend      | Returns result to UI                        | Displays success or error message                     | Success/Error notification |                                        |
| 6      | System       | (If scheduled) Triggers archive at EOD      | Same as above, but user is notified only on error     | Email/In-app notification  |                                        |
| 7      | User         | (If error) Reviews error and can retry      | System provides retry option or error details         | Retry button, Error details|                                        |

### Exit Points
- User sees a success message and archived appointments are available.
- User is notified of any errors and can retry or seek help.
- System logs all actions for audit purposes.

### Error Scenarios

| Error Scenario         | Trigger                                 | System Response                                 | User Recovery Action                |
|-----------------------|-----------------------------------------|------------------------------------------------|-------------------------------------|
| API Rate Limit        | Too many requests to MS Graph API       | Shows error, retries with backoff, notifies user| Wait and retry, or try later        |
| Partial Archive Fail  | Some appointments fail to archive       | Notifies user, provides retry option            | Retry archiving, review error log   |
| Duplicate Archive     | Archive already in progress             | Prevents duplicate, shows status                | Wait for completion                 |
| Auth Expired          | User session/token expired              | Prompts user to re-authenticate                 | Log in again                        |
| Calendar Not Found    | Archive calendar missing                | Prompts user to create/select archive calendar  | Create/select calendar              |

## UI Components
- Dashboard with "Archive Now" button and archive status indicator
- Success/Error notification banners or modals
- Retry button (on error)
- Archive log/history panel (optional)
- Loading spinner/progress indicator

## Accessibility Considerations
- All buttons and notifications must be accessible via keyboard and screen readers
- Sufficient color contrast for status indicators
- Error messages should be clear and actionable

## Performance Expectations
- Manual archive should complete within a few seconds for typical daily appointment volume
- UI should remain responsive during background operations
- System should handle API rate limits gracefully

## Related Flows
- Timesheet Generation and Export (UXF-BIL-001)
- Error Notification Flow (UXF-NOT-001)
- Authentication Flow

## Notes
- All archiving actions are logged for audit and compliance
- Future: Support for multi-user and admin troubleshooting

## Change Tracking

This section records the history of changes made to this document. Add a new row for each significant update.

| Version | Date       | Author      | Description of Changes         |
|---------|------------|-------------|-------------------------------|
| 1.0     | 2024-06-11 | [Your Name] | Initial version               |

## Additional UI/UX Note
- When the user clicks the manual archive button, a notification should appear indicating 'Archive started'.
- When the archive completes (success or error), the same notification should be updated to reflect the final state (e.g., 'Archive complete', 'Archive failed').
- This ensures real-time feedback and avoids notification clutter. 