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
from rich.console import Console
from rich.tree import Tree

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
from cli.commands.auth import auth_app
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


@config_app.callback()
def config_callback(ctx: typer.Context):
    """Configuration management commands.

    Manage configurations for various operations.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@archive_config_main_app.callback()
def calendar_config_callback(ctx: typer.Context):
    """Calendar configuration commands.

    Manage calendar-related configurations.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())

# Register configuration apps
archive_config_main_app.add_typer(archive_config_app, name="archive")
archive_config_main_app.add_typer(timesheet_config_app, name="timesheet")
archive_config_main_app.add_typer(backup_config_app, name="backup")
archive_config_main_app.add_typer(restoration_config_app, name="restore")
config_app.add_typer(archive_config_main_app, name="calendar")


def build_command_tree():
    """Build a tree of commands for display."""
    tree = Tree("admin-assistant", style="bold green")

    # Manually build the tree based on our known structure
    # Main commands
    category_node = tree.add("[blue]category[/blue] - Category management")
    category_node.add("[cyan]list[/cyan] - List categories")
    category_node.add("[cyan]add[/cyan] - Add new category")
    category_node.add("[cyan]edit[/cyan] - Edit existing category")
    category_node.add("[cyan]delete[/cyan] - Delete category")
    category_node.add("[cyan]validate[/cyan] - Validate appointment categories")

    calendar_node = tree.add("[blue]calendar[/blue] - Calendar operations")
    calendar_node.add("[cyan]archive[/cyan] - Execute calendar archiving")
    calendar_node.add("[cyan]timesheet[/cyan] - Execute timesheet archiving")
    calendar_node.add("[cyan]backup[/cyan] - Backup calendar to file or another calendar")
    calendar_node.add("[cyan]travel[/cyan] - Auto-plan travel")
    calendar_node.add("[cyan]analyze-overlaps[/cyan] - Analyze overlapping appointments")
    calendar_node.add("[cyan]list[/cyan] - List calendars for user")
    calendar_node.add("[cyan]create[/cyan] - Create new calendar")

    # Restoration under calendar
    restore_node = calendar_node.add("[cyan]restore[/cyan] - Appointment restoration operations")
    restore_node.add("[yellow]from-audit-logs[/yellow] - Restore appointments from audit logs")
    restore_node.add("[yellow]from-backup-calendars[/yellow] - Restore from backup calendars")
    restore_node.add("[yellow]backup-calendar[/yellow] - Backup calendar to file or another calendar")

    config_node = tree.add("[blue]config[/blue] - Configuration operations")
    calendar_config_node = config_node.add("[cyan]calendar[/cyan] - Calendar configuration operations")

    # Archive config
    archive_config_node = calendar_config_node.add("[yellow]archive[/yellow] - Archive configuration management")
    archive_config_node.add("[green]list[/green] - List archive configurations")
    archive_config_node.add("[green]create[/green] - Create archive configuration")
    archive_config_node.add("[green]set-default[/green] - Set default archive configuration")
    archive_config_node.add("[green]activate[/green] - Activate archive configuration")
    archive_config_node.add("[green]deactivate[/green] - Deactivate archive configuration")
    archive_config_node.add("[green]delete[/green] - Delete archive configuration")

    # Timesheet config
    timesheet_config_node = calendar_config_node.add("[yellow]timesheet[/yellow] - Timesheet configuration management")
    timesheet_config_node.add("[green]list[/green] - List timesheet configurations")
    timesheet_config_node.add("[green]create[/green] - Create timesheet configuration")
    timesheet_config_node.add("[green]set-default[/green] - Set default timesheet configuration")
    timesheet_config_node.add("[green]activate[/green] - Activate timesheet configuration")
    timesheet_config_node.add("[green]deactivate[/green] - Deactivate timesheet configuration")
    timesheet_config_node.add("[green]delete[/green] - Delete timesheet configuration")

    # Backup config
    backup_config_node = calendar_config_node.add("[yellow]backup[/yellow] - Backup configuration management")
    backup_config_node.add("[green]list[/green] - List backup configurations")
    backup_config_node.add("[green]create[/green] - Create backup configuration")

    # Restoration config
    restore_config_node = calendar_config_node.add("[yellow]restore[/yellow] - Restoration configuration management")
    restore_config_node.add("[green]list[/green] - List restoration configurations")

    auth_node = tree.add("[blue]auth[/blue] - Authentication and authorization commands")
    msgraph_node = auth_node.add("[cyan]msgraph[/cyan] - Microsoft Graph authentication")
    msgraph_node.add("[yellow]login[/yellow] - Login to Microsoft 365")
    msgraph_node.add("[yellow]logout[/yellow] - Logout from Microsoft 365")

    jobs_node = tree.add("[blue]jobs[/blue] - Background job management")
    jobs_node.add("[cyan]schedule[/cyan] - Schedule recurring archive jobs")
    jobs_node.add("[cyan]trigger[/cyan] - Trigger manual archive job")
    jobs_node.add("[cyan]remove[/cyan] - Remove scheduled jobs")
    jobs_node.add("[cyan]status[/cyan] - Get job status for user")
    jobs_node.add("[cyan]health[/cyan] - Job scheduler health check")

    prompt_node = tree.add("[blue]prompt[/blue] - Interactive prompt system")
    prompt_node.add("[cyan]run[/cyan] - Run interactive prompt")

    recover_node = tree.add("[blue]recover[/blue] - Recovery operations management")
    recover_node.add("[cyan]list[/cyan] - List reversible operations")
    recover_node.add("[cyan]show[/cyan] - Show operation details")
    recover_node.add("[cyan]reverse[/cyan] - Reverse a completed operation")

    tree.add("[blue]tree[/blue] - Show the full command tree structure")

    return tree

@app.command("tree")
def show_command_tree():
    """Show the full command tree structure."""
    console = Console()
    tree = build_command_tree()
    console.print(tree)


@app.callback()
def main(ctx: typer.Context):
    """Admin Assistant CLI: Manage calendars, archives, and timesheets for users.

    Use --help on any command for details and options.

    Examples:
      # Authentication
      admin-assistant auth msgraph login
      admin-assistant auth msgraph logout

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

      # Restoration operations
      admin-assistant calendar restore from-audit-logs --user <USER_ID> --start-date "2024-01-01"
      admin-assistant calendar restore from-backup-calendars --user <USER_ID> --source "Backup" --destination "Recovered"
      admin-assistant config calendar restore list --user <USER_ID>

      # Recovery operations (reversible operations)
      admin-assistant recover list --user <USER_ID>
      admin-assistant recover show <OPERATION_ID> --user <USER_ID>
      admin-assistant recover reverse <OPERATION_ID> --reason "Mistake" --user <USER_ID>

      # Command tree display
      admin-assistant tree

      # URI formats (new format with account context recommended)
      # New format: msgraph://user@example.com/calendars/primary
      # Legacy format: msgraph://calendars/primary (still supported)
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


# Import restoration app and recovery operations
from cli.recovery_operations import recovery_app
from cli.restoration import restoration_app

# Add restoration app to calendar app
calendar_app.add_typer(restoration_app, name="restore")

# Register main command apps
app.add_typer(category_app, name="category")
app.add_typer(calendar_app, name="calendar")
app.add_typer(config_app, name="config")
app.add_typer(auth_app, name="auth")
app.add_typer(jobs_app, name="jobs")
app.add_typer(interactive_prompt_app, name="prompt")
app.add_typer(recovery_app, name="recover")


if __name__ == "__main__":
    app()
