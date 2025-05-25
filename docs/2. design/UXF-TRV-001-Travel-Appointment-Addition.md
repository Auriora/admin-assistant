# UX Flow Diagram and Description Template

## Flow Information
- **Flow ID**: UXF-TRV-001
- **Flow Name**: Travel Appointment Addition
- **Created By**: [Your Name]
- **Creation Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Related Requirements**: FR-TRV-001, FR-TRV-002, FR-TRV-003, FR-TRV-004, FR-TRV-005, FR-TRV-006, FR-TRV-007, FR-TRV-008; UC-TRV-001
- **Priority**: High

## Flow Objective
Automatically add travel appointments to the user's calendar based on location data, using Google Directions API for travel time estimation and handling exceptions such as multi-day trips and traffic data unavailability. This flow ensures accurate travel time tracking for billing and scheduling.

## User Personas
- Professional user (primary, single-user scenario)
- (Future) Admin or support user (for troubleshooting)

## Preconditions
- User is authenticated via Microsoft account
- Appointments with different locations exist in the calendar
- User profile has Home location configured
- User has granted necessary permissions to the application

## Flow Diagram
```
@startuml
actor User
participant "Web UI" as UI
participant "Backend Service" as BE
database "Archive Calendar" as Archive
participant "Google Directions API" as GAPI

User -> UI: Views calendar or triggers travel calculation
UI -> BE: Request travel appointment addition
BE -> Archive: Fetch appointments and locations
BE -> GAPI: Request travel time between locations
GAPI --> BE: Return travel time (or error)
BE -> Archive: Add travel appointments
BE -> UI: Show travel appointments and status
@enduml
```

## Detailed Flow Description

### Entry Points
- User views calendar or triggers travel calculation (manually or as part of archiving/export process).
- System detects appointments requiring travel and initiates calculation.

### Step-by-Step Flow

| Step # | Actor        | Action                                      | System Response                                      | UI Elements                | Notes                                  |
|--------|--------------|---------------------------------------------|------------------------------------------------------|----------------------------|----------------------------------------|
| 1      | User/System  | Triggers travel calculation (manual/auto)   | System identifies appointments needing travel        | Button, auto-trigger       | Can be part of archiving/export        |
| 2      | Backend      | Fetches appointments and locations          | Returns list of appointment pairs needing travel     | N/A                        |                                        |
| 3      | Backend      | Requests travel time from Google API        | Receives travel time or error                        | N/A                        | Handles API quota, errors              |
| 4      | Backend      | Adds travel appointments to calendar        | Confirms addition or shows error                     | N/A                        | Handles exceptions, multi-day trips    |
| 5      | Backend      | Returns result to UI                        | Displays travel appointments, errors, or alerts      | Travel appt list, alerts   | Alerts for insufficient travel time    |
| 6      | User         | Reviews travel appointments/alerts          | Can adjust or retry if needed                        | Travel appt list, Retry    |                                        |

### Exit Points
- Travel appointments are added to the calendar.
- User is notified of any errors, conflicts, or insufficient travel time.
- System logs all actions for audit purposes.

### Error Scenarios

| Error Scenario         | Trigger                                 | System Response                                 | User Recovery Action                |
|-----------------------|-----------------------------------------|------------------------------------------------|-------------------------------------|
| API Quota Exceeded    | Google Directions API limit reached      | Notifies user, skips travel calculation         | Retry later, check API usage        |
| Route Unreachable     | Invalid source/destination               | Prompts user to check locations                 | User corrects location              |
| Traffic Data Unavail. | No traffic data from API                 | Uses standard travel time, notifies user        | Accept fallback or retry            |
| Insufficient Time     | Back-to-back appointments, not enough travel time | Alerts user via email/UI                | User adjusts schedule               |
| Auth Expired          | User session/token expired               | Prompts user to re-authenticate                 | Log in again                        |

## UI Components
- Calendar view with travel appointments
- Travel calculation trigger button (if manual)
- Travel appointment list/summary
- Error/alert banners or modals
- Retry button (on error)

## Accessibility Considerations
- All controls accessible via keyboard and screen readers
- Sufficient color contrast for travel and error indicators
- Clear, actionable error messages and alerts

## Performance Expectations
- Travel calculation and appointment addition should complete within a few seconds for typical data volumes
- UI should remain responsive during background operations
- System should handle API and calculation errors gracefully

## Related Flows
- Location Recommendation and Assignment (UXF-LOC-001)
- Daily Calendar Archiving (UXF-CAL-001)
- Error Notification Flow (UXF-NOT-001)

## Notes
- All travel calculations and appointment additions are logged for audit and compliance
- Future: Support for multi-user and admin troubleshooting

## Change Tracking

This section records the history of changes made to this document. Add a new row for each significant update.

| Version | Date       | Author      | Description of Changes         |
|---------|------------|-------------|-------------------------------|
| 1.0     | 2024-06-11 | [Your Name] | Initial version               |

</rewritten_file> 