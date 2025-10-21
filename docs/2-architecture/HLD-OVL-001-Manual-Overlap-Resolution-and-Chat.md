---
title: "HLD: Manual Overlap Resolution and Chat"
id: "HLD-OVL-001"
type: [ hld, architecture, workflow ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [hld, overlap, chat, ai, ux]
links:
  tooling: []
---

# High-Level Design: Manual Overlap Resolution and Chat

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Audience**: [Developers, UX Designers, Product Managers]

## 1. Purpose

This document describes the high-level design for the manual overlap resolution feature. The objective is to enable users to resolve overlapping appointments with the assistance of a persistent chat/AI interface. Users can keep, edit, merge, or create new appointments, and all actions and AI suggestions are logged for a complete audit trail.

## 2. Context

- **User Personas**: The primary user is a professional whose calendar may contain conflicting or overlapping events that need manual intervention.
- **Preconditions**:
  - The user must be authenticated.
  - Overlapping appointments must have been previously detected and logged in the `ActionLog`, grouped within a virtual calendar.

## 3. Details

### 3.1. Flow Diagram (Textual)

1.  User navigates to the Overlap Resolution page.
2.  The system displays a list of unresolved overlap groups (virtual calendars).
3.  User selects a group to resolve.
4.  The system presents all overlapping appointments, resolution options, and AI-powered suggestions in a chat interface.
5.  User interacts with the persistent chat/AI for advice or to generate suggestions.
6.  User chooses a resolution (keep, edit, merge, or create new).
7.  The system applies the resolution, updates the `ActionLog`, and saves the chat history.
8.  The user can return at any time to review the chat and resolution history.

### 3.2. Step-by-Step Flow

| Step # | Actor     | Action                                      | System Response                                      |
|--------|-----------|---------------------------------------------|------------------------------------------------------|
| 1      | User      | Navigates to the Overlap Resolution page.   | Loads the list of unresolved overlap groups.         |
| 2      | User      | Selects an overlap group to resolve.        | Displays all associated appointments and the chat UI.|
| 3      | System/AI | Presents AI-powered suggestions.            | Shows a recommended resolution in the chat.          |
| 4      | User      | Interacts with the chat/AI for advice.      | The chat history is updated and stored.              |
| 5      | User      | Chooses a resolution option.                | The system applies the changes and closes the task.  |

### 3.3. Error Scenarios

| Scenario       | Trigger                                     | System Response                                 |
|----------------|---------------------------------------------|-------------------------------------------------|
| AI Unavailable | The OpenAI API is down or returns an error. | Notifies the user and allows a retry or manual action. |
| Save Failure   | A backend or database error occurs.         | An error message is shown, allowing a retry.    |
| Auth Expired   | The user's session or token has expired.    | Prompts the user to re-authenticate.            |

### 3.4. Design Considerations

- **UI Components**: The UI will feature a list of overlap groups, a detailed view for each group's appointments, a persistent chat window with history, and clear resolution option buttons.
- **Persistence**: Chat history is persistent, allowing users to leave and return to a resolution task without losing context.
- **Auditability**: All user actions and AI suggestions are logged for compliance and troubleshooting.

# References

- **Related Requirements**: FR-OVL-001 to FR-OVL-007, FR-AI-001 to FR-AI-006
- **Related Flows**:
  - [Daily Calendar Archiving](HLD-CAL-001-Daily-Calendar-Archiving.md)
  - [AI Integration and Recommendations](HLD-AI-001-AI-Integration-and-Recommendations.md)
  - [Audit Log and Export](HLD-AUD-001-Audit-Log-and-Export.md)
