# UXF-CLI-001: Command-Line Interface (CLI) Design

## Purpose and Scope
The Admin Assistant CLI provides a command-line interface for administrative, maintenance, and automation tasks. It enables advanced users, system administrators, and automated scripts to interact with the system without using the web UI. The CLI is implemented in the `cli/` directory and is a first-class interface alongside the web application.

## Supported Use Cases and Commands (Overview)
- **Archiving:** Trigger calendar archiving for a user or date range
- **Export:** Generate and export timesheets, reports, or data extracts
- **User Management:** List, add, or deactivate users (admin only)
- **Diagnostics:** Run health checks, view logs, or test integrations
- **Automation:** Schedule or script any supported operation for headless or batch execution

## Architecture and Core Interaction
- The CLI is a thin layer over the core business logic and services, ensuring feature parity and consistent behavior with the web UI.
- All CLI commands invoke core services directly, using the same repository and service abstractions as the web and background jobs.
- The CLI is implemented using Python's Typer, Click, or argparse for argument parsing and help output.

## Security and Auditability
- Sensitive CLI operations (e.g., user management, data export) require authentication and authorization.
- All CLI actions are logged with user, timestamp, and command details for auditability.
- CLI must not expose secrets or sensitive data in help output or logs.

## Extensibility and Best Practices
- New features in the core layer should expose corresponding CLI commands where appropriate.
- CLI commands should be scriptable, support non-interactive operation, and provide clear error messages.
- Help output must be comprehensive and up-to-date for all commands and options.
- Follow the same error handling, logging, and observability standards as the rest of the system.

## Example Command Structure
```
$ admin-assistant-cli --help
Usage: admin-assistant-cli [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  archive      Archive calendar data for a user/date range
  export       Export timesheet or report
  user         User management commands
  diagnostics  Run system diagnostics
  ...

$ admin-assistant-cli archive --user alice@example.com --start 2024-06-01 --end 2024-06-07
Archive completed for user alice@example.com (7 appointments archived)
```

## References
- [CLI Requirements](../1-requirements/3-SRS-Specific-Requirements.md#3.1.12-command-line-interface-cli)
- [System Architecture](architecture.md)
- [Core Layer and Data Access Patterns](architecture.md#41-core-layer-and-data-access-patterns) 