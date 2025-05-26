# UX Flow Diagram and Description Template

## Flow Information
- **Flow ID**: UXF-BIL-001
- **Flow Name**: Timesheet Generation and Export
- **Created By**: [Your Name]
- **Creation Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Related Requirements**: FR-BIL-001, FR-BIL-002, FR-BIL-003, FR-BIL-004, FR-BIL-005, FR-BIL-006, FR-BIL-007, FR-BIL-008, FR-EXP-001, FR-EXP-002, FR-PRI-002; UC-BIL-001
- **Priority**: High

## Flow Objective
Allow users to generate, review, and export categorized timesheets for a selected date range, with options to export as PDF, CSV, or Excel, and upload to OneDrive/Xero. The flow ensures accuracy, user control, and compliance with billing and privacy requirements.

## User Personas
- Professional user (primary, single-user scenario)
- (Future) Admin or support user (for troubleshooting)

## Preconditions
- User is authenticated via Microsoft account
- Archive calendar is populated with appointments
- User has granted necessary permissions to the application
- PDF template is available (or default will be used)

## Flow Diagram
```
@startuml
actor User
participant "Web UI" as UI
participant "Backend Service" as BE
database "Archive Calendar" as Archive
participant "OneDrive/Xero API" as OD
participant "PDF/Export Service" as Export

User -> UI: Selects date range, clicks "Generate Timesheet"
UI -> BE: Send timesheet generation request
BE -> Archive: Fetch appointments for range
BE -> Export: Categorize, generate PDF/CSV/Excel
Export --> BE: Return file
BE -> OD: Upload to OneDrive/Xero
OD --> BE: Confirm upload
BE -> UI: Show download link, upload status, errors
@enduml
```

## Detailed Flow Description

### Entry Points
- User logs into the web application and navigates to the Timesheet/Export page.
- User selects a date range and clicks "Generate Timesheet".

### Step-by-Step Flow

| Step # | Actor        | Action                                      | System Response                                      | UI Elements                | Notes                                  |
|--------|--------------|---------------------------------------------|------------------------------------------------------|----------------------------|----------------------------------------|
| 1      | User         | Navigates to Timesheet/Export page          | Loads export options and available date ranges        | Timesheet page, date picker|                                        |
| 2      | User         | Selects date range, clicks "Generate"       | Sends request to backend                             | Date picker, Generate button|                                        |
| 3      | Backend      | Fetches appointments from archive calendar  | Receives appointment data                            | N/A                        |                                        |
| 4      | Backend      | Categorizes appointments (AI/rules/manual)  | Prompts user for ambiguous/missing categories        | Category selector, prompts | User can override categories           |
| 5      | Backend      | Generates PDF/CSV/Excel timesheet           | Returns file or error                                | N/A                        | Uses template or default               |
| 6      | Backend      | Uploads file to OneDrive/Xero               | Confirms upload or shows error                       | Upload status indicator     |                                        |
| 7      | Backend      | Returns download link/status to UI          | Displays download link, upload status, errors        | Download link, status, error|                                        |
| 8      | User         | Downloads file, reviews, or retries         | System logs action, allows retry if error            | Download button, Retry     |                                        |

### Exit Points
- User successfully downloads timesheet and/or confirms upload to OneDrive/Xero.
- User is notified of any errors and can retry or seek help.
- System logs all actions for audit purposes.

### Error Scenarios

| Error Scenario         | Trigger                                 | System Response                                 | User Recovery Action                |
|-----------------------|-----------------------------------------|------------------------------------------------|-------------------------------------|
| API Failure           | OneDrive/Xero API error                 | Shows error, allows retry                       | Retry upload, download locally      |
| PDF Template Missing  | Template not found/corrupt              | Uses default template, notifies user            | Review output, upload manually      |
| Ambiguous Category    | Appointment cannot be auto-categorized  | Prompts user for input                          | User selects/fixes category         |
| Export Failure        | File generation error                   | Shows error, allows retry                       | Retry export                        |
| Auth Expired          | User session/token expired              | Prompts user to re-authenticate                 | Log in again                        |

## UI Components
- Timesheet/Export page with date picker and export options
- Category selector and override prompts
- Generate/Download/Retry buttons
- Upload status indicator
- Success/Error notification banners or modals

## Accessibility Considerations
- All controls accessible via keyboard and screen readers
- Sufficient color contrast for status and error indicators
- Clear, actionable error messages and prompts

## Performance Expectations
- Timesheet generation and export should complete within a few seconds for typical data volumes
- UI should remain responsive during background operations
- System should handle API and export errors gracefully

## Related Flows
- Daily Calendar Archiving (UXF-CAL-001)
- Error Notification Flow (UXF-NOT-001)
- Authentication Flow

## Notes
- All export and upload actions are logged for audit and compliance
- Future: Support for multi-user and admin troubleshooting

## Change Tracking

This section records the history of changes made to this document. Add a new row for each significant update.

| Version | Date       | Author      | Description of Changes         |
|---------|------------|-------------|-------------------------------|
| 1.0     | 2024-06-11 | [Your Name] | Initial version               |

</rewritten_file> 