---
title: "HLD: CLI Command Structure"
id: "HLD-CLI-001"
type: [ hld, architecture, cli ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [hld, cli, architecture, commands]
links:
  tooling: []
---

# High-Level Design: CLI Command Structure

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: DD-MM-YYYY
- **Last Updated**: 2024-12-19
- **Audience**: [Developers, Power Users]

## 1. Purpose

This document provides a comprehensive overview of the Admin Assistant Command-Line Interface (CLI) command structure and organization. It serves as the authoritative reference for all available commands, their options, and usage patterns.

## 2. Context

The CLI is designed with clear separation between different types of commands to ensure usability and discoverability.

- **Command Design Principles**:
  - **Contextual Organization**: Commands are grouped by their primary context (e.g., `calendar`, `config`, `jobs`).
  - **Hierarchical Structure**: Related commands are nested logically (e.g., `config calendar archive`).
  - **Consistent Patterns**: Similar option names (`--user`) and behaviors (`--help`, interactive prompts) are used across all commands.
  - **Operational vs. Configuration**: A clear distinction is made between executing an action (e.g., `calendar archive`) and managing its settings (e.g., `config calendar archive`).

## 3. Details

### 3.1. Complete Command Tree

```
admin-assistant
├── calendar
│   ├── archive
│   ├── backup
│   ├── travel
│   ├── analyze-overlaps
│   ├── list
│   └── create
├── category
│   ├── list
│   ├── add
│   ├── edit
│   ├── delete
│   └── validate
├── config
│   └── calendar
│       └── archive
│           ├── list
│           ├── create
│           ├── activate
│           ├── deactivate
│           ├── delete
│           └── set-default
├── timesheet
│   ├── export
│   └── upload
├── jobs
│   ├── schedule
│   ├── schedule-backup
│   ├── trigger
│   ├── status
│   ├── backup-status
│   ├── remove
│   └── health
├── restore
│   ├── from-audit-logs
│   ├── from-backup-calendars
│   ├── backup-calendar
│   └── list-configs
└── login
    ├── msgraph
    └── logout
```

### 3.2. Key Command Groups

#### Calendar Operations (`calendar`)
Performs direct actions on calendar data, such as archiving, backup, and travel planning.

```bash
admin-assistant calendar archive --user <USER_ID> --archive-config <CONFIG_ID>
```

#### Configuration Management (`config`)
Manages system settings, primarily for calendar archiving.

```bash
admin-assistant config calendar archive create --user <USER_ID> --name "Work Archive"
```

#### Category Management (`category`)
Manages appointment, email, and contact categories.

```bash
admin-assistant category list --user <USER_ID>
```

#### Background Job Management (`jobs`)
Manages scheduled and manual background jobs for archiving and other tasks.

```bash
admin-assistant jobs schedule --user <USER_ID> --type daily
```

#### Appointment Restoration (`restore`)
Restores appointments from various sources like audit logs or backup calendars.

```bash
admin-assistant restore from-audit-logs --user <USER_ID> --dry-run
```

#### Authentication (`login`)
Handles user authentication and token management with Microsoft 365.

```bash
admin-assistant login msgraph --user <USER_ID>
```

### 3.3. Common Patterns

- **Environment Variables**: Set `ADMIN_ASSISTANT_USER` to avoid specifying `--user` for every command.
- **Help System**: Every command and subcommand supports the `--help` flag for detailed documentation.
- **Interactive Mode**: Many commands will interactively prompt for required options if they are not provided on the command line.

# References

- [System Architecture](./ARCH-001-System-Architecture.md)