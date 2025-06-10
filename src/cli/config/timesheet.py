"""Timesheet configuration management commands."""

from typing import Optional

import typer
import tzlocal
from rich.console import Console
from rich.table import Table

from cli.common.options import user_option
from cli.common.utils import resolve_cli_user

timesheet_config_app = typer.Typer(help="Timesheet configuration management")


@timesheet_config_app.command("list")
def list_timesheet_configs(user_input: Optional[str] = user_option):
    """List all timesheet configurations for a user."""
    from core.services.archive_configuration_service import ArchiveConfigurationService

    try:
        # Get user
        user = resolve_cli_user(user_input)

        service = ArchiveConfigurationService()
        # Filter for timesheet configurations only
        all_configs = service.list_for_user(user.id)
        configs = [c for c in all_configs if getattr(c, 'archive_purpose', 'general') == 'timesheet']
        
        console = Console()
        if not configs:
            console.print(
                f"[yellow]No timesheet configurations found for user {user.id} ({user.username or user.email}).[/yellow]"
            )
            return
        table = Table(
            title=f"Timesheet Configurations for user {user.id} ({user.username or user.email})"
        )
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Source", style="magenta")
        table.add_column("Dest", style="magenta")
        table.add_column("Active", style="yellow")
        table.add_column("TZ", style="blue")
        for c in configs:
            table.add_row(
                str(getattr(c, "id", "")),
                str(getattr(c, "name", "")),
                str(getattr(c, "source_calendar_uri", "")),
                str(getattr(c, "destination_calendar_uri", "")),
                "✔" if getattr(c, "is_active", False) else "✗",
                str(getattr(c, "timezone", "")),
            )
        console.print(table)
    except Exception as e:
        console = Console()
        console.print(f"[red]Error listing timesheet configurations: {e}[/red]")
        raise typer.Exit(code=1)


@timesheet_config_app.command("create")
def create_timesheet_config(
    user_input: Optional[str] = user_option,
    name: str = typer.Option(None, "--name", help="Name for the timesheet configuration"),
    source_calendar_uri: str = typer.Option(
        None, "--source-uri", help="Source calendar URI (e.g., msgraph://id)"
    ),
    destination_calendar_uri: str = typer.Option(
        None,
        "--dest-uri",
        help="Destination (timesheet) calendar URI (e.g., msgraph://id)",
    ),
    timezone: str = typer.Option(
        None, "--timezone", help="Timezone (IANA format, e.g., Europe/London)"
    ),
    is_active: bool = typer.Option(
        True, "--active/--inactive", help="Whether this config is active"
    ),
):
    """Create a new timesheet configuration for a user.
    
    Timesheet configurations are specialized archive configurations that filter appointments
    for business categories (billable, non-billable, travel) and exclude personal appointments.
    """
    from core.models.archive_configuration import ArchiveConfiguration
    from core.services.archive_configuration_service import ArchiveConfigurationService

    try:
        # Get user
        user = resolve_cli_user(user_input)

        # Get system timezone
        system_timezone = tzlocal.get_localzone_name()
        # Prompt for missing fields
        if not name:
            name = typer.prompt("Name for the timesheet configuration")
        if not source_calendar_uri:
            source_calendar_uri = typer.prompt(
                "Source calendar URI (e.g., msgraph://id)"
            )
        if not destination_calendar_uri:
            destination_calendar_uri = typer.prompt(
                "Destination (timesheet) calendar URI (e.g., msgraph://id)"
            )
        if not timezone:
            timezone = typer.prompt(
                "Timezone (IANA format, e.g., Europe/London)", default=system_timezone
            )
        config = ArchiveConfiguration(
            user_id=user.id,
            name=name,
            source_calendar_uri=source_calendar_uri,
            destination_calendar_uri=destination_calendar_uri,
            is_active=is_active,
            timezone=timezone,
            archive_purpose='timesheet',  # Set timesheet purpose
            allow_overlaps=False,  # Timesheet configs typically resolve overlaps
        )
        service = ArchiveConfigurationService()
        service.create(config)
        typer.echo(f"Created timesheet configuration: {config}")
        typer.echo("[blue]This configuration will filter appointments for business categories only.[/blue]")
    except Exception as e:
        typer.echo(f"Failed to create timesheet configuration: {e}")
        raise typer.Exit(code=1)


@timesheet_config_app.command("set-default")
def set_default_timesheet_config(
    user_input: Optional[str] = user_option,
    config_id: int = typer.Option(
        ..., "--config-id", help="ID of the timesheet config to set as default"
    ),
):
    """Set a timesheet config as the default for a user (prints instructions if persistent storage is not available)."""
    typer.echo(
        f"To use this timesheet config as default, use --timesheet-config {config_id} in timesheet commands."
    )
    typer.echo(
        "(Persistent default config storage is not implemented in this CLI. Consider scripting this or request a feature update.)"
    )


@timesheet_config_app.command("activate")
def activate_timesheet_config(
    user_input: Optional[str] = user_option,
    config_id: int = typer.Option(
        ..., "--config-id", help="ID of the timesheet config to activate"
    ),
):
    """Activate a timesheet configuration (set is_active=True)."""
    from core.services.archive_configuration_service import ArchiveConfigurationService

    try:
        # Get user
        user = resolve_cli_user(user_input)

        service = ArchiveConfigurationService()
        config = service.get_by_id(config_id)
        if not config or getattr(config, "user_id", None) != user.id:
            typer.echo(
                f"Timesheet config {config_id} not found for user {user.id} ({user.username or user.email})."
            )
            raise typer.Exit(code=1)

        # Verify this is a timesheet configuration
        if getattr(config, 'archive_purpose', 'general') != 'timesheet':
            typer.echo(f"[red]Config {config_id} is not a timesheet configuration (purpose: {getattr(config, 'archive_purpose', 'general')}).[/red]")
            raise typer.Exit(code=1)

        setattr(config, "is_active", True)
        service.update(config)
        typer.echo(f"Timesheet config {config_id} activated.")
    except Exception as e:
        typer.echo(f"Failed to activate timesheet config: {e}")
        raise typer.Exit(code=1)


@timesheet_config_app.command("deactivate")
def deactivate_timesheet_config(
    user_input: Optional[str] = user_option,
    config_id: int = typer.Option(
        ..., "--config-id", help="ID of the timesheet config to deactivate"
    ),
):
    """Deactivate a timesheet configuration (set is_active=False)."""
    from core.services.archive_configuration_service import ArchiveConfigurationService

    try:
        # Get user
        user = resolve_cli_user(user_input)

        service = ArchiveConfigurationService()
        config = service.get_by_id(config_id)
        if not config or getattr(config, "user_id", None) != user.id:
            typer.echo(
                f"Timesheet config {config_id} not found for user {user.id} ({user.username or user.email})."
            )
            raise typer.Exit(code=1)

        # Verify this is a timesheet configuration
        if getattr(config, 'archive_purpose', 'general') != 'timesheet':
            typer.echo(f"[red]Config {config_id} is not a timesheet configuration (purpose: {getattr(config, 'archive_purpose', 'general')}).[/red]")
            raise typer.Exit(code=1)

        setattr(config, "is_active", False)
        service.update(config)
        typer.echo(f"Timesheet config {config_id} deactivated.")
    except Exception as e:
        typer.echo(f"Failed to deactivate timesheet config: {e}")
        raise typer.Exit(code=1)


@timesheet_config_app.command("delete")
def delete_timesheet_config(
    user_input: Optional[str] = user_option,
    config_id: int = typer.Option(
        ..., "--config-id", help="ID of the timesheet config to delete"
    ),
):
    """Delete a timesheet configuration by ID."""
    from core.services.archive_configuration_service import ArchiveConfigurationService

    try:
        # Get user
        user = resolve_cli_user(user_input)

        service = ArchiveConfigurationService()
        config = service.get_by_id(config_id)
        if not config or getattr(config, "user_id", None) != user.id:
            typer.echo(
                f"Timesheet config {config_id} not found for user {user.id} ({user.username or user.email})."
            )
            raise typer.Exit(code=1)

        # Verify this is a timesheet configuration
        if getattr(config, 'archive_purpose', 'general') != 'timesheet':
            typer.echo(f"[red]Config {config_id} is not a timesheet configuration (purpose: {getattr(config, 'archive_purpose', 'general')}).[/red]")
            raise typer.Exit(code=1)

        service.delete(config_id)
        typer.echo(f"Timesheet config {config_id} deleted.")
    except Exception as e:
        typer.echo(f"Failed to delete timesheet config: {e}")
        raise typer.Exit(code=1)
