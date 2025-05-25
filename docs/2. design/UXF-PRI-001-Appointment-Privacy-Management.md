# UX Flow Diagram and Description Template

## Flow Information
- **Flow ID**: UXF-PRI-001
- **Flow Name**: Appointment Privacy Management
- **Created By**: [Your Name]
- **Creation Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Related Requirements**: FR-PRI-001, FR-PRI-002, FR-PRI-003; UC-PRI-001
- **Priority**: High

## Flow Objective
Automatically mark personal and travel appointments as private, exclude private appointments from timesheet exports, and maintain a log of privacy changes with rollback capability. This flow ensures user privacy and compliance with data protection requirements.

## User Personas
- Professional user (primary, single-user scenario)
- (Future) Admin or support user (for troubleshooting)

## Preconditions
- User is authenticated via Microsoft account
- Appointments exist in the calendar/archive
- User has granted necessary permissions to the application

## Flow Diagram
```
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

## Detailed Flow Description

### Entry Points
- User views or edits an appointment or timesheet (e.g., on calendar, appointment details, or export page).
- System detects personal or travel appointments and marks them as private.

### Step-by-Step Flow

| Step # | Actor        | Action                                      | System Response                                      | UI Elements                | Notes                                  |
|--------|--------------|---------------------------------------------|------------------------------------------------------|----------------------------|----------------------------------------|
| 1      | User/System  | Appointment is personal/travel              | System marks as private                              | Privacy indicator           | Can be triggered on save or export     |
| 2      | Backend      | Records privacy change in log               | Updates privacy log                                  | N/A                        |                                        |
| 3      | Backend      | Excludes private appointments from export   | Timesheet/export omits private appointments          | N/A                        |                                        |
| 4      | User         | Reviews privacy status, can roll back       | System provides rollback option                      | Privacy log, Rollback button|                                        |
| 5      | Backend      | Reverts privacy status (if requested)       | Updates appointment and log                          | N/A                        |                                        |
| 6      | Backend      | Confirms update to UI                       | Shows success or error message                       | Success/Error notification  |                                        |

### Exit Points
- Appointment is marked as private or reverted to public.
- Private appointments are excluded from exports.
- User is notified of any errors and can resolve them.
- System logs all actions for audit purposes.

### Error Scenarios

| Error Scenario         | Trigger                                 | System Response                                 | User Recovery Action                |
|-----------------------|-----------------------------------------|------------------------------------------------|-------------------------------------|
| Log Failure           | Privacy log/database error               | Shows error, allows retry                       | Retry action                        |
| Rollback Failure      | Error reverting privacy status           | Shows error, allows retry                       | Retry rollback                      |
| Save Failure          | Backend/database error                   | Shows error, allows retry                       | Retry save                          |
| Auth Expired          | User session/token expired               | Prompts user to re-authenticate                 | Log in again                        |

## UI Components
- Appointment details page/modal with privacy indicator
- Privacy log/history panel
- Rollback button (for privacy changes)
- Success/Error notification banners or modals

## Accessibility Considerations
- All controls accessible via keyboard and screen readers
- Sufficient color contrast for privacy indicators and error messages
- Clear, actionable error messages and prompts

## Performance Expectations
- Privacy marking and rollback should complete within a second
- UI should remain responsive during backend operations
- System should handle log and save errors gracefully

## Related Flows
- Timesheet Generation and Export (UXF-BIL-001)
- Appointment Categorization (UXF-CAT-001)
- Error Notification Flow (UXF-NOT-001)

## Notes
- All privacy actions and changes are logged for audit and compliance
- Future: Support for multi-user and admin troubleshooting

## Change Tracking

This section records the history of changes made to this document. Add a new row for each significant update.

| Version | Date       | Author      | Description of Changes         |
|---------|------------|-------------|-------------------------------|
| 1.0     | 2024-06-11 | [Your Name] | Initial version               | 