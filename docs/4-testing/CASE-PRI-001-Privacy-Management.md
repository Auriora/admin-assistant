---
title: "Test Case: Privacy Management for Appointments"
id: "CASE-PRI-001"
type: [ testing, test-case ]
status: [ draft ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [testing, privacy, functional, security]
links:
  tooling: []
---

# Test Case: Privacy Management for Appointments

- **Owner**: Auriora Team
- **Status**: Draft
- **Created Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Audience**: [QA Team, Developers]
- **Related Requirements**: FR-PRI-001, FR-PRI-002, FR-PRI-003, NFR-SEC-001

## 1. Purpose

Verify that the system automatically marks personal and travel appointments as private, excludes private appointments from timesheet exports, and maintains a log of privacy changes with rollback capability. This test case ensures user privacy and compliance with data protection requirements.

## 2. Preconditions

-   The user is authenticated.
-   Appointments exist in the user's calendar.
-   The system is configured to identify personal and travel appointments.

## 3. Test Data

-   A personal appointment (e.g., marked with a specific keyword or category).
-   A travel appointment (e.g., created by the travel automation feature).
-   An existing privacy change in the log that can be rolled back.

## 4. Test Steps

| Step # | Description                                       | Expected Result                                                              |
|--------|---------------------------------------------------|------------------------------------------------------------------------------|
| 1      | Create or modify a personal appointment.          | The system automatically marks the appointment as private.                   |
| 2      | Create or modify a travel appointment.            | The system automatically marks the appointment as private.                   |
| 3      | Generate a timesheet export for a period including private appointments. | Private appointments are excluded from the generated timesheet.              |
| 4      | Navigate to the privacy log/history UI.           | All privacy changes (automatic and manual) are logged and visible.           |
| 5      | Select a privacy change from the log and initiate a rollback. | The appointment's privacy status is reverted to its previous state.          |
| 6      | Verify the updated privacy status of the appointment. | The appointment's privacy status reflects the rollback.                      |

## 5. Post-conditions

-   Personal and travel appointments are correctly marked as private.
-   Private appointments are excluded from timesheet exports.
-   All privacy changes are logged and can be reversed.

## 6. Special Requirements

-   The privacy log must be accessible via the UI and provide a clear rollback mechanism.
-   The system must differentiate between automatic and manual privacy changes in the log.

## 7. Dependencies

-   Privacy/Categorization Service.
-   Export Service.
-   Audit Logging Service.

## 8. Notes

-   Test scenarios should cover both automatic marking of privacy and manual overrides.
-   Verify that the exclusion from timesheets is robust across different export formats.

# References

-   [HLD: Appointment Privacy Management](../2-architecture/HLD-PRI-001-Appointment-Privacy-Management.md)
-   [HLD: Timesheet Generation and Export](../2-architecture/HLD-BIL-001-Timesheet-Generation-and-Export.md)
