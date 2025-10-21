# Test Case Template

## Test Case Information
- **Test Case ID**: TC-BIL-001
- **Test Case Name**: Generate and Export Timesheet (PDF)
- **Created By**: [Your Name]
- **Creation Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Related Requirements**: FR-BIL-001, FR-BIL-003, FR-BIL-004, FR-PRI-002, FR-EXP-001, NFR-PERF-001
- **Priority**: High

## Test Objective
Verify that the user can generate a timesheet PDF from archived appointments, and that the PDF is uploaded to OneDrive and Xero, excluding private appointments.

## Preconditions
- Archive calendar is populated.
- User is authenticated.
- OneDrive and Xero integrations are configured.

## Test Data
- Archive calendar with 5 appointments (some private, some billable).

## Test Steps
| Step # | Description | Expected Result     |
|--------|-------------|---------------------|
| 1      | User selects date range and requests timesheet | System extracts relevant appointments |
| 2      | System generates PDF | PDF matches template, excludes private appointments |
| 3      | System uploads PDF to OneDrive and Xero | Files appear in both services |
| 4      | Simulate API failure | System retries and notifies user if failure persists |

## Post-conditions
- Timesheet is generated and uploaded.
- User is notified of any errors.

## Special Requirements
- PDF must match template.
- Exclude private appointments.

## Dependencies
- Archive calendar, OneDrive/Xero APIs.

## Notes
- Test both successful and failure scenarios.

## Change Tracking

| Version | Date | Author | Description of Changes |
|---------|------|--------|------------------------|
| 1.0 | 2024-06-11 | [Your Name] | Initial version | 