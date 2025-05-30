"""
Admin Assistant CLI
==================

Usage Examples:
---------------
# List all archive configs for a user
admin-assistant config calendar archive config list --user <USER_ID>

# Create a new archive config (interactive prompts for missing fields)
admin-assistant config calendar archive config create --user <USER_ID>

# Create a new archive config (all options provided)
admin-assistant config calendar archive config create --user <USER_ID> --name "Work Archive" --source-uri "msgraph://source" --dest-uri "msgraph://dest" --timezone "Europe/London" --active

# Activate/deactivate/delete a config
admin-assistant config calendar archive config activate --user <USER_ID> --config-id <CONFIG_ID>
admin-assistant config calendar archive config deactivate --user <USER_ID> --config-id <CONFIG_ID>
admin-assistant config calendar archive config delete --user <USER_ID> --config-id <CONFIG_ID>

# Set a config as default (prints usage instructions)
admin-assistant config calendar archive config set-default --user <USER_ID> --config-id <CONFIG_ID>

# Archive calendar events using a specific config
admin-assistant config calendar archive archive --user <USER_ID> --archive-config <CONFIG_ID> --date "last 7 days"

All commands support --help for detailed options and descriptions.

Extending the CLI:
------------------
- To add new calendar or archive features, add commands to the appropriate Typer app (calendar_app, archive_app, archive_config_app).
- Integrate with core services by importing from core.services or core.orchestrators as needed.
- Use interactive prompts for user-friendly CLI, and provide all options for automation/scripting.
"""
import typer
from datetime import datetime, timedelta, date
from core.orchestrators.archive_job_runner import ArchiveJobRunner
from core.utilities import get_graph_client
from core.db import get_session
import re

app = typer.Typer(help="Admin Assistant CLI for running calendar and timesheet operations.")
calendar_app = typer.Typer(help="Calendar operations")
timesheet_app = typer.Typer(help="Timesheet operations")
archive_app = typer.Typer(help="Archive operations")
config_app = typer.Typer(help="Configuration operations")
archive_config_app = typer.Typer(help="Calendar configuration operations")
archive_archive_config_app = typer.Typer(help="Archive configuration management")

user_id_option = typer.Option(
    ...,
    "--user",
    help="User to operate on.",
    envvar="ADMIN_ASSISTANT_USER",
    show_default=False,
)

def parse_flexible_date(date_str: str) -> date:
    """
    Parses a flexible date string and returns a date object.

    Supported formats:
    - 'today', 'yesterday'
    - day-month-year (e.g., 31-12-2024, 31-Dec-2024, 31-12, 31-Dec)
      - Month can be numeric or a name (short or long form)
      - Year is optional (defaults to the current year)

    Returns:
        date: The parsed date object.

    Raises:
        ValueError: If the input string cannot be parsed as a date.
    """
    if not date_str or date_str.lower() == "yesterday":
        return datetime.now().date() - timedelta(days=1)
    if date_str.lower() == "today":
        return datetime.now().date()
    # Try day-month-year or day-month
    date_str = date_str.strip()
    # Accept separators: -, /, . or space
    pattern = r"^(\d{1,2})[\-/. ]([A-Za-z]+|\d{1,2})(?:[\-/. ](\d{2,4}))?$"
    m = re.match(pattern, date_str)
    if m:
        day = int(m.group(1))
        month = m.group(2)
        year = m.group(3)
        # Convert month
        try:
            month_num = int(month)
        except ValueError:
            try:
                month_num = datetime.strptime(month[:3], "%b").month
            except ValueError:
                month_num = datetime.strptime(month, "%B").month
        # Year
        if year:
            year = int(year)
            if year < 100:
                year += 2000
        else:
            year = datetime.now().year
        return date(year, month_num, day)
    # Try ISO format
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        pass
    raise ValueError(f"Unrecognized date format: {date_str}")

def parse_date_range(date_str: str) -> tuple[date, date]:
    """
    Parse a flexible date range string. Supports:
    - Phrases: today, yesterday, last 7 days, last week, last 30 days, last month
    - Single date (day-month[-year], month as number or name, year optional)
    - Date range: <date> to <date>, <date> - <date>, <day> to <date>, <day> - <date>
    Returns (start_date, end_date) as date objects.
    """
    date_str = (date_str or "yesterday").strip().lower()
    now = datetime.now().date()
    # Phrases
    if date_str in ("today",):
        return now, now
    if date_str in ("yesterday",):
        yest = now - timedelta(days=1)
        return yest, yest
    if date_str in ("last 7 days", "last week"):
        end = now
        start = now - timedelta(days=6)
        return start, end
    if date_str in ("last 30 days", "last month"):
        end = now
        start = now - timedelta(days=29)
        return start, end
    # Range: <date> to <date> or <date> - <date>
    range_match = re.match(r"(.+?)(?:\s*(?:to|-)\s*)(.+)", date_str)
    if range_match:
        start_str, end_str = range_match.group(1).strip(), range_match.group(2).strip()
        start = parse_flexible_date(start_str)
        end = parse_flexible_date(end_str)
        return start, end
    # Single date
    single = parse_flexible_date(date_str)
    return single, single

@app.callback()
def main(ctx: typer.Context):
    """Admin Assistant CLI: Manage calendars, archives, and timesheets for users.

Use --help on any command for details and options.

Examples:
  admin-assistant config calendar archive config list --user <USER_ID>
  admin-assistant config calendar archive config create --user <USER_ID>
  admin-assistant config calendar archive config activate --user <USER_ID> --config-id <CONFIG_ID>
  admin-assistant config calendar archive archive --user <USER_ID> --archive-config <CONFIG_ID> --date "last 7 days"
"""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())

@archive_app.command("archive")
def archive(
    date_option: str = typer.Option(
        "yesterday",
        "--date",
        help="Date or date range. Accepts: 'today', 'yesterday', 'last 7 days', 'last week', 'last 30 days', 'last month', a single date (e.g. 31-12-2024, 31-Dec, 31-12), or a range (e.g. 1-6 to 7-6, 1-6-2024 - 7-6-2024)"
    ),
    user_id: int = user_id_option,
    archive_config_id: int = typer.Option(..., "--archive-config", help="Archive configuration to use.", show_default=False)
):
    """Manually trigger calendar archiving for the configured user and archive configuration."""
    runner = ArchiveJobRunner()
    session = get_session()
    try:
        start_dt, end_dt = parse_date_range(date_option)
    except Exception as e:
        typer.echo(f"Error parsing date: {e}")
        raise typer.Exit(code=1)
    try:
        from core.services import UserService
        user_service = UserService()
        user = user_service.get_by_id(user_id)
        if not user:
            typer.echo(f"No user found in user DB for user_id={user_id}.")
            raise typer.Exit(code=1)
        graph_client = get_graph_client(user=user, session=session)
        # If only one date is present, set both to the same value
        if start_dt and not end_dt:
            end_dt = start_dt
        if end_dt and not start_dt:
            start_dt = end_dt
        result = runner.run_archive_job(
            user_id=user_id,
            archive_config_id=archive_config_id,
            start_date=start_dt,
            end_date=end_dt
        )
    except Exception as e:
        typer.echo(f"Archiving failed: {e}")
        raise typer.Exit(code=1)
    typer.echo("[ARCHIVE RESULT]")
    typer.echo(result)

@calendar_app.command("travel")
def travel_auto_plan():
    """Auto-plan travel."""
    typer.echo("Auto-planning travel...")

@archive_archive_config_app.command("list")
def list_configs(user_id: int = user_id_option):
    """List all archive configurations for a user."""
    from core.services.archive_configuration_service import ArchiveConfigurationService
    service = ArchiveConfigurationService()
    configs = service.list_for_user(user_id)
    if not configs:
        typer.echo(f"No archive configurations found for user_id={user_id}.")
        raise typer.Exit(code=0)
    typer.echo(f"Archive Configurations for user_id={user_id}:")
    for c in configs:
        typer.echo(f"ID: {getattr(c, 'id', None)} | Name: {getattr(c, 'name', None)} | Source: {getattr(c, 'source_calendar_uri', None)} | Dest: {getattr(c, 'destination_calendar_uri', None)} | Active: {getattr(c, 'is_active', None)} | TZ: {getattr(c, 'timezone', None)}")

@archive_archive_config_app.command("create")
def create_config(
    user_id: int = user_id_option,
    name: str = typer.Option(None, "--name", help="Name for the archive configuration"),
    source_calendar_uri: str = typer.Option(None, "--source-uri", help="Source calendar URI (e.g., msgraph://id)"),
    destination_calendar_uri: str = typer.Option(None, "--dest-uri", help="Destination (archive) calendar URI (e.g., msgraph://id)"),
    timezone: str = typer.Option(None, "--timezone", help="Timezone (IANA format, e.g., Europe/London)"),
    is_active: bool = typer.Option(True, "--active/--inactive", help="Whether this config is active")
):
    """Create a new archive configuration for a user."""
    from core.models.archive_configuration import ArchiveConfiguration
    from core.services.archive_configuration_service import ArchiveConfigurationService
    # Prompt for missing fields
    if not name:
        name = typer.prompt("Name for the archive configuration")
    if not source_calendar_uri:
        source_calendar_uri = typer.prompt("Source calendar URI (e.g., msgraph://id)")
    if not destination_calendar_uri:
        destination_calendar_uri = typer.prompt("Destination (archive) calendar URI (e.g., msgraph://id)")
    if not timezone:
        timezone = typer.prompt("Timezone (IANA format, e.g., Europe/London)")
    config = ArchiveConfiguration(
        user_id=user_id,
        name=name,
        source_calendar_uri=source_calendar_uri,
        destination_calendar_uri=destination_calendar_uri,
        is_active=is_active,
        timezone=timezone
    )
    service = ArchiveConfigurationService()
    try:
        service.create(config)
        typer.echo(f"Created archive configuration: {config}")
    except Exception as e:
        typer.echo(f"Failed to create archive configuration: {e}")
        raise typer.Exit(code=1)

@archive_archive_config_app.command("set-default")
def set_default_config(
    user_id: int = user_id_option,
    config_id: int = typer.Option(..., "--config-id", help="ID of the config to set as default")
):
    """Set a config as the default for a user (prints instructions if persistent storage is not available)."""
    typer.echo(f"To use this config as default, use --archive-config {config_id} in archive commands.")
    typer.echo("(Persistent default config storage is not implemented in this CLI. Consider scripting this or request a feature update.)")

@archive_archive_config_app.command("activate")
def activate_config(
    user_id: int = user_id_option,
    config_id: int = typer.Option(..., "--config-id", help="ID of the config to activate")
):
    """Activate an archive configuration (set is_active=True)."""
    from core.services.archive_configuration_service import ArchiveConfigurationService
    service = ArchiveConfigurationService()
    config = service.get_by_id(config_id)
    if not config or getattr(config, 'user_id', None) != user_id:
        typer.echo(f"Config {config_id} not found for user {user_id}.")
        raise typer.Exit(code=1)
    setattr(config, 'is_active', True)
    service.update(config)
    typer.echo(f"Config {config_id} activated.")

@archive_archive_config_app.command("deactivate")
def deactivate_config(
    user_id: int = user_id_option,
    config_id: int = typer.Option(..., "--config-id", help="ID of the config to deactivate")
):
    """Deactivate an archive configuration (set is_active=False)."""
    from core.services.archive_configuration_service import ArchiveConfigurationService
    service = ArchiveConfigurationService()
    config = service.get_by_id(config_id)
    if not config or getattr(config, 'user_id', None) != user_id:
        typer.echo(f"Config {config_id} not found for user {user_id}.")
        raise typer.Exit(code=1)
    setattr(config, 'is_active', False)
    service.update(config)
    typer.echo(f"Config {config_id} deactivated.")

@archive_archive_config_app.command("delete")
def delete_config(
    user_id: int = user_id_option,
    config_id: int = typer.Option(..., "--config-id", help="ID of the config to delete")
):
    """Delete an archive configuration by ID."""
    from core.services.archive_configuration_service import ArchiveConfigurationService
    service = ArchiveConfigurationService()
    config = service.get_by_id(config_id)
    if not config or getattr(config, 'user_id', None) != user_id:
        typer.echo(f"Config {config_id} not found for user {user_id}.")
        raise typer.Exit(code=1)
    service.delete(config_id)
    typer.echo(f"Config {config_id} deleted.")

archive_config_app.add_typer(archive_archive_config_app, name="archive")
config_app.add_typer(archive_config_app, name="calendar")

timesheet_app.add_typer(timesheet_app, name="timesheet")

@timesheet_app.command("export")
def export(
    output: str = typer.Option("PDF", "--output", "-o", help="Output format: PDF or CSV"),
    user_id: int = user_id_option
):
    """Export timesheet data."""
    typer.echo(f"Exporting timesheet as {output} for user {user_id}")

@timesheet_app.command("upload")
def upload(
    destination: str = typer.Option(..., help="Upload destination (e.g., Xero)"),
    user_id: int = user_id_option
):
    """Upload timesheet."""
    typer.echo(f"Uploading timesheet to {destination} for user {user_id}")

app.add_typer(calendar_app, name="calendar")
app.add_typer(config_app, name="config")

if __name__ == "__main__":
    app() 
