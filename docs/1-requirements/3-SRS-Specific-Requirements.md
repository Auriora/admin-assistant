---
title: "SRS Specific Requirements"
id: "SRS-Specific-Requirements"
type: [ srs, requirements ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "2024-12-19"
tags: [srs, requirements, functional, non-functional]
links:
  tooling: []
---

# Specific Requirements

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: DD-MM-YYYY
- **Last Updated**: 2024-12-19
- **Audience**: [Developers, Testers, Project Managers]

## 1. Purpose

This section details the specific functional and non-functional requirements of the Admin Assistant system.

## 2. Details

### 2.1 Functional Requirements

#### 2.1.1 Calendar Archiving

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-CAL-001   | Automatically copy all appointments from the main calendar to an archive calendar at end of day. | Must-have   | Prevents loss of historical data.           |
| FR-CAL-002   | Allow user to manually trigger the archiving process.                                            | Should-have | Provides flexibility and control.           |
| FR-CAL-003   | Archive all appointments, regardless of status.                                                  | Must-have   | Ensures complete record.                    |
| FR-CAL-004   | Archived appointments are immutable records; only user can update or delete archived entries.     | Must-have   | Ensures auditability and historical accuracy.|
| FR-CAL-005   | All appointments and archives must be stored in GMT; display adjusts for local time zones.       | Must-have   | Consistent time handling across zones.       |
| FR-CAL-006   | For overlapping appointments, only one is archived; user is prompted to resolve overlaps, with OpenAI recommendations. | Must-have | Prevents double-counting and confusion.     |
| FR-CAL-007   | System must handle Microsoft Graph API rate limits gracefully, with retries and user notification if limits are hit. | Must-have | Reliability and user awareness.             |
| FR-CAL-008   | On partial archiving failure, notify user via email and web UI, with options to retry or resolve. | Must-have   | Ensures no silent data loss.                |
| FR-CAL-009   | Prevent duplicate archiving: if archiving is in progress, new requests wait; only archive from last archived appointment unless overridden. | Must-have | Data integrity and efficiency.              |
| FR-CAL-010   | Manual archive trigger must provide real-time feedback: show 'archive started' and 'archive complete' notifications, updating the same notification as state changes. | Should-have | Improves user experience and clarity. |

#### 2.1.2 Overlap Resolution

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-OVL-001   | The system must detect overlapping appointments and log them for user-driven resolution.         | Must-have   | Prevents data conflicts and double-counting.|
| FR-OVL-002   | Overlap resolution must be handled only by user intervention, not automatically during archiving.| Must-have   | Ensures user control and accuracy.          |
| FR-OVL-003   | The user must be able to choose which appointment(s) to keep, adjust start/end times, merge descriptions, or combine these actions to resolve overlaps. | Must-have | Flexibility in conflict resolution.         |
| FR-OVL-004   | The system must provide AI-powered suggestions (using OpenAI) for resolving overlaps, including merged subject lines and descriptions. | Should-have | Improves efficiency and user experience.    |
| FR-OVL-005   | The system must provide a persistent chat interface for overlap resolution, storing the chat so the user can return at any time. | Should-have | Supports asynchronous and collaborative resolution. |
| FR-OVL-006   | The ActionLog must group/associate all appointments needing resolution for a given overlap, referencing a virtual calendar containing the full details of the overlapping appointments. | Must-have | Ensures all relevant data is available for resolution. |
| FR-OVL-007   | The user must be able to update an existing appointment or create a new one as the result of a resolution. | Must-have | Supports all user workflows.                |

#### 2.1.3 Timesheet Extraction and Billing

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-BIL-001   | Extract timesheet data from the archive calendar.                                                | Must-have   | Enables billing and reporting.              |
| FR-BIL-002   | Categorize appointments as Billable, Non-billable, or Travel.                                   | Must-have   | Supports accurate billing.                  |
| FR-BIL-003   | Generate a PDF timesheet matching the current Excel design, with template support.              | Must-have   | Familiar output, flexible for future needs. |
| FR-BIL-004   | Upload the PDF to OneDrive and connect directly to Xero via API.                                | Must-have   | Streamlines workflow.                       |
| FR-BIL-005   | For ambiguous or missing categories, system uses rules and/or OpenAI, then prompts user for input. | Must-have  | Accurate billing categorization.            |
| FR-BIL-006   | If PDF template is missing/corrupt, use a default template.                                      | Must-have   | Robustness in document generation.          |
| FR-BIL-007   | On OneDrive/Xero API failure, system retries and notifies user.                                  | Must-have   | Reliability and user awareness.             |
| FR-BIL-008   | Billing is always based on the archive; after billing, archive is locked for that period. Option to include missed appointments in next timesheet. | Must-have | Data consistency and auditability.          |

#### 2.1.4 Location Recommendation

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-LOC-001   | Recommend a location for appointments missing one, using a fixed list, then past appointments.   | Must-have   | Ensures location data completeness.         |
| FR-LOC-002   | Allow user to add new locations or auto-create from invitations.                                | Should-have | Improves usability and automation.          |
| FR-LOC-003   | If location is unknown or ambiguous, prompt user for input.                                      | Must-have   | Ensures location accuracy.                  |
| FR-LOC-004   | If user adds a location that conflicts with existing ones, prompt user to resolve.               | Must-have   | Prevents data inconsistency.                |

#### 2.1.5 Travel Assumptions and Calculation

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-TRV-001   | Assume travel starts/ends at Home (user profile), unless all-day event at another location.      | Must-have   | Accurate travel calculation.                |
| FR-TRV-002   | Handle exceptions such as multi-day trips.                                                      | Should-have | Flexibility for real-world scenarios.       |
| FR-TRV-003   | Add separate travel appointments using Google Directions API, considering traffic predictions.   | Must-have   | Accurate travel time for billing.           |
| FR-TRV-004   | System must handle Google Directions API quota/limits and notify user if exceeded.               | Must-have   | Reliability and cost control.               |
| FR-TRV-005   | If route is unreachable, prompt user to check source/destination.                                | Must-have   | User awareness and data accuracy.           |
| FR-TRV-006   | If traffic data is unavailable, use standard travel time.                                        | Must-have   | Fallback for robust travel calculation.     |
| FR-TRV-007   | If back-to-back appointments leave insufficient travel time, alert user via email.               | Must-have   | Prevents scheduling conflicts.              |
| FR-TRV-008   | For all-day/multi-day events, adjust start/end location logic accordingly.                       | Must-have   | Accurate travel planning.                   |

#### 2.1.6 Categorization and Privacy

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-CAT-001   | Recommend billing categories using subject, attendees, and location (AI-assisted).               | Must-have   | Reduces manual work, improves accuracy.     |
| FR-CAT-002   | Allow user to override AI recommendations.                                                       | Must-have   | User control and trust.                     |
| FR-PRI-001   | Automatically mark personal and travel appointments as private.                                  | Must-have   | Protects sensitive information.             |
| FR-PRI-002   | Exclude private appointments from timesheet exports.                                             | Must-have   | Privacy compliance.                         |
| FR-PRI-003   | Maintain a log of all privacy/out-of-office changes; allow user to roll back individual changes via UI. | Must-have | Transparency and error recovery.            |

#### 2.1.7 Out-of-Office Automation

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-OOO-001   | Automatically mark all appointments as Out-of-Office.                                            | Must-have   | Consistent calendar status.                 |

#### 2.1.8 Rules and Guidelines

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-RUL-001   | Maintain a user-specific rules/guidelines base for recommendations.                              | Must-have   | Customizable automation.                    |
| FR-RUL-002   | Allow user to edit/add rules via the UI.                                                         | Must-have   | User empowerment.                           |
| FR-RUL-003   | Use OpenAI API for complex recommendations.                                                      | Should-have | Advanced automation.                        |

#### 2.1.9 User Interface

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-UI-001    | Provide a UI to trigger archives, generate timesheets, and manage rules.                        | Must-have   | Core user interaction.                      |
| FR-UI-002    | Support mobile-friendly exports.                                                                 | Should-have | Usability on mobile devices.                |
| FR-UI-003    | Detailed lists must be paged; calendar views show only relevant data for selected date range.    | Must-have   | Usability with large data sets.             |
| FR-UI-004    | UI must be responsive and handle mobile layouts gracefully.                                      | Must-have   | Mobile usability.                           |

#### 2.1.10 Additional/Recommended

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-AUD-001   | Track all automated changes in an audit log.                                                     | Should-have | Transparency and troubleshooting.           |
| FR-OVR-001   | Detect and process manual changes made in Outlook.                                               | Should-have | Ensures data consistency.                   |
| FR-NOT-001   | Notify user of missing data or conflicts.                                                        | Should-have | Prevents errors and omissions.              |
| FR-MUL-001   | Make provisions for multi-user support.                                                          | Could-have  | Future scalability.                         |
| FR-ROL-001   | Make provisions for role-based access.                                                           | Could-have  | Future scalability.                         |
| FR-EXP-001   | Support CSV/Excel export in addition to PDF.                                                     | Should-have | Flexibility in reporting.                   |
| FR-EXP-002   | Export functions must handle special characters, large data sets, and ensure format compatibility. | Must-have | Robustness in reporting.                    |

#### 2.1.11 AI Integration (OpenAI)

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-AI-001    | Integrate with OpenAI API for AI-powered recommendations and automation.                         | Must-have   | Enables advanced automation and suggestions. |
| FR-AI-002    | Allow user to review and override AI-generated recommendations.                                  | Must-have   | User control and trust.                     |
| FR-AI-003    | User must review and approve timesheet before billing submission.                                | Must-have   | Prevents errors from AI misclassification.  |
| FR-AI-004    | System must minimize and anonymize sensitive data sent to OpenAI.                                | Must-have   | Data privacy and compliance.                |
| FR-AI-005    | If OpenAI is unavailable, system retries later; not time-critical.                               | Must-have   | Robustness to external API downtime.        |
| FR-AI-006    | System must sanitize input to OpenAI to prevent prompt injection attacks.                        | Must-have   | Security.                                   |

#### 2.1.12 Notification System

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-NOT-002   | The system must support notifications via toast (in-app), email, or both, configurable per user and notification class. | Must-have   | User control and awareness.                 |
| FR-NOT-003   | Notifications must support progress updates, including a progress description, percentage complete, and state (e.g., not started, in-progress, success, failed). | Must-have   | Real-time feedback for long-running tasks.  |
| FR-NOT-004   | Each notification must be uniquely updatable by a transaction_id, so that progress/state updates do not create duplicates. | Must-have   | Prevents notification clutter.              |
| FR-NOT-005   | Users must be able to mark notifications as read and configure which notification classes trigger which channels. | Should-have | User experience and control.                |
| FR-NOT-006   | The UI must visually distinguish notification channels (toast/email/both), show progress and state, and allow marking as read. | Must-have   | Clarity and usability.                      |
| FR-NOT-007   | All notification events and user responses must be logged for audit and compliance.              | Must-have   | Traceability and compliance.                |

#### 2.1.13 Command-Line Interface (CLI)

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-CLI-001   | Provide a CLI (`cli/`) for administrative, maintenance, and automation tasks (e.g., archiving, export, user management, diagnostics). | Must-have   | Enables automation, scripting, and headless operation. |
| FR-CLI-002   | CLI must support all major features available in the web UI, with clear help and error messages. | Should-have | Parity and usability for advanced users.     |
| FR-CLI-003   | CLI must be secure, require authentication for sensitive operations, and log all actions.        | Must-have   | Security and auditability.                   |
| FR-CLI-004   | CLI commands must be scriptable and support non-interactive operation.                          | Must-have   | Automation and integration.                  |

### 2.2 Non-Functional Requirements

#### 2.2.1 Security

| ID              | Requirement                                                                                  | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-SEC-001     | Use Microsoft account authentication (OAuth2/OpenID Connect).                               | Must-have   | Secure user authentication.                 |
| NFR-SEC-002     | Only authorized users can access their own data; future-proof for role-based access.         | Must-have   | Data privacy and future scalability.        |
| NFR-SEC-003     | Encrypt all sensitive data at rest and in transit (HTTPS).                                  | Must-have   | Protects user data.                        |
| NFR-SEC-004     | Secure integration with all third-party APIs; never expose secrets in logs or client code.   | Must-have   | Prevents credential leaks.                  |
| NFR-SEC-005     | Secure session management with timeouts and anti-hijacking measures.                        | Must-have   | Prevents unauthorized access.               |
| NFR-SEC-006     | System must handle token expiry and revocation for all integrated APIs.                          | Must-have   | Reliability and security.                   |
| NFR-SEC-007     | System must prevent sensitive data exposure in logs, exports, and API responses.                 | Must-have   | Data privacy.                               |
| NFR-SEC-008     | System must be adaptable to changes in privacy laws or API terms.                                | Must-have   | Legal compliance.                           |

#### 2.2.2 Reliability & Availability

| ID              | Requirement                                                                                  | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-REL-001     | System uptime must be at least 99.5%.                                                       | Must-have   | Ensures availability.                       |
| NFR-REL-002     | Graceful error handling for API failures, network issues, and unexpected errors.             | Must-have   | User experience and data integrity.         |
| NFR-REL-003     | No data loss or corruption during archiving, export, or sync operations.                     | Must-have   | Data integrity.                             |

#### 2.2.3 Performance

| ID              | Requirement                                                                                  | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-PERF-001    | UI actions should complete within a few seconds; background jobs within 5 minutes.           | Must-have   | Responsive user experience.                 |
| NFR-PERF-002    | System must scale to handle increased data volume and future multi-user support.             | Must-have   | Scalability.                                |

#### 2.2.4 Usability

| ID              | Requirement                                                                                  | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-USE-001     | UI must be intuitive, clear, and require minimal training.                                   | Must-have   | User adoption and efficiency.               |
| NFR-USE-002     | UI should meet accessibility standards (e.g., WCAG 2.1 AA).                                  | Must-have   | Accessibility for all users.                |
| NFR-USE-003     | UI must be responsive and usable on mobile devices.                                          | Must-have   | Mobile usability.                           |

#### 2.2.5 Maintainability

| ID              | Requirement                                                                                  | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-MNT-001     | Codebase must be modular, well-documented, and follow project guidelines.                    | Must-have   | Easier maintenance and onboarding.          |
| NFR-MNT-002     | System must be easily extensible for new features and integrations.                          | Must-have   | Future-proofing.                            |
| NFR-MNT-003     | All environment-specific settings must be configurable, not hard-coded.                      | Must-have   | Deployment flexibility.                     |

#### 2.2.6 Auditability

| ID              | Requirement                                                                                  | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-AUD-001     | All critical actions (archiving, exports, API calls, errors) must be securely logged.        | Must-have   | Troubleshooting and compliance.             |
| NFR-AUD-002     | Maintain an audit trail of automated changes for transparency and traceability.              | Must-have   | Accountability.                             |
| NFR-AUD-003     | System must manage audit log size and performance; old logs may be archived or pruned.           | Must-have   | Prevents performance issues.                |

#### 2.2.7 Compliance & Privacy

| ID              | Requirement                                                                                  | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-COM-001     | Comply with relevant data protection laws (e.g., GDPR if applicable).                        | Must-have   | Legal compliance.                           |
| NFR-COM-002     | Obtain user consent for accessing and processing calendar and personal data.                 | Must-have   | User rights and transparency.               |
| NFR-COM-003     | Adhere to Microsoft, Xero, and Google API terms of service.                                  | Must-have   | Third-party compliance.                     |

#### 2.2.8 Backup & Recovery

| ID              | Requirement                                                                                  | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-BKP-001     | Regular backups of critical data (e.g., archived appointments, configuration).                | Must-have   | Data protection.                            |
| NFR-BKP-002     | Ability to restore service and data in case of failure.                                      | Must-have   | Disaster recovery.                          |
| NFR-BKP-003     | System must verify backup completeness and restore consistency.                                  | Must-have   | Data integrity and disaster recovery.        |

#### 2.2.9 Multi-user/Role Provisions

| ID              | Requirement                                                                                  | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-MUL-001      | System must ensure strict user data isolation in multi-user mode.                                | Must-have   | Data privacy and security.                  |
| NFR-ROL-001      | System must prevent unauthorized role escalation.                                                | Must-have   | Security.                                   |
| NFR-ROL-002      | System must prevent unauthorized role escalation.                                                | Must-have   | Security.                                   |

# References

- Link to additional resources, specs, or tickets
