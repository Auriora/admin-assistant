# Test Case Template

## Test Case Information
- **Test Case ID**: TC-CAL-001
- **Test Case Name**: Archive Daily Appointments (Automated)
- **Created By**: [Your Name]
- **Creation Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Related Requirements**: FR-CAL-001, FR-CAL-003, FR-CAL-004, NFR-REL-001
- **Priority**: High

## Test Objective
Verify that the system automatically archives all appointments from the main calendar to the archive calendar at the end of the day, ensuring all appointments are copied, archived entries are immutable, and user is notified of any errors.

## Preconditions
- User is authenticated.
- Main and archive calendars exist.
- There are appointments in the main calendar for the day.

## Test Data
- Main calendar with 3 appointments (varied status, including recurring).

## Test Steps
| Step # | Description | Expected Result     |
|--------|-------------|---------------------|
| 1      | Wait for end-of-day trigger      | System initiates archiving process |
| 2      | System copies all appointments   | All appointments appear in archive calendar |
| 3      | Attempt to edit archived entry   | Edit is allowed only by user, not system |
| 4      | Simulate archiving failure       | User receives notification (email and UI) |

## Post-conditions
- All appointments are archived and immutable.
- User is notified of any errors.

## Special Requirements
- Must handle recurring appointments.
- Must not miss any appointments.

## Dependencies
- Calendar service, notification service.

## Notes
- Test both successful and failure scenarios.

## Change Tracking

| Version | Date | Author | Description of Changes |
|---------|------|--------|------------------------|
| 1.0 | 2024-06-11 | [Your Name] | Initial version | 