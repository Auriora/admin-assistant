---
title: "Test Case: User Notification of Issues"
id: "CASE-NOT-001"
type: [ testing, test-case ]
status: [ draft ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [testing, notification, functional]
links:
  tooling: []
---

# Test Case: User Notification of Issues

- **Owner**: Auriora Team
- **Status**: Draft
- **Created Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Audience**: [QA Team, Developers]
- **Related Requirements**: FR-NOT-001, NFR-REL-001

## 1. Purpose

Verify that the system reliably detects missing or conflicting data and notifies the user via their configured notification method (email or in-app). This test case ensures that users are promptly informed of critical issues requiring their attention.

## 2. Preconditions

-   The user is authenticated.
-   The system is configured to detect specific issues (e.g., missing location for an appointment, overlapping appointments).
-   The user's notification preferences (email, in-app) are configured.

## 3. Test Data

-   An appointment intentionally created with a missing location.
-   Two or more appointments created to overlap in time.

## 4. Test Steps

| Step # | Description                                       | Expected Result                                                              |
|--------|---------------------------------------------------|------------------------------------------------------------------------------|
| 1      | Trigger a scenario where the system detects missing/conflicting data (e.g., attempt to archive an appointment with a missing location, or create overlapping appointments). | The system detects the issue and initiates a notification process.           |
| 2      | Observe the user's configured notification channel (email inbox or in-app notifications). | The user receives a notification containing relevant details about the issue. |
| 3      | Verify the content of the notification.           | The notification accurately describes the issue and suggests next steps (if applicable). |

## 5. Post-conditions

-   The user is aware of the detected issue.
-   The system has logged the notification event.

## 6. Special Requirements

-   The test should be executed for both email and in-app notification configurations.
-   The notification content should be clear, concise, and actionable.

## 7. Dependencies

-   The Notification Service must be operational.
-   The Calendar Archiving or Appointment Management features must be able to trigger issue detection.

## 8. Notes

-   Consider testing different types of issues that trigger notifications.
-   Verify that notifications are dismissible or markable as read in the UI.

# References

-   [HLD: User Notification of Issues](../../2-architecture/HLD-NOT-001-User-Notification-of-Issues.md)
