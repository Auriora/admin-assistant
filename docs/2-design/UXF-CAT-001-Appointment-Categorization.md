# UX Flow Diagram and Description Template

## Flow Information
- **Flow ID**: UXF-CAT-001
- **Flow Name**: Appointment Categorization
- **Created By**: [Your Name]
- **Creation Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Related Requirements**: FR-CAT-001, FR-CAT-002, FR-BIL-002, FR-BIL-005; UC-CAT-001
- **Priority**: High

## Flow Objective
Enable users to categorize appointments for billing and reporting, using AI-powered recommendations based on subject, attendees, and location, with the ability for users to review and override suggested categories. This flow ensures accurate billing and reduces manual effort.

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

## Detailed Flow Description

### Entry Points
- User views or edits an appointment or timesheet (e.g., on calendar, appointment details, or export page).
- System detects uncategorized or ambiguous appointments and prompts user.

### Step-by-Step Flow

| Step # | Actor        | Action                                      | System Response                                      | UI Elements                | Notes                                  |
|--------|--------------|---------------------------------------------|------------------------------------------------------|----------------------------|----------------------------------------|
| 1      | User/System  | Appointment needs categorization            | Prompts user with recommended category               | Prompt/modal, category field| Can be triggered on save or export     |
| 2      | Backend      | Requests category recommendation (AI/rules) | Returns recommended category                         | Recommendation field        |                                        |
| 3      | User         | Accepts or overrides category               | Sends selection to backend                           | Accept/Override buttons     |                                        |
| 4      | Backend      | Saves category to appointment               | Updates appointment in archive/calendar              | N/A                        |                                        |
| 5      | Backend      | Confirms update to UI                       | Shows success or error message                       | Success/Error notification  |                                        |

### Exit Points
- Appointment is updated with a valid category.
- User is notified of any errors and can resolve them.
- System logs all actions for audit purposes.

### Error Scenarios

| Error Scenario         | Trigger                                 | System Response                                 | User Recovery Action                |
|-----------------------|-----------------------------------------|------------------------------------------------|-------------------------------------|
| AI Unavailable        | OpenAI API error/downtime                | Notifies user, allows manual categorization     | User selects category manually      |
| Ambiguous Category    | AI/rules cannot determine category       | Prompts user for input                          | User selects/fixes category         |
| Save Failure          | Backend/database error                   | Shows error, allows retry                       | Retry save                          |
| Auth Expired          | User session/token expired               | Prompts user to re-authenticate                 | Log in again                        |

## UI Components
- Appointment details page/modal with category field
- Category recommendation field
- Accept/Override buttons
- Success/Error notification banners or modals

## Accessibility Considerations
- All controls accessible via keyboard and screen readers
- Sufficient color contrast for prompts and error indicators
- Clear, actionable error messages and prompts

## Performance Expectations
- Category recommendations should appear within a second
- UI should remain responsive during backend operations
- System should handle AI and save errors gracefully

## Related Flows
- Timesheet Generation and Export (UXF-BIL-001)
- Daily Calendar Archiving (UXF-CAL-001)
- Error Notification Flow (UXF-NOT-001)

## Notes
- All categorization actions and changes are logged for audit and compliance
- Future: Support for multi-user and admin troubleshooting

## Change Tracking

This section records the history of changes made to this document. Add a new row for each significant update.

| Version | Date       | Author      | Description of Changes         |
|---------|------------|-------------|-------------------------------|
| 1.0     | 2024-06-11 | [Your Name] | Initial version               | 