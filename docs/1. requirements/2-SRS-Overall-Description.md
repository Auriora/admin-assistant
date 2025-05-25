# 2. Overall Description

This section provides a high-level overview of the Admin Assistant system, including its purpose, functionality, and how it interacts with its environment.

Admin Assistant is a web application designed for professionals who rely on Microsoft 365 Calendar to manage appointments, billing, and travel. The system automates the archiving of calendar appointments, extraction of timesheets for billing, travel time calculation, and appointment categorization, integrating with Microsoft 365 via the Microsoft Graph API. The application is intended for single-user operation initially, with provisions for future multi-user and role-based access.

## 2.1 Product Perspective

Admin Assistant operates as a standalone web application, integrating directly with the user's Microsoft 365 account using the Microsoft Graph API. It interacts with external services such as OneDrive, Xero, and Google Directions API for document storage, billing, and travel time estimation, respectively. The system is designed to be extensible for future integration with additional services and multi-user environments.

## 2.2 Product Functions

- Automated daily archiving of calendar appointments
- Manual trigger for archiving
- Extraction and categorization of timesheet data for billing
- PDF generation and upload to OneDrive and Xero
- Location recommendation and management
- Travel time calculation and appointment creation
- Appointment categorization and privacy management
- Out-of-Office automation
- Rules and guidelines management for recommendations
- User interface for interaction and management
- Audit logging and notifications
- Data export in PDF, CSV, and Excel formats

Notable functions or capabilities that the Admin Assistant system will not provide:

- Direct modification of the user's main calendar outside of archiving and travel appointment creation
- Support for non-Microsoft calendar sources (initially)
- In-app billing or payment processing (beyond Xero integration)

## 2.3 Constraints

The following constraints affect the design and implementation of the Admin Assistant system:

### Technical Constraints

- Must use Microsoft Graph API for calendar access
- Must use Microsoft authentication
- Must support integration with OneDrive, Xero, and Google Directions API

### Technology Stack Constraints

- Web application (framework TBD)
- Must be deployable on standard cloud or on-premise infrastructure

### Business Constraints

- Initially single-user, but must be designed for future multi-user and role-based support
- Must comply with data privacy and security best practices

## 2.4 Assumptions

The following assumptions are made regarding the Admin Assistant system:

- User has a Microsoft 365 account with calendar access
- User has access to OneDrive and Xero accounts
- User consents to use of external APIs (Google Directions, OpenAI)
- User will configure locations and rules as needed
