"""
Admin Assistant CLI
==================

Usage Examples:
---------------
# Archive calendar events using a specific config
admin-assistant calendar archive "Work Archive" --user <USER_ID> --date "last 7 days"

# Timesheet calendar events using a specific config (business categories only)
admin-assistant calendar timesheet "Timesheet Config" --user <USER_ID> --date "last 7 days"

# List all archive configs for a user
admin-assistant config calendar archive list --user <USER_ID>

# List all timesheet configs for a user
admin-assistant config calendar timesheet list --user <USER_ID>

# Create a new archive config (interactive prompts for missing fields)
admin-assistant config calendar archive create --user <USER_ID>

# Create a new timesheet config (interactive prompts for missing fields)
admin-assistant config calendar timesheet create --user <USER_ID>

# Create a new archive config (all options provided)
admin-assistant config calendar archive create --user <USER_ID> --name "Work Archive" --source-uri "msgraph://user@example.com/calendars/primary" --dest-uri "msgraph://user@example.com/calendars/\"Archive Calendar\"" --timezone "Europe/London" --active

# Create a new timesheet config (all options provided)
admin-assistant config calendar timesheet create --user <USER_ID> --name "Timesheet Archive" --source-uri "msgraph://user@example.com/calendars/primary" --dest-uri "msgraph://user@example.com/calendars/\"Timesheet Archive\"" --timezone "Europe/London" --active

# Activate/deactivate/delete a config
admin-assistant config calendar archive activate --user <USER_ID> --config-id <CONFIG_ID>
admin-assistant config calendar archive deactivate --user <USER_ID> --config-id <CONFIG_ID>
admin-assistant config calendar archive delete --user <USER_ID> --config-id <CONFIG_ID>

# Timesheet config management (same commands as archive)
admin-assistant config calendar timesheet activate --user <USER_ID> --config-id <CONFIG_ID>
admin-assistant config calendar timesheet deactivate --user <USER_ID> --config-id <CONFIG_ID>
admin-assistant config calendar timesheet delete --user <USER_ID> --config-id <CONFIG_ID>

# Set a config as default (prints usage instructions)
admin-assistant config calendar archive set-default --user <USER_ID> --config-id <CONFIG_ID>
admin-assistant config calendar timesheet set-default --user <USER_ID> --config-id <CONFIG_ID>

All commands support --help for detailed options and descriptions.

Extending the CLI:
------------------
- To add new calendar or archive features, add commands to the appropriate module in cli/commands/ or cli/config/.
- Integrate with core services by importing from core.services or core.orchestrators as needed.
- Use interactive prompts for user-friendly CLI, and provide all options for automation/scripting.
"""

import os
from typing import Optional

import typer

# Load environment variables from .env file in current working directory
try:
    from dotenv import load_dotenv

    # Load environment variables from .env file in current working directory
    if os.path.exists(".env"):
        load_dotenv(".env")

except ImportError:
    # python-dotenv not available, continue without loading .env files
    pass

# Import command modules
from cli.commands.calendar import calendar_app
from cli.commands.category import category_app
from cli.commands.login import login_app
from cli.commands.jobs import jobs_app
from cli.commands.interactive_prompt import interactive_prompt_app
from cli.config.archive import archive_config_app
from cli.config.timesheet import timesheet_config_app
from cli.config.backup import backup_config_app
from cli.config.restoration import restoration_config_app

# Create main app and config app
app = typer.Typer(
    help="Admin Assistant CLI for running calendar and timesheet operations.",
    rich_markup_mode="rich"
)
config_app = typer.Typer(help="Configuration operations", rich_markup_mode="rich")
archive_config_main_app = typer.Typer(help="Calendar configuration operations", rich_markup_mode="rich")

# Register configuration apps
archive_config_main_app.add_typer(archive_config_app, name="archive")
archive_config_main_app.add_typer(timesheet_config_app, name="timesheet")
archive_config_main_app.add_typer(backup_config_app, name="backup")
config_app.add_typer(archive_config_main_app, name="calendar")
config_app.add_typer(restoration_config_app, name="restore")


@app.callback()
def main(ctx: typer.Context):
    """Admin Assistant CLI: Manage calendars, archives, and timesheets for users.

    Use --help on any command for details and options.

    Examples:
      # Archive operations
      admin-assistant calendar archive "Work Archive" --user <USER_ID> --date "last 7 days"
      admin-assistant config calendar archive list --user <USER_ID>
      admin-assistant config calendar archive create --user <USER_ID>
      admin-assistant config calendar archive activate --user <USER_ID> --config-id <CONFIG_ID>

      # Timesheet operations (business categories only)
      admin-assistant calendar timesheet "Timesheet Config" --user <USER_ID> --date "last 7 days"
      admin-assistant config calendar timesheet list --user <USER_ID>
      admin-assistant config calendar timesheet create --user <USER_ID>
      admin-assistant config calendar timesheet activate --user <USER_ID> --config-id <CONFIG_ID>

      # URI formats (new format with account context recommended)
      # New format: msgraph://user@example.com/calendars/primary
      # Legacy format: msgraph://calendars/primary (still supported)
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


# Register main command apps
app.add_typer(category_app, name="category")
app.add_typer(calendar_app, name="calendar")
app.add_typer(config_app, name="config")
app.add_typer(login_app, name="login")
app.add_typer(jobs_app, name="jobs")
app.add_typer(interactive_prompt_app, name="prompt")

# Import and add existing apps
from cli.reversible_operations import reversible_app
app.add_typer(reversible_app, name="reverse")

from cli.restoration import restoration_app
app.add_typer(restoration_app, name="restore")


if __name__ == "__main__":
    app()
