# 1. Introduction

This section provides an introduction to the Admin Assistant system and this SRS document.

## 1.1 Purpose

The purpose of this Software Requirements Specification (SRS) is to define the functional and non-functional requirements for the Admin Assistant system. Admin Assistant is a web application that automates calendar archiving, timesheet extraction, billing, travel calculation, and appointment categorization for a single user (with future support for multiple users and roles). The system integrates with Microsoft 365 Calendar via the Microsoft Graph API and uses Microsoft account authentication. This document establishes a clear foundation for the development, testing, and deployment of the system, ensuring that all stakeholders have a shared understanding of the system's capabilities and constraints.

This SRS document serves as the primary reference for:

- **Developers** responsible for implementing and testing the application.
- **UX / UI designers** defining user interactions and visual design.
- **Project managers and stakeholders** tracking scope and progress.
- **Quality-assurance engineers** creating verification and validation plans.
- **Security and compliance teams** ensuring adherence to relevant standards.

## 1.2 Scope

This Software Requirements Specification (SRS) document defines the requirements for Admin Assistant. The scope of this document **includes**:

- Functional requirements for all features and capabilities of Admin Assistant, such as calendar archiving, timesheet extraction, billing integration, travel calculation, appointment categorization, privacy management, and user interface.
- Non-functional requirements including performance, security, usability, and reliability
- External interface requirements for user interfaces, software interfaces, and communications interfaces
- System constraints and assumptions related to the application environment
- Use cases that describe how users will interact with the system to accomplish key tasks
- Compliance requirements and standards the system must adhere to in the professional services domain

This SRS document **does not include**:

- Detailed technical implementation specifications of the web framework or database
- Project management information such as schedules, budgets, or resource allocation
- Test plans or test cases (these will be covered in separate documentation)
- User documentation or training materials for end users
- Deployment or operational procedures for server environments

## 1.3 Definitions and Acronyms

- **SRS**: Software Requirements Specification
- **UI**: User Interface
- **UX**: User Experience
- **API**: Application Programming Interface
- **PDF**: Portable Document Format
- **JWT**: JSON Web Token
- **CRUD**: Create, Read, Update, Delete
- **MVP**: Minimum Viable Product
- **Microsoft Graph API**: Microsoft API for accessing Microsoft 365 services