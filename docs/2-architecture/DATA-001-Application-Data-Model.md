---
title: "Architecture: Application Data Model"
id: "DATA-001"
type: [ data, architecture, design ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [data-model, architecture, database]
links:
  tooling: []
---

# Application Data Model

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY
- **Audience**: [Developers, Architects]

## 1. Purpose

This document describes the main data entities and their relationships for the Admin Assistant system. It clarifies the architectural decision to separate the data model into two distinct databases: a **Core Database** and a **Web Database**.

## 2. Context

The decision to use two separate databases was made to support modularity, security, and future extensibility.

- **Security**: Sensitive tokens and user-facing data are isolated in the web database, while core business data is kept separate.
- **Modularity**: Enables independent migration and versioning for the core business logic and the web front end.
- **Integration**: Facilitates integration with external APIs and services without exposing core business data directly.
- **Maintainability**: Allows for a clear separation of concerns, making each layer easier to test, maintain, and extend.

## 3. Details

### 3.1. Database Separation

| Entity                  | Core DB | Web DB |
|------------------------|:-------:|:------:|
| User                   |   ✓     |    ✓   |
| Appointment            |   ✓     |        |
| Location               |   ✓     |        |
| Category               |   ✓     |        |
| Timesheet              |   ✓     |        |
| AuditLog               |         |    ✓   |
| Rule                   |         |    ✓   |
| Notification           |         |    ✓   |
| ArchivePreference      |         |    ✓   |
| VirtualCalendar        |   ✓     |        |
| ChatSession/AIInteraction |  ✓      |        |
| EntityAssociation      |   ✓     |        |
| Prompt                 |   ✓     |        |
| ActionLog              |   ✓     |        |

### 3.2. Core Database Entities

- **User**: Represents a system user.
- **Appointment**: A calendar event, linked to a user, location, and category.
- **Location**: User-defined or system-recommended locations.
- **Category**: Billing or classification category for appointments.
- **Timesheet**: A generated timesheet for a user and date range.
- **VirtualCalendar**: A temporary grouping of overlapping appointments for user resolution.
- **ChatSession**: Persistent chat history for AI-assisted interactions.
- **ActionLog**: A central task list for items requiring user attention (e.g., overlap resolution).
- **Prompt**: Stores system, user, and action-specific prompts for the AI service.
- **EntityAssociation**: A generic mapping table to associate any entity with any other entity (e.g., an `ActionLog` task to a `VirtualCalendar`).

### 3.3. Web Database Entities

- **User**: The web-specific user model, potentially with different fields from the core user.
- **AuditLog**: Records all critical actions for compliance and troubleshooting.
- **Rule**: User-defined rules for automation.
- **Notification** & **NotificationPreference**: Manages user notifications and their preferences.
- **ArchivePreference**: User-specific preferences for the archiving process.

### 3.4. Key Relationships

- A **User** owns all their related data (Appointments, Locations, etc.).
- An **Appointment** references a Location and a Category.
- An **ActionLog** entry can be linked to a **VirtualCalendar** and a **ChatSession** via the **EntityAssociation** table to manage the overlap resolution process.

# References

- **Diagram**: See `DATA-001-Data-Model.puml` for the detailed PlantUML ERD diagram.
- **Schema**: See `DATA-002-Current-Schema.md` for the full database schema documentation.
