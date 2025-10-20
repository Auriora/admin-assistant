# UX Flow Diagram and Description Template

## Flow Information
- **Flow ID**: UXF-OVL-001
- **Flow Name**: Manual Overlap Resolution and Persistent Chat/AI
- **Created By**: [AI Assistant]
- **Creation Date**: 2024-06-11
- **Related Requirements**: FR-OVL-001 to FR-OVL-007, FR-AI-001 to FR-AI-006
- **Priority**: High

## Flow Objective
Enable users to manually resolve overlapping appointments, with options to keep, edit, merge, or create new appointments, and to interact with a persistent chat/AI interface for suggestions and support. All actions and AI suggestions are logged for audit and compliance.

## User Personas
- Professional user (primary, single-user scenario)
- (Future) Admin or support user (for troubleshooting)

## Preconditions
- User is authenticated via Microsoft account
- Overlapping appointments have been detected and logged in ActionLog, grouped in a virtual calendar

## Flow Diagram (Textual)
- User navigates to the Overlap Resolution page
- System displays unresolved overlap groups (virtual calendars)
- User selects a group to resolve
- System presents all overlapping appointments, options, and AI suggestions
- User interacts with persistent chat/AI for advice or suggestions
- User chooses to keep, edit, merge, or create new appointment(s)
- System applies resolution, updates ActionLog, and saves chat history
- User can return later to continue or review the chat/resolution

## Detailed Flow Description

| Step # | Actor        | Action                                      | System Response                                      | UI Elements                | Notes                                  |
|--------|--------------|---------------------------------------------|------------------------------------------------------|----------------------------|----------------------------------------|
| 1      | User         | Navigates to Overlap Resolution page        | Loads unresolved overlap groups (virtual calendars)   | Overlap list, status       |                                        |
| 2      | User         | Selects an overlap group                    | Displays all overlapping appointments, options, AI chat| Appointment list, chat     |                                        |
| 3      | System/AI    | Presents AI-powered suggestions             | Shows recommended resolution, merged subject, etc.    | AI suggestion, chat        |                                        |
| 4      | User         | Interacts with chat/AI for advice           | Chat history is updated and stored                    | Chat window                | Supports async/sync workflows          |
| 5      | User         | Chooses to keep, edit, merge, or create     | System applies changes, updates ActionLog, closes group| Resolution options         |                                        |
| 6      | User         | Returns later to continue or review         | Loads previous chat and resolution state              | Chat, appointment list     |                                        |

## Error Scenarios

| Error Scenario         | Trigger                                 | System Response                                 | User Recovery Action                |
|-----------------------|-----------------------------------------|------------------------------------------------|-------------------------------------|
| AI Unavailable        | OpenAI API error/downtime                | Notifies user, allows retry or manual action    | Retry or proceed manually           |
| Save Failure          | Backend/database error                   | Shows error, allows retry                       | Retry save                          |
| Auth Expired          | User session/token expired               | Prompts user to re-authenticate                 | Log in again                        |

## UI Components
- Overlap group list with status (unresolved/resolved)
- Appointment list for each group
- Persistent chat/AI window (with history)
- Resolution options (keep, edit, merge, create new)
- Success/Error notification banners or modals

## Accessibility Considerations
- All controls accessible via keyboard and screen readers
- Sufficient color contrast for appointments, chat, and error messages
- Clear, actionable error messages and prompts

## Performance Expectations
- Loading and saving should complete within a few seconds
- Chat/AI suggestions should appear promptly
- UI should remain responsive during backend operations

## Related Flows
- Daily Calendar Archiving (UXF-CAL-001)
- AI Integration and Recommendations (UXF-AI-001)
- Audit Log and Export (UXF-AUD-001)

## Notes
- All overlap resolution actions and AI suggestions are logged for audit and compliance
- Chat history is persistent and available for future reference
- Future: Support for multi-user and admin troubleshooting 