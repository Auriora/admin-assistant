# 4. Use Cases

This section describes the key use cases for the Admin Assistant system, focusing on user interactions and expected outcomes. These use cases represent the most important scenarios that the system must support.

## 4.1 UC-CAL-001 Archive Daily Appointments

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

## 4.2 UC-BIL-001 Generate and Export Timesheet

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

## 4.3 UC-LOC-001 Recommend/Assign Location

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

## 4.4 UC-TRV-001 Add Travel Appointments

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

## 4.5 UC-CAT-001 Categorize Appointments

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

## 4.6 UC-PRI-001 Mark Appointments as Private

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

## 4.7 UC-UI-001 Manage Rules and Guidelines

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

## 4.8 UC-NOT-001 Notify User of Issues

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
