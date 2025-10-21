---
title: "Test Case: Generate and Export Timesheet (PDF)"
id: "CASE-BIL-001"
type: [ testing, test-case ]
status: [ draft ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [testing, timesheet, functional, export]
links:
  tooling: []
---

# Test Case: Generate and Export Timesheet (PDF)

- **Owner**: Auriora Team
- **Status**: Draft
- **Created Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Audience**: [QA Team, Developers]
- **Related Requirements**: FR-BIL-001, FR-BIL-003, FR-BIL-004, FR-PRI-002, FR-EXP-001, NFR-PERF-001

## 1. Purpose

Verify that the user can generate a timesheet PDF from archived appointments, and that the PDF is uploaded to OneDrive and Xero, while correctly excluding private appointments. This test case ensures accurate billing, compliance with privacy rules, and reliable integration with external services.

## 2. Preconditions

-   The archive calendar is populated with a mix of private and billable appointments.
-   The user is authenticated.
-   OneDrive and Xero integrations are configured and active.
-   A timesheet PDF template is available (or the system's default will be used).

## 3. Test Data

-   An archive calendar containing:
    -   3-5 billable appointments for a specific client.
    -   1-2 private appointments within the same date range.
    -   1-2 non-billable appointments.
-   A configured OneDrive destination folder.
-   A configured Xero connection.

## 4. Test Steps

| Step # | Description                                       | Expected Result                                                              |
|--------|---------------------------------------------------|------------------------------------------------------------------------------|
| 1      | User selects a date range that includes the test appointments and requests timesheet generation via the UI. | The system extracts relevant appointments from the archive calendar.         |
| 2      | The system generates the timesheet PDF.           | The generated PDF matches the specified template and correctly excludes all private appointments. |
| 3      | The system attempts to upload the generated PDF to OneDrive and Xero. | The PDF file appears in the configured OneDrive folder and is linked/uploaded to Xero. |
| 4      | Simulate an API failure during the upload process (e.g., for OneDrive or Xero). | The system retries the upload (if configured) and notifies the user if the failure persists. |
| 5      | Verify the content of the generated PDF.          | The PDF accurately reflects billable and non-billable time, and private entries are absent. |

## 5. Post-conditions

-   A timesheet PDF is successfully generated and, if no errors occurred, uploaded to OneDrive and Xero.
-   The user is notified of any errors during the generation or upload process.
-   All timesheet generation and upload actions are logged for audit purposes.

## 6. Special Requirements

-   The generated PDF must strictly adhere to the specified template design.
-   Private appointments must be completely excluded from the timesheet export.

## 7. Dependencies

-   Archive Calendar Service.
-   OneDrive API Integration.
-   Xero API Integration.
-   PDF Generation Service.
-   Notification Service.

## 8. Notes

-   Test both successful generation/upload and various failure scenarios (e.g., API downtime, template issues).
-   Verify that the timesheet accurately reflects categorization and time calculations.

# References

-   [HLD: Timesheet Generation and Export](../2-architecture/HLD-BIL-001-Timesheet-Generation-and-Export.md)
-   [HLD: Appointment Privacy Management](../2-architecture/HLD-PRI-001-Appointment-Privacy-Management.md)
-   [HLD: User Notification of Issues](../2-architecture/HLD-NOT-001-User-Notification-of-Issues.md)
