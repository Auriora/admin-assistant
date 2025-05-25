# 3. Specific Requirements

This section details the specific functional and non-functional requirements of the Admin Assistant system.

## 3.1 Functional Requirements

### 3.1.1 Calendar Archiving

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-CAL-001   | Automatically copy all appointments from the main calendar to an archive calendar at end of day. | Must-have   | Prevents loss of historical data.           |
| FR-CAL-002   | Allow user to manually trigger the archiving process.                                            | Should-have | Provides flexibility and control.           |
| FR-CAL-003   | Archive all appointments, regardless of status.                                                  | Must-have   | Ensures complete record.                    |

### 3.1.2 Timesheet Extraction and Billing

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-BIL-001   | Extract timesheet data from the archive calendar.                                                | Must-have   | Enables billing and reporting.              |
| FR-BIL-002   | Categorize appointments as Billable, Non-billable, or Travel.                                   | Must-have   | Supports accurate billing.                  |
| FR-BIL-003   | Generate a PDF timesheet matching the current Excel design, with template support.              | Must-have   | Familiar output, flexible for future needs. |
| FR-BIL-004   | Upload the PDF to OneDrive and connect directly to Xero via API.                                | Must-have   | Streamlines workflow.                       |

### 3.1.3 Location Recommendation

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-LOC-001   | Recommend a location for appointments missing one, using a fixed list, then past appointments.   | Must-have   | Ensures location data completeness.         |
| FR-LOC-002   | Allow user to add new locations or auto-create from invitations.                                | Should-have | Improves usability and automation.          |

### 3.1.4 Travel Assumptions and Calculation

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-TRV-001   | Assume travel starts/ends at Home (user profile), unless all-day event at another location.      | Must-have   | Accurate travel calculation.                |
| FR-TRV-002   | Handle exceptions such as multi-day trips.                                                      | Should-have | Flexibility for real-world scenarios.       |
| FR-TRV-003   | Add separate travel appointments using Google Directions API, considering traffic predictions.   | Must-have   | Accurate travel time for billing.           |

### 3.1.5 Categorization and Privacy

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-CAT-001   | Recommend billing categories using subject, attendees, and location (AI-assisted).               | Must-have   | Reduces manual work, improves accuracy.     |
| FR-CAT-002   | Allow user to override AI recommendations.                                                       | Must-have   | User control and trust.                     |
| FR-PRI-001   | Automatically mark personal and travel appointments as private.                                  | Must-have   | Protects sensitive information.             |
| FR-PRI-002   | Exclude private appointments from timesheet exports.                                             | Must-have   | Privacy compliance.                         |

### 3.1.6 Out-of-Office Automation

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-OOO-001   | Automatically mark all appointments as Out-of-Office.                                            | Must-have   | Consistent calendar status.                 |

### 3.1.7 Rules and Guidelines

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-RUL-001   | Maintain a user-specific rules/guidelines base for recommendations.                              | Must-have   | Customizable automation.                    |
| FR-RUL-002   | Allow user to edit/add rules via the UI.                                                         | Must-have   | User empowerment.                           |
| FR-RUL-003   | Use OpenAI API for complex recommendations.                                                      | Should-have | Advanced automation.                        |

### 3.1.8 User Interface

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-UI-001    | Provide a UI to trigger archives, generate timesheets, and manage rules.                        | Must-have   | Core user interaction.                      |
| FR-UI-002    | Support mobile-friendly exports.                                                                 | Should-have | Usability on mobile devices.                |

### 3.1.9 Additional/Recommended

| ID           | Requirement                                                                                      | Priority    | Rationale                                   |
|--------------|--------------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| FR-AUD-001   | Track all automated changes in an audit log.                                                     | Should-have | Transparency and troubleshooting.           |
| FR-OVR-001   | Detect and process manual changes made in Outlook.                                               | Should-have | Ensures data consistency.                   |
| FR-NOT-001   | Notify user of missing data or conflicts.                                                        | Should-have | Prevents errors and omissions.              |
| FR-MUL-001   | Make provisions for multi-user support.                                                          | Could-have  | Future scalability.                         |
| FR-ROL-001   | Make provisions for role-based access.                                                           | Could-have  | Future scalability.                         |
| FR-EXP-001   | Support CSV/Excel export in addition to PDF.                                                     | Should-have | Flexibility in reporting.                   |

## 3.2 Non-Functional Requirements

### 3.2.1 Performance

| ID              | Requirement                                                    | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-PERF-001    | Process daily archiving and timesheet generation within 5 min. | Must-have   | Timely automation.                          |

### 3.2.2 Security

| ID              | Requirement                                                    | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-SEC-001     | Use Microsoft authentication and encrypted storage.            | Must-have   | Protects user data.                         |

### 3.2.3 Usability

| ID              | Requirement                                                    | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-USE-001     | UI must be simple, intuitive, and mobile-friendly.             | Should-have | Improves user experience.                   |

### 3.2.4 Reliability

| ID              | Requirement                                                    | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-REL-001     | Handle API failures gracefully and retry as needed.            | Must-have   | Ensures reliability.                        |

### 3.2.5 Maintainability

| ID              | Requirement                                                    | Priority    | Rationale                                   |
|-----------------|----------------------------------------------------------------|-------------|---------------------------------------------|
| NFR-MNT-001     | Codebase should be modular and well-documented.                | Should-have | Eases future enhancements.                  |
