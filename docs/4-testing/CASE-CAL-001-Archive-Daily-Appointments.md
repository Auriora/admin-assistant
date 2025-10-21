---
title: "Test Case: Calendar Archive Daily Appointments"
id: "CASE-CAL-001"
type: [ testing, test-case ]
status: [ draft ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [testing, archiving, functional, integration]
links:
  tooling: []
---

# Test Case: Calendar Archive Daily Appointments

- **Owner**: Auriora Team
- **Status**: Draft
- **Created Date**: 2024-12-19
- **Last Updated**: 2024-12-19
- **Audience**: [QA Team, Developers]
- **Related Requirements**: UXF-CAL-001 (now HLD-CAL-001), Calendar Archiving Workflow (now WF-CAL-001)

## 1. Purpose

Verify that the `CalendarArchiveOrchestrator` successfully archives appointments from the source calendar to the archive calendar. This includes validating overlap detection, category processing, privacy automation, and meeting modification handling, ensuring data integrity and compliance.

## 2. Preconditions

-   The user is authenticated with Microsoft Graph.
-   Source and archive calendars are configured and accessible.
-   Test appointments exist in the source calendar, covering various scenarios (e.g., normal, overlapping, private).
-   A database session is available.
-   A mock MS Graph client is configured.

## 3. Test Data

```python
# Sample test appointments from conftest.py
sample_appointments = [
    {
        'subject': 'Team Meeting',
        'start_time': datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
        'end_time': datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
        'calendar_id': 'source-calendar',
        'location': 'Conference Room A'
    },
    {
        'subject': 'Client Call - Acme Corp - Consulting',
        'start_time': datetime(2025, 6, 1, 14, 0, tzinfo=UTC),
        'end_time': datetime(2025, 6, 1, 15, 0, tzinfo=UTC),
        'calendar_id': 'source-calendar',
        'location': 'Online'
    }
]
```

## 4. Test Steps

-   **Setup Mock Repositories**: Configure MS Graph appointment repositories with test data.
-   **Load Test Data**: Prepare sample appointments with various scenarios (e.g., normal, overlapping, private, meeting modifications).
-   **Execute Archiving**: Call `orchestrator.archive_user_appointments()` with the prepared data.
-   **Verify Results**: Check for successful archiving, correct category processing, accurate overlap detection, and proper privacy automation.
-   **Validate Audit Logs**: Ensure that a complete and correct audit trail is created for all operations.
-   **Check Error Handling**: Verify graceful error handling and reporting for any simulated failures.

## 5. Expected Results

-   **Archiving Success**: All non-overlapping appointments are successfully copied to the archive calendar.
-   **Category Processing**: Customer/billing information is parsed and applied correctly.
-   **Overlap Detection**: Overlapping appointments are accurately identified and logged for user resolution.
-   **Privacy Automation**: Private appointments are flagged appropriately and handled as per privacy rules.
-   **Audit Logging**: A complete audit trail with detailed operation metadata is created.
-   **Error Handling**: Any failures are handled gracefully, with detailed logging and appropriate user notifications.

## 6. Actual Test Coverage

-   ✅ End-to-end archiving workflow.
-   ✅ MS Graph API integration (mocked).
-   ✅ Category processing integration.
-   ✅ Overlap resolution integration (detection and logging).
-   ✅ Privacy automation integration.
-   ✅ Meeting modification integration.
-   ✅ Audit logging verification.
-   ✅ Error scenario handling.

## 7. Dependencies

-   `CalendarArchiveOrchestrator`
-   MS Graph API (mocked)
-   Database session
-   Test fixtures from `conftest.py`

## 8. Notes

-   This integration test uses comprehensive mocking for the MS Graph API to ensure isolation and speed.
-   It covers both success and failure scenarios to validate robustness.
-   It verifies the integration of all workflow processing services.
-   Ensures data integrity and audit compliance throughout the archiving process.

# References

-   [HLD: Daily Calendar Archiving](../2-architecture/HLD-CAL-001-Daily-Calendar-Archiving.md)
-   [WF: Outlook Calendar Management Workflow](../1-requirements/WF-Outlook-Calendar-Management.md)
-   [IMPL: Testing and Observability](../3-implementation/IMPL-Testing-And-Observability.md)
