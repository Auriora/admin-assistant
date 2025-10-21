---
title: "SRS Overall Description"
id: "SRS-Overall-Description"
type: [ srs, description ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "2024-12-19"
tags: [srs, description, requirements]
links:
  tooling: []
---

# Overall Description

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: DD-MM-YYYY
- **Last Updated**: 2024-12-19
- **Audience**: [Developers, Project Managers, Stakeholders]

## 1. Purpose

This section provides a high-level overview of the Admin Assistant system, including its purpose, functionality, and how it interacts with its environment. Admin Assistant is a web application designed for professionals who rely on Microsoft 365 Calendar to manage appointments, billing, and travel. The system automates the archiving of calendar appointments, extraction of timesheets for billing, travel time calculation, and appointment categorization, integrating with Microsoft 365 via the Microsoft Graph API. The application is intended for single-user operation initially, with provisions for future multi-user and role-based access.

## 2. Context

### Product Perspective

Admin Assistant operates as a standalone web application, integrating directly with the user's Microsoft 365 account using the Microsoft Graph API. It interacts with external services such as OneDrive, Xero, Google Directions API, and OpenAI for document storage, billing, travel time estimation, and AI-powered recommendations and automation, respectively. The system is designed to be extensible for future integration with additional services and multi-user environments.

### Assumptions

The following assumptions are made regarding the Admin Assistant system:

- User has a Microsoft 365 account with calendar access
- User has access to OneDrive and Xero accounts
- User consents to use of external APIs (Google Directions, OpenAI)
- User will configure locations and rules as needed

## 3. Details

### Product Functions

- Automated daily archiving of calendar appointments
- Manual trigger for archiving
- Extraction and categorization of timesheet data for billing
- PDF generation and upload to OneDrive and Xero
- Location recommendation and management
- Travel time calculation and appointment creation
- Appointment categorization and privacy management
- Out-of-Office automation
- Rules and guidelines management for recommendations
- AI-powered recommendations and automation using OpenAI
- User interface for interaction and management
- Audit logging and notifications
- Data export in PDF, CSV, and Excel formats

Notable functions or capabilities that the Admin Assistant system will not provide:

- Direct modification of the user's main calendar outside of archiving and travel appointment creation
- Support for non-Microsoft calendar sources (initially)
- In-app billing or payment processing (beyond Xero integration)

### Constraints

The following constraints affect the design and implementation of the Admin Assistant system:

#### Technical Constraints

- Must use Microsoft Graph API for calendar access
- Must use Microsoft authentication
- Must support integration with OneDrive, Xero, Google Directions API, and OpenAI

#### Technology Stack Constraints

- The project will be implemented in **Python** using the **Flask** web framework.
- **Bootstrap** will be used for layout and graphics, integrated via **Flask-Bootstrap** or **Flask-Bootstrap4**.
- Flask's Jinja2 templating engine will be used for dynamic HTML generation.
- Flask extensions may be used for authentication, forms, and other features as needed.
- The system must be deployable on standard cloud or on-premise infrastructure.
- **Alternative:** For future scalability or if a more full-featured framework is required, **Django** (with django-crispy-forms and django-bootstrap4) may be considered.

#### Business Constraints

- Initially single-user, but must be designed for future multi-user and role-based support
- Must comply with data privacy and security best practices

# References

- Link to additional resources, specs, or tickets
