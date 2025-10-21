---
title: "SRS Use Cases"
id: "SRS-Use-Cases"
type: [ srs, use-cases ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "2024-12-19"
tags: [srs, use-cases, requirements]
links:
  tooling: []
---

# Use Cases

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: DD-MM-YYYY
- **Last Updated**: 2024-12-19
- **Audience**: [Developers, Testers, Product Managers]

## 1. Purpose

This section describes the key use cases for the Admin Assistant system, focusing on user interactions and expected outcomes. These use cases represent the most important scenarios that the system must support.

## 2. Details

### 2.1 UC-CAL-001 Archive Daily Appointments

| Field                        | Description                                                                                                   |
|------------------------------|---------------------------------------------------------------------------------------------------------------|
| **Use Case ID**              | UC-CAL-001                                                                                                    |
| **Name**                     | Archive Daily Appointments                                                                                    |
| **Primary Actors**           | System (automated), User (manual trigger)                                                                     |
| **Stakeholders & Interests** | **User**: Wants reliable, unalterable record of appointments                                                  |
| **Pre-conditions**           | 1. User is authenticated<br>2. Main and archive calendars exist                                               |
| **Post-conditions**          | **Successful**: All appointments copied to archive calendar<br>**Failure**: User notified of any errors        |
| **Main Flow**                | 1. At end of day, system copies all appointments to archive calendar<br>2. User can manually trigger archive   |
| **Alternative Flows**        | **AF-1**: Archive fails—system notifies user                                                                  |
| **Special Requirements**     | - Must not miss any appointments<br>- Must handle recurring appointments                                      |
| **Related FRs**              | FR-CAL-001, FR-CAL-002, FR-CAL-003                                                                            |
| **Related NFRs**             | NFR-REL-001                                                                                                   |

### 2.2 UC-BIL-001 Generate and Export Timesheet

| Field                        | Description                                                                                                   |
|------------------------------|---------------------------------------------------------------------------------------------------------------|
| **Use Case ID**              | UC-BIL-001                                                                                                    |
| **Name**                     | Generate and Export Timesheet                                                                                  |
| **Primary Actors**           | User                                                                                                          |
| **Stakeholders & Interests** | **User**: Wants accurate, categorized timesheet for billing                                                    |
| **Pre-conditions**           | 1. Archive calendar populated<br>2. User is authenticated                                                      |
| **Post-conditions**          | **Successful**: PDF generated, uploaded to OneDrive and Xero<br>**Failure**: User notified of any errors      |
| **Main Flow**                | 1. User selects date range<br>2. System extracts and categorizes data<br>3. PDF generated and uploaded         |
| **Alternative Flows**        | **AF-1**: User overrides categorization<br>**AF-2**: Export as CSV/Excel                                      |
| **Special Requirements**     | - PDF must match template<br>- Exclude private appointments                                                   |
| **Related FRs**              | FR-BIL-001, FR-BIL-002, FR-BIL-003, FR-BIL-004, FR-PRI-002, FR-EXP-001                                       |
| **Related NFRs**             | NFR-PERF-001, NFR-SEC-001                                                                                     |

### 2.3 UC-LOC-001 Recommend/Assign Location

| Field                        | Description                                                                                                   |
|------------------------------|---------------------------------------------------------------------------------------------------------------|
| **Use Case ID**              | UC-LOC-001                                                                                                    |
| **Name**                     | Recommend/Assign Location                                                                                      |
| **Primary Actors**           | System, User                                                                                                  |
| **Stakeholders & Interests** | **User**: Wants accurate location data for all appointments                                                    |
| **Pre-conditions**           | 1. Appointment missing location<br>2. User is authenticated                                                    |
| **Post-conditions**          | **Successful**: Location assigned<br>**Failure**: User notified of missing location                           |
| **Main Flow**                | 1. System checks for missing locations<br>2. Recommends from list or past data<br>3. User can confirm/add new  |
| **Alternative Flows**        | **AF-1**: Location auto-created from invitation                                                               |
| **Special Requirements**     | - User can configure location list                                                                            |
| **Related FRs**              | FR-LOC-001, FR-LOC-002                                                                                        |
| **Related NFRs**             | NFR-USE-001                                                                                                   |

### 2.4 UC-TRV-001 Add Travel Appointments

| Field                        | Description                                                                                                   |
|------------------------------|---------------------------------------------------------------------------------------------------------------|
| **Use Case ID**              | UC-TRV-001                                                                                                    |
| **Name**                     | Add Travel Appointments                                                                                        |
| **Primary Actors**           | System                                                                                                        |
| **Stakeholders & Interests** | **User**: Wants accurate travel time and appointments                                                          |
| **Pre-conditions**           | 1. Appointments with different locations<br>2. User profile has Home location                                  |
| **Post-conditions**          | **Successful**: Travel appointments added<br>**Failure**: User notified of any errors                         |
| **Main Flow**                | 1. System calculates travel needs<br>2. Adds travel appointments using Google Directions API                   |
| **Alternative Flows**        | **AF-1**: Multi-day trip exception handled                                                                    |
| **Special Requirements**     | - Use traffic predictions                                                                                     |
| **Related FRs**              | FR-TRV-001, FR-TRV-002, FR-TRV-003                                                                            |
| **Related NFRs**             | NFR-PERF-001, NFR-REL-001                                                                                     |

### 2.5 UC-CAT-001 Categorize Appointments

| Field                        | Description                                                                                                   |
|------------------------------|---------------------------------------------------------------------------------------------------------------|
| **Use Case ID**              | UC-CAT-001                                                                                                    |
| **Name**                     | Categorize Appointments                                                                                        |
| **Primary Actors**           | System, User                                                                                                  |
| **Stakeholders & Interests** | **User**: Wants correct billing categorization                                                                 |
| **Pre-conditions**           | 1. Appointment exists<br>2. User is authenticated                                                             |
| **Post-conditions**          | **Successful**: Category assigned<br>**Failure**: User notified                                               |
| **Main Flow**                | 1. System recommends category<br>2. User can override                                                         |
| **Alternative Flows**        | **AF-1**: AI recommendation used                                                                              |
| **Special Requirements**     | - Use subject, attendees, location                                                                            |
| **Related FRs**              | FR-CAT-001, FR-CAT-002                                                                                        |
| **Related NFRs**             | NFR-USE-001                                                                                                   |

### 2.6 UC-PRI-001 Mark Appointments as Private

| Field                        | Description                                                                                                   |
|------------------------------|---------------------------------------------------------------------------------------------------------------|
| **Use Case ID**              | UC-PRI-001                                                                                                    |
| **Name**                     | Mark Appointments as Private                                                                                   |
| **Primary Actors**           | System                                                                                                        |
| **Stakeholders & Interests** | **User**: Wants privacy for personal and travel appointments                                                   |
| **Pre-conditions**           | 1. Appointment exists<br>2. User is authenticated                                                             |
| **Post-conditions**          | **Successful**: Appointment marked private<br>**Failure**: User notified                                      |
| **Main Flow**                | 1. System marks personal/travel appointments as private                                                       |
| **Alternative Flows**        | **AF-1**: User can review privacy status                                                                      |
| **Special Requirements**     | - Exclude from timesheet exports                                                                              |
| **Related FRs**              | FR-PRI-001, FR-PRI-002                                                                                        |
| **Related NFRs**             | NFR-SEC-001                                                                                                   |

### 2.7 UC-UI-001 Manage Rules and Guidelines

| Field                        | Description                                                                                                   |
|------------------------------|---------------------------------------------------------------------------------------------------------------|
| **Use Case ID**              | UC-UI-001                                                                                                     |
| **Name**                     | Manage Rules and Guidelines                                                                                   |
| **Primary Actors**           | User                                                                                                          |
| **Stakeholders & Interests** | **User**: Wants to customize automation                                                                       |
| **Pre-conditions**           | 1. User is authenticated                                                                                      |
| **Post-conditions**          | **Successful**: Rules updated<br>**Failure**: User notified                                                   |
| **Main Flow**                | 1. User adds/edits rules via UI<br>2. System applies rules for recommendations                               |
| **Alternative Flows**        | **AF-1**: System uses OpenAI for complex recommendations                                                      |
| **Special Requirements**     | - Rules are user-specific                                                                                     |
| **Related FRs**              | FR-RUL-001, FR-RUL-002, FR-RUL-003                                                                            |
| **Related NFRs**             | NFR-MNT-001                                                                                                   |

### 2.8 UC-NOT-001 Notify User of Issues

| Field                        | Description                                                                                                   |
|------------------------------|---------------------------------------------------------------------------------------------------------------|
| **Use Case ID**              | UC-NOT-001                                                                                                    |
| **Name**                     | Notify User of Issues                                                                                          |
| **Primary Actors**           | System                                                                                                        |
| **Stakeholders & Interests** | **User**: Wants to be aware of missing/conflicting data                                                       |
| **Pre-conditions**           | 1. System detects issue                                                                                       |
| **Post-conditions**          | **Successful**: User notified<br>**Failure**: Issue logged                                                    |
| **Main Flow**                | 1. System detects missing/conflicting data<br>2. Notifies user                                                |
| **Alternative Flows**        | **AF-1**: Notification via email or in-app                                                                    |
| **Special Requirements**     | - Notification method configurable                                                                            |
| **Related FRs**              | FR-NOT-001                                                                                                    |
| **Related NFRs**             | NFR-REL-001                                                                                                   |

### 2.9 UC-NOT-002 Advanced Notification Handling

| Field                        | Description                                                                                                   |
|------------------------------|---------------------------------------------------------------------------------------------------------------|
| **Use Case ID**              | UC-NOT-002                                                                                                    |
| **Name**                     | Advanced Notification Handling                                                                                |
| **Primary Actors**           | System, User                                                                                                  |
| **Stakeholders & Interests** | **User**: Wants timely, actionable, and non-intrusive notifications; control over notification preferences     |
| **Pre-conditions**           | 1. User is authenticated<br>2. System detects an event requiring notification                                 |
| **Post-conditions**          | **Successful**: User receives notification via preferred channel(s), can track progress, and mark as read      |
| **Main Flow**                | 1. System detects event<br>2. System creates/updates notification (by transaction_id)<br>3. Notification delivered via toast/email/both<br>4. User views notification, sees progress/state<br>5. User can mark as read or take action<br>6. System logs all events and responses |
| **Alternative Flows**        | **AF-1**: User changes notification preferences<br>**AF-2**: Notification delivery fails, fallback to alternate channel |
| **Special Requirements**     | - Progress, state, and channel must be shown in UI<br>- User can configure notification preferences           |
| **Related FRs**              | FR-NOT-002, FR-NOT-003, FR-NOT-004, FR-NOT-005, FR-NOT-006, FR-NOT-007                                       |
| **Related NFRs**             | NFR-REL-001, NFR-USE-001, NFR-AUD-001                                                                         |

### 2.10 UC-OVL-001 Manual Overlap Resolution and AI Chat

| Field                        | Description                                                                                                   |
|------------------------------|---------------------------------------------------------------------------------------------------------------|
| **Use Case ID**              | UC-OVL-001                                                                                                    |
| **Name**                     | Manual Overlap Resolution and AI Chat                                                                         |
| **Primary Actors**           | User                                                                                                          |
| **Stakeholders & Interests** | **User**: Wants to resolve overlapping appointments accurately and efficiently, with AI assistance             |
| **Pre-conditions**           | 1. Overlapping appointments detected and logged in ActionLog<br>2. User is authenticated                      |
| **Post-conditions**          | **Successful**: Overlaps resolved as per user decision<br>**Failure**: Overlaps remain unresolved             |
| **Main Flow**                | 1. User views unresolved overlaps (grouped in a virtual calendar)<br>2. System presents options and AI suggestions<br>3. User chooses to keep, edit, merge, or create new appointment(s)<br>4. User can interact with AI chat for suggestions<br>5. System applies resolution and updates ActionLog<br>6. Chat history is saved for future reference |
| **Alternative Flows**        | **AF-1**: User returns later to continue resolution<br>**AF-2**: User ignores AI suggestions and resolves manually |
| **Special Requirements**     | - Persistent chat interface<br>- AI-powered suggestions<br>- All actions logged for audit                     |
| **Related FRs**              | FR-OVL-001, FR-OVL-002, FR-OVL-003, FR-OVL-004, FR-OVL-005, FR-OVL-006, FR-OVL-007                           |
| **Related NFRs**             | NFR-USE-001, NFR-AUD-001                                                                                      |

# References

- Link to additional resources, specs, or tickets
