---
title: "Test Case: Appointment Categorization (AI-assisted and Manual Override)"
id: "CASE-CAT-001"
type: [ testing, test-case ]
status: [ draft ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [testing, categorization, functional, ai]
links:
  tooling: []
---

# Test Case: Appointment Categorization (AI-assisted and Manual Override)

- **Owner**: Auriora Team
- **Status**: Draft
- **Created Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Audience**: [QA Team, Developers]
- **Related Requirements**: FR-CAT-001, FR-CAT-002, FR-BIL-002, FR-BIL-005, NFR-USE-001

## 1. Purpose

Verify that the system accurately recommends billing categories for appointments using AI, allows the user to override these recommendations, and appropriately handles ambiguous or missing categories. This test case ensures accurate billing and user control over categorization.

## 2. Preconditions

-   The user is authenticated.
-   Appointments exist in the user's calendar or archive.
-   The system has a functional categorization service and, if applicable, integration with the OpenAI API.

## 3. Test Data

-   **Scenario 1 (AI Recommendation)**: An appointment with a clear subject, attendees, and location that should lead to a confident AI recommendation (e.g., "Meeting with Client X at Location Y").
-   **Scenario 2 (Manual Override)**: An appointment where the AI provides a recommendation, but the user wishes to select a different category.
-   **Scenario 3 (Ambiguous/Missing Category)**: An appointment with insufficient information for AI to confidently categorize, or an appointment explicitly lacking a category.

## 4. Test Steps

| Step # | Description                                       | Expected Result                                                              |
|--------|---------------------------------------------------|------------------------------------------------------------------------------|
| 1      | View an appointment from Scenario 1.              | The system suggests a billing category using AI and predefined rules.        |
| 2      | For the appointment in Scenario 2, observe the AI recommendation and then manually select a different category. | The user's manual selection is saved and overrides the AI recommendation.    |
| 3      | View an appointment from Scenario 3.              | The system prompts the user for input to assign a category, as AI/rules could not confidently determine one. |
| 4      | Verify that the assigned categories are used in downstream processes (e.g., timesheet generation). | The timesheet accurately reflects the categories assigned (either by AI or manual override). |

## 5. Post-conditions

-   Each appointment has a correct billing category assigned.
-   User overrides are respected.
-   Ambiguous cases are handled by user input.

## 6. Special Requirements

-   AI recommendations should leverage appointment subject, attendees, and location.
-   The UI must clearly present AI recommendations and allow for easy manual override.

## 7. Dependencies

-   Categorization Service.
-   OpenAI API integration (for AI recommendations).
-   Timesheet Generation Service (for verification).

## 8. Notes

-   Ensure that the system logs both AI recommendations and user overrides for audit purposes.
-   Test the responsiveness of AI recommendations.

# References

-   [HLD: Appointment Categorization](../2-architecture/HLD-CAT-001-Appointment-Categorization.md)
-   [HLD: AI Integration and Recommendations](../2-architecture/HLD-AI-001-AI-Integration-and-Recommendations.md)
