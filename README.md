# Admin Assistant

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?logo=gnu)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Tests](https://github.com/bcherrington/admin-assistant/workflows/Tests/badge.svg)](https://github.com/bcherrington/admin-assistant/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/bcherrington/admin-assistant/branch/main/graph/badge.svg)](https://codecov.io/gh/bcherrington/admin-assistant)
[![GitHub issues](https://img.shields.io/github/issues/bcherrington/admin-assistant.svg?logo=github)](https://github.com/bcherrington/admin-assistant/issues)
[![GitHub last commit](https://img.shields.io/github/last-commit/bcherrington/admin-assistant.svg?logo=github)](https://github.com/bcherrington/admin-assistant/commits/main)
[![Status: Development](https://img.shields.io/badge/Status-Development-orange.svg?logo=git)](https://github.com/bcherrington/admin-assistant)

A comprehensive calendar management and timesheet automation system for Microsoft 365 users. Admin Assistant automates calendar archiving, appointment categorization, overlap resolution, privacy management, and timesheet generation for professional service providers.

## 🚀 Project Status

**Current Status**: Core infrastructure complete (80%), implementing timesheet generation and travel management features.

- ✅ **Infrastructure Complete**: Microsoft Graph integration, database schema, CLI interface, testing framework
- ✅ **Phase 1 Workflows**: Calendar archiving, category processing, overlap resolution, privacy automation
- 🔄 **In Progress**: PDF timesheet generation, travel detection, Xero integration
- 📋 **Next**: Enhanced web interface, email notifications, client communications

For detailed status and implementation roadmap, see [Consolidated Action Plan](docs/CAP-001-Consolidated-Action-Plan.md).

## 📚 Documentation

### Quick Start Documents
- **[Consolidated Action Plan](docs/CAP-001-Consolidated-Action-Plan.md)** - Current status and implementation roadmap
- **[Current Implementation Status](docs/CIS-001-Current-Implementation-Status.md)** - Detailed feature completion status
- **[CLI Command Structure](docs/2-design/CLI-001-Command-Structure.md)** - Complete CLI reference
- **[System Architecture](docs/2-design/ARCH-001-System-Architecture.md)** - Technical architecture overview

### Complete Documentation Structure
```
docs/
├── 1-requirements/          # System requirements and use cases
├── 2-design/               # Architecture and design documents
├── 3-implementation/       # Implementation guides
├── 4-testing/             # Test cases and plans
├── guidelines/            # Development guidelines
└── CAP-001-Consolidated-Action-Plan.md  # Main project roadmap
```

## 🛠️ CLI Usage

The Admin Assistant provides a powerful CLI for managing calendars, archives, categories, and timesheet operations.

### Quick Start
```bash
# Set user environment variable to avoid repeating --user
export ADMIN_ASSISTANT_USER=123

# Login to Microsoft 365
admin-assistant login msgraph --user 123

# Archive calendar events
admin-assistant calendar archive --archive-config 1 --date "last 7 days"

# List categories
admin-assistant category list

# Generate timesheet (coming soon)
admin-assistant timesheet export --output PDF
```

### Core Commands

#### Calendar Operations
```bash
# Archive calendar events using a specific config
admin-assistant calendar archive "Work Archive" --user <USER_ID> --date "last week"

# List calendars for user
admin-assistant calendar list --user <USER_ID> --store msgraph

# Create new calendar
admin-assistant calendar create --user <USER_ID> --store msgraph --name "Archive Calendar"

# Analyze overlapping appointments
admin-assistant calendar analyze-overlaps --user <USER_ID> --start-date "2024-01-01"

# Backup calendar to file
admin-assistant calendar backup --user <USER_ID> --source "Work Calendar" --destination "/backups/work.csv" --format csv

# Backup calendar to another calendar
admin-assistant calendar backup --user <USER_ID> --source "Work Calendar" --destination "Work Backup" --format local_calendar
```

#### Category Management
```bash
# List categories
admin-assistant category list --user <USER_ID> --store local

# Add new category
admin-assistant category add --user <USER_ID> --name "Client Work" --description "Billable client work"

# Validate appointment categories
admin-assistant category validate --user <USER_ID> --start-date "2024-01-01" --stats
```

#### Configuration Management
```bash
# List all archive configs for a user
admin-assistant config calendar archive list --user <USER_ID>

# Create a new archive config (interactive prompts for missing fields)
admin-assistant config calendar archive create --user <USER_ID>

# Create a new archive config (all options provided)
admin-assistant config calendar archive create --user <USER_ID> --name "Work Archive" --source-uri "msgraph://source" --dest-uri "msgraph://dest" --timezone "Europe/London" --active

# Activate/deactivate/delete a config
admin-assistant config calendar archive activate --user <USER_ID> --config-id <CONFIG_ID>
admin-assistant config calendar archive deactivate --user <USER_ID> --config-id <CONFIG_ID>
admin-assistant config calendar archive delete --user <USER_ID> --config-id <CONFIG_ID>
```

#### Authentication
```bash
# Login to Microsoft 365
admin-assistant login msgraph --user <USER_ID>

# Logout
admin-assistant login logout --user <USER_ID>
```

#### Background Jobs
```bash
# Schedule automatic archiving
admin-assistant jobs schedule --user <USER_ID> --config-id <CONFIG_ID> --frequency daily

# Check job status
admin-assistant jobs status --user <USER_ID>

# Trigger manual archive
admin-assistant jobs trigger --user <USER_ID> --config <CONFIG_ID>

# Schedule automatic backup
admin-assistant jobs schedule-backup --user <USER_ID> --source "Work Calendar" --destination "/backups/work.csv" --type daily --hour 2

# Check backup job status
admin-assistant jobs backup-status --user <USER_ID>
```

#### Appointment Restoration
```bash
# Restore appointments from audit logs (failed operations)
admin-assistant restore from-audit-logs --user <USER_ID> --start-date "2025-05-29" --end-date "2025-06-06"

# Restore from backup calendars
admin-assistant restore from-backup-calendars --user <USER_ID> --source "Recovered" "Recovered Missing" --destination "Consolidated Recovery"

# Backup a calendar to file
admin-assistant restore backup-calendar --user <USER_ID> --source "Main Calendar" --destination "backup.csv" --format csv

# List restoration configurations
admin-assistant restore list-configs --user <USER_ID>

# Dry run (preview without making changes)
admin-assistant restore from-audit-logs --dry-run
```

For complete CLI documentation, see [CLI Command Structure](docs/2-design/CLI-001-Command-Structure.md).

## 🏗️ Architecture

Admin Assistant is built as a modular, service-oriented application with:

- **Core Layer**: Business logic, domain models, and data access abstractions
- **Web Interface**: Flask-based web UI with Bootstrap and Jinja2
- **CLI Interface**: Typer-based command-line interface for automation
- **Integration Layer**: Microsoft Graph, Google Directions, Xero, OpenAI APIs
- **Data Layer**: SQLAlchemy with PostgreSQL/SQLite support
- **Background Processing**: Flask-APScheduler for automated tasks

Key architectural patterns:
- Repository pattern for data access abstraction
- Service layer for business logic
- Orchestrator pattern for complex workflows
- Generic entity associations for extensibility

See [System Architecture](docs/2-design/ARCH-001-System-Architecture.md) for detailed technical documentation.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Microsoft 365 account with calendar access
- Virtual environment (recommended)

### Installation
```bash
# Clone the repository
git clone https://github.com/bcherrington/admin-assistant.git
cd admin-assistant

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -m flask db upgrade

# Login to Microsoft 365
admin-assistant login msgraph --user <YOUR_USER_ID>
```

### First Steps
1. **Create an archive configuration**: `admin-assistant config calendar archive create --user <USER_ID>`
2. **Test archiving**: `admin-assistant calendar archive "Work Archive" --user <USER_ID> --date "yesterday"`
3. **Validate categories**: `admin-assistant category validate --user <USER_ID> --stats`

## 🧪 Development

### Running Tests
```bash
# Activate virtual environment
source .venv/bin/activate

# Run core application tests (default - excludes utility tests)
python scripts/dev_cli.py test all

# Run all tests including utilities
python scripts/dev_cli.py test all-inclusive

# Run only utility/development infrastructure tests
python scripts/dev_cli.py test utilities

# Run with coverage
python scripts/dev_cli.py test all --coverage

# Run specific test categories
python scripts/dev_cli.py test unit
python scripts/dev_cli.py test integration
```

#### Test Organization
- **Core Tests**: Application logic, services, repositories (default runs)
- **Utility Tests**: Testing infrastructure, development tools (excluded by default)
- **Integration Tests**: End-to-end workflows and system integration

### Development Guidelines
- Follow the patterns established in `core/` directory
- Use repository pattern for data access
- Add comprehensive tests for new features
- Update documentation for API changes

See [Development Guidelines](docs/guidelines/) for detailed coding standards.

## 📋 Current Features

### ✅ Implemented
- **Calendar Archiving**: Automated daily archiving with overlap detection
- **Appointment Restoration**: Generic restoration from audit logs, backup calendars, and export files
- **Calendar Backup**: Backup calendars to various formats (CSV, JSON, ICS) or other calendars
- **Category Management**: Appointment categorization with validation
- **Privacy Automation**: Automatic privacy marking and out-of-office detection
- **Overlap Resolution**: Smart detection and resolution of conflicting appointments
- **CLI Interface**: Comprehensive command-line tools with restoration commands
- **Background Jobs**: Scheduled archiving and maintenance tasks
- **Audit Logging**: Complete audit trail for all operations with reversible operations support

### 🔄 In Development
- **PDF Timesheet Generation**: Extract and format billable hours
- **Travel Detection**: Automatic travel appointment suggestions
- **Xero Integration**: Invoice generation with timesheet attachments

### 📋 Planned
- **Enhanced Web Interface**: Improved UI for overlap resolution
- **Email Notifications**: Client communications and status updates
- **Advanced Reporting**: Analytics and insights dashboard

## 🤝 Contributing

This project follows the [Solo-Developer-AI-Process](docs/Solo-Developer-AI-Process.md) framework for AI-assisted development.

For implementation tasks, see [AI Implementation Prompts](docs/AIP-001-AI-Implementation-Prompts.md) for ready-to-use development prompts.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📚 Documentation

### Quick Start
- [Getting Started Guide](docs/user-guides/UG-001-Getting-Started.md) - Start here for new users
- [CLI Reference](docs/user-guides/UG-002-CLI-Reference.md) - Complete command reference
- [Troubleshooting Guide](docs/user-guides/UG-003-Troubleshooting.md) - Common issues and solutions

### Project Documentation
- [Current Implementation Status](docs/CIS-001-Current-Implementation-Status.md) - Single source of truth for project status
- [Consolidated Action Plan](docs/CAP-001-Consolidated-Action-Plan.md) - Development roadmap and priorities
- [Solo Developer AI Process](docs/Solo-Developer-AI-Process.md) - Development framework

### Technical Documentation
- [Software Requirements Specification](docs/1-requirements/) - Complete requirements
- [System Architecture](docs/2-design/ARCH-001-System-Architecture.md) - System design
- [Database Schema](docs/2-design/DATABASE-SCHEMA-001-Current-Schema.md) - Current database structure
- [CLI Command Structure](docs/2-design/CLI-001-Command-Structure.md) - Command organization
- [Test Plan](docs/4-testing/TP-001-Test-Plan.md) - Testing strategy
- [Requirements Traceability](docs/A-traceability/TM-001-Requirements-Implementation-Matrix.md) - Implementation tracking

## 🔗 Links

- **Issues**: [GitHub Issues](https://github.com/bcherrington/admin-assistant/issues)
- **Project Board**: [GitHub Projects](https://github.com/bcherrington/admin-assistant/projects)