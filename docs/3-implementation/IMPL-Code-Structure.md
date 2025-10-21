---
title: "Implementation Guide: Code Structure Overview"
id: "IMPL-Code-Structure"
type: [ implementation ]
status: [ draft ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [implementation, guide, code-structure, coding-standards]
links:
  tooling: []
---

# Implementation Guide: Code Structure Overview

- **Owner**: Auriora Team
- **Status**: Draft
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY
- **Audience**: [Developers, Maintainers]
- **Scope**: Root

## 1. Purpose

This document describes the overall code organization and directory structure of the Admin Assistant project. It aims to provide developers and maintainers with a clear understanding of where different components reside and how they interact, facilitating navigation, development, and maintenance.

## 2. Summary

The Admin Assistant project follows a modular and layered architecture, primarily organized around a `src/` directory containing the core application logic, web interface, and command-line interface. Supporting assets such as documentation, tests, and scripts are located in their respective top-level directories.

## 3. Key Concepts

- `src/`: Contains all primary source code for the application.
  - `src/core/`: Houses the core business logic, domain models, services, repositories, and utilities. This layer is designed to be independent of any specific interface (web or CLI).
  - `src/web/`: Contains the Flask web application, including routes, templates, static files, and web-specific configurations.
  - `src/cli/`: Contains the command-line interface application, defining commands and their logic, which interacts with the `core/` services.
- `tests/`: Contains all unit, integration, and end-to-end tests for the project, mirroring the `src/` structure.
- `docs/`: Stores all project documentation, organized into subfolders for requirements, architecture, implementation, etc.
- `scripts/`: Contains various utility scripts for development, deployment, or one-off tasks.
- `config/`: Holds configuration files for different environments or tools.
- `.venv/`: (Hidden) Python virtual environment for managing project dependencies.
- `logs/`: (Generated) Directory for application log files.

## 4. Usage

To understand the project's structure, developers typically start by exploring the `src/` directory. For example, to run the web application or a CLI command:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the Flask web application
flask run

# Run a CLI command (e.g., list calendars for user 1)
admin-assistant calendar list --user 1
```

## 5. Internal Behaviour

The `src/core/` directory is the heart of the application, containing reusable business logic that is agnostic to the presentation layer. Both the `src/web/` and `src/cli/` components interact with the `src/core/` services and repositories to perform operations. This separation ensures that business rules are defined once and consistently applied across all interfaces.

- **Data Flow**: User input (from web UI or CLI) is processed by the respective interface layer, which then calls appropriate services in `src/core/`. These services interact with repositories (also in `src/core/`) to access data or external APIs.
- **Dependency Management**: Dependencies are managed via `requirements.txt` and installed into the `.venv/`.
- **Configuration**: Application-wide and environment-specific configurations are handled through `config/` files and environment variables.

## 6. Extension Points

- **New Features**: New business logic should primarily be added to `src/core/` (new services, models, repositories).
- **New Interfaces**: Additional interfaces (e.g., a mobile API, a desktop app) can be built on top of `src/core/` without modifying existing logic.
- **Integrations**: New external API integrations should be encapsulated within `src/core/repositories/` or dedicated service modules.
- **Configuration**: The `config/` directory and environment variable system allow for flexible deployment and customization.

# References

- [System Architecture](../2-architecture/ARCH-001-System-Architecture.md)
- [Current Database Schema](../2-architecture/DATA-002-Current-Schema.md)
- [Audit Logging Implementation](./IMPL-Audit-Logging.md)
- [CLI Command Structure](../2-architecture/HLD-CLI-001-Command-Structure.md)