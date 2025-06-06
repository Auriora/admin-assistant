# Development Scripts

This directory contains development and build helper scripts for the admin-assistant project.

## Main Development CLI

The primary entry point is `dev_cli.py`, which provides a unified interface to all development tasks.

### Usage

```bash
# Activate virtual environment first
source .venv/bin/activate

# Run the development CLI
python scripts/dev_cli.py --help
```

### Available Commands

#### Environment Information
```bash
python scripts/dev_cli.py info
```
Shows comprehensive development environment information including Python version, virtual environment status, Git repository status, and project paths.

#### Testing Commands
```bash
python scripts/dev_cli.py test --help
python scripts/dev_cli.py test unit              # Run unit tests
python scripts/dev_cli.py test integration       # Run integration tests
python scripts/dev_cli.py test all               # Run all tests
python scripts/dev_cli.py test coverage          # Generate coverage report
python scripts/dev_cli.py test specific <path>   # Run specific test
python scripts/dev_cli.py test marker <marker>   # Run tests with marker
python scripts/dev_cli.py test archiving         # Run archiving tests
python scripts/dev_cli.py test observability     # Run observability tests
python scripts/dev_cli.py test lint              # Lint test files
```

#### Database Commands
```bash
python scripts/dev_cli.py db --help
python scripts/dev_cli.py db init                # Initialize database
python scripts/dev_cli.py db migrate             # Create migration
python scripts/dev_cli.py db upgrade             # Upgrade database
python scripts/dev_cli.py db current             # Show current revision
python scripts/dev_cli.py db history             # Show migration history
python scripts/dev_cli.py db reset               # Reset database (WARNING: deletes data)
python scripts/dev_cli.py db backup              # Backup database files
```

#### Build Commands
```bash
python scripts/dev_cli.py build --help
python scripts/dev_cli.py build package          # Build package distributions
python scripts/dev_cli.py build install          # Install package in current environment
python scripts/dev_cli.py build check            # Check package metadata
python scripts/dev_cli.py build clean            # Clean build artifacts
python scripts/dev_cli.py build deps             # Show build dependencies
python scripts/dev_cli.py build info             # Show build information
```

#### Version Management
```bash
python scripts/dev_cli.py version --help
python scripts/dev_cli.py version show           # Show current version
python scripts/dev_cli.py version bump <part>    # Bump version (major/minor/patch/release/num)
python scripts/dev_cli.py version tag            # Create git tag
python scripts/dev_cli.py version history        # Show version history
python scripts/dev_cli.py version check          # Check version consistency
```

#### Cleanup Commands
```bash
python scripts/dev_cli.py clean --help
python scripts/dev_cli.py clean list             # List cleanable artifacts
python scripts/dev_cli.py clean build            # Clean build artifacts
python scripts/dev_cli.py clean test             # Clean test artifacts
python scripts/dev_cli.py clean cache            # Clean Python cache
python scripts/dev_cli.py clean temp             # Clean temporary files
python scripts/dev_cli.py clean node             # Clean Node.js artifacts
python scripts/dev_cli.py clean all              # Clean all artifacts
```

## Legacy Scripts

The following legacy scripts have been removed and replaced by the unified CLI:

- **`init_core_db.py`** - ✅ **Replaced by**: `./dev db init`
- **`run_tests.py`** - ✅ **Replaced by**: `./dev test` commands

### Appointment Restoration Scripts (Removed)

The following appointment restoration scripts have been **removed** and replaced by integrated CLI commands in the main admin-assistant CLI:

- **`restore_lost_appointments.py`** - ✅ **Replaced by**: `admin-assistant restore from-audit-logs`
- **`restore_missing_appointments.py`** - ✅ **Replaced by**: `admin-assistant restore from-audit-logs` (with custom date ranges)
- **`restore_to_msgraph_recovery.py`** - ✅ **Replaced by**: `admin-assistant restore from-backup-calendars`
- **`export_appointments_for_msgraph.py`** - ✅ **Replaced by**: `admin-assistant restore backup-calendar`
- **`verify_restored_appointments.py`** - ✅ **Replaced by**: `admin-assistant restore list-configs` and dry-run options
- **`run_appointment_restoration.sh`** - ✅ **Replaced by**: Direct CLI commands
- **`run_export_for_msgraph.sh`** - ✅ **Replaced by**: Direct CLI commands
- **`run_msgraph_restoration.sh`** - ✅ **Replaced by**: Direct CLI commands

**Migration Examples:**

```bash
# Old way (scripts removed)
./scripts/run_appointment_restoration.sh --dry-run
python scripts/restore_lost_appointments.py --start-date 2025-05-29

# New way (integrated into main CLI)
admin-assistant restore from-audit-logs --dry-run
admin-assistant restore from-audit-logs --start-date 2025-05-29

# Old way (scripts removed)
python scripts/restore_to_msgraph_recovery.py --dry-run

# New way (integrated into main CLI)
admin-assistant restore from-backup-calendars --source "Recovered" "Recovered Missing" --destination "MSGraph Recovery" --dry-run
```

See the [Appointment Restoration Guide](../docs/user-guides/appointment-restoration-guide.md) for complete usage instructions.

## Architecture

The development CLI is built using [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/) for a modern CLI experience with:

- **Modular command structure** - Commands are organized into logical groups
- **Rich output** - Beautiful tables, progress indicators, and colored output
- **Environment validation** - Checks for virtual environment, dependencies, etc.
- **Error handling** - Graceful error handling with helpful messages
- **Progress indication** - Visual feedback for long-running operations

### Directory Structure

```
scripts/
├── dev_cli.py              # Main CLI entry point
├── commands/               # Command modules
│   ├── __init__.py
│   ├── test_commands.py    # Testing commands
│   ├── db_commands.py      # Database commands
│   ├── build_commands.py   # Build and packaging commands
│   ├── version_commands.py # Version management commands
│   └── clean_commands.py   # Cleanup commands
├── utils/                  # Shared utilities
│   ├── __init__.py
│   ├── environment.py      # Environment setup and validation
│   └── paths.py           # Path management utilities
└── README.md              # This file
```

## Migration from Legacy Scripts

The legacy scripts have been removed. If you have any references to them, here's how to migrate:

### From `run_tests.py` (removed)
```bash
# Old way (no longer available)
python scripts/run_tests.py --unit --verbose --coverage

# New way
./dev test unit --verbose --coverage
# or
python scripts/dev_cli.py test unit --verbose --coverage
```

### From `init_core_db.py` (removed)
```bash
# Old way (no longer available)
python scripts/init_core_db.py

# New way
./dev db init
# or
python scripts/dev_cli.py db init
```

## Requirements

The development CLI requires the following dependencies (already included in the project):
- `typer[all]` - CLI framework
- `rich` - Rich text and beautiful formatting
- `pytest` - Testing framework (for test commands)
- `bump2version` - Version management (for version commands)

## Contributing

When adding new development scripts or commands:

1. **Use the CLI framework** - Add new commands to the appropriate command module
2. **Follow the pattern** - Use Rich for output, handle errors gracefully
3. **Add help text** - Provide clear descriptions for commands and options
4. **Test thoroughly** - Ensure commands work in different environments
5. **Update documentation** - Add new commands to this README
