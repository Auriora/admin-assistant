"""Archive configuration management commands."""

from typing import Optional

import typer
import tzlocal
from rich.console import Console
from rich.table import Table

from cli.common.options import user_option
from cli.common.utils import (
    resolve_cli_user,
    get_account_context_for_user,
    suggest_uri_with_account_context,
    validate_uri_account_context,
    get_uri_autocompletion_suggestions,
)

archive_config_app = typer.Typer(help="Archive configuration management")


@archive_config_app.command("list")
def list_configs(user_input: Optional[str] = user_option):
    """List all archive configurations for a user."""
    from core.services.archive_configuration_service import ArchiveConfigurationService

    try:
        # Get user
        user = resolve_cli_user(user_input)

        service = ArchiveConfigurationService()
        configs = service.list_for_user(user.id)
        console = Console()
        if not configs:
            console.print(
                f"[yellow]No archive configurations found for user {user.id} ({user.username or user.email}).[/yellow]"
            )
            return
        table = Table(
            title=f"Archive Configurations for user {user.id} ({user.username or user.email})"
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
        console.print(f"[red]Error listing archive configurations: {e}[/red]")
        raise typer.Exit(code=1)


def _get_uri_autocompletion(user_input: Optional[str] = None):
    """Get URI auto-completion suggestions based on resolved user."""
    try:
        user = resolve_cli_user(user_input)
        return get_uri_autocompletion_suggestions(user)
    except:
        # Fallback suggestions if user resolution fails
        return [
            "msgraph://calendars/primary",
            "msgraph://calendars/\"Archive Calendar\"",
            "local://calendars/primary",
        ]


@archive_config_app.command("create")
def create_config(
    user_input: Optional[str] = user_option,
    name: str = typer.Option(None, "--name", help="Name for the archive configuration"),
    source_calendar_uri: str = typer.Option(
        None,
        "--source-uri",
        help="Source calendar URI (e.g., msgraph://user@example.com/calendars/primary)",
        autocompletion=lambda: _get_uri_autocompletion()
    ),
    destination_calendar_uri: str = typer.Option(
        None,
        "--dest-uri",
        help="Destination (archive) calendar URI (e.g., msgraph://user@example.com/calendars/\"Archive Calendar\")",
        autocompletion=lambda: _get_uri_autocompletion()
    ),
    timezone: str = typer.Option(
        None, "--timezone", help="Timezone (IANA format, e.g., Europe/London)"
    ),
    is_active: bool = typer.Option(
        True, "--active/--inactive", help="Whether this config is active"
    ),
):
    """Create a new archive configuration for a user."""
    from core.models.archive_configuration import ArchiveConfiguration
    from core.services.archive_configuration_service import ArchiveConfigurationService

    console = Console()

    try:
        # Get user
        user = resolve_cli_user(user_input)
        account_context = get_account_context_for_user(user)

        # Get system timezone
        system_timezone = tzlocal.get_localzone_name()

        # Prompt for missing fields with enhanced examples
        if not name:
            name = typer.prompt("Name for the archive configuration")

        if not source_calendar_uri:
            console.print(f"\n[blue]Examples for source calendar URI:[/blue]")
            console.print(f"  msgraph://{account_context}/calendars/primary")
            console.print(f"  msgraph://{account_context}/calendars/\"Work Calendar\"")
            console.print(f"  msgraph://calendars/primary (legacy format)")
            source_calendar_uri = typer.prompt(
                "Source calendar URI"
            )

        if not destination_calendar_uri:
            console.print(f"\n[blue]Examples for destination calendar URI:[/blue]")
            console.print(f"  msgraph://{account_context}/calendars/\"Archive Calendar\"")
            console.print(f"  local://{account_context}/calendars/\"Local Archive\"")
            console.print(f"  msgraph://calendars/\"Archive Calendar\" (legacy format)")
            destination_calendar_uri = typer.prompt(
                "Destination (archive) calendar URI"
            )

        if not timezone:
            timezone = typer.prompt(
                "Timezone (IANA format, e.g., Europe/London)", default=system_timezone
            )

        # Validate URIs and provide suggestions
        source_valid, source_error = validate_uri_account_context(source_calendar_uri, user)
        if not source_valid:
            console.print(f"[yellow]Warning - Source URI: {source_error}[/yellow]")
            suggested_source = suggest_uri_with_account_context(source_calendar_uri, user)
            if suggested_source != source_calendar_uri:
                console.print(f"[blue]Suggested format: {suggested_source}[/blue]")
                if typer.confirm("Use suggested format?"):
                    source_calendar_uri = suggested_source

        dest_valid, dest_error = validate_uri_account_context(destination_calendar_uri, user)
        if not dest_valid:
            console.print(f"[yellow]Warning - Destination URI: {dest_error}[/yellow]")
            suggested_dest = suggest_uri_with_account_context(destination_calendar_uri, user)
            if suggested_dest != destination_calendar_uri:
                console.print(f"[blue]Suggested format: {suggested_dest}[/blue]")
                if typer.confirm("Use suggested format?"):
                    destination_calendar_uri = suggested_dest
        config = ArchiveConfiguration(
            user_id=user.id,
            name=name,
            source_calendar_uri=source_calendar_uri,
            destination_calendar_uri=destination_calendar_uri,
            is_active=is_active,
            timezone=timezone,
        )
        service = ArchiveConfigurationService()
        service.create(config)

        console.print(f"[green]✓ Created archive configuration: {config.name}[/green]")
        console.print(f"  ID: {config.id}")
        console.print(f"  Source: {config.source_calendar_uri}")
        console.print(f"  Destination: {config.destination_calendar_uri}")
        console.print(f"  Active: {config.is_active}")
        console.print(f"  Timezone: {config.timezone}")

    except Exception as e:
        console.print(f"[red]Failed to create archive configuration: {e}[/red]")
        raise typer.Exit(code=1)


@archive_config_app.command("set-default")
def set_default_config(
    user_input: Optional[str] = user_option,
    config_id: int = typer.Option(
        ..., "--config-id", help="ID of the config to set as default"
    ),
):
    """Set a config as the default for a user (prints instructions if persistent storage is not available)."""
    typer.echo(
        f"To use this config as default, use --archive-config {config_id} in archive commands."
    )
    typer.echo(
        "(Persistent default config storage is not implemented in this CLI. Consider scripting this or request a feature update.)"
    )


@archive_config_app.command("activate")
def activate_config(
    user_input: Optional[str] = user_option,
    config_id: int = typer.Option(
        ..., "--config-id", help="ID of the config to activate"
    ),
):
    """Activate an archive configuration (set is_active=True)."""
    from core.services.archive_configuration_service import ArchiveConfigurationService

    try:
        # Get user
        user = resolve_cli_user(user_input)

        service = ArchiveConfigurationService()
        config = service.get_by_id(config_id)
        if not config or getattr(config, "user_id", None) != user.id:
            typer.echo(
                f"Config {config_id} not found for user {user.id} ({user.username or user.email})."
            )
            raise typer.Exit(code=1)
        setattr(config, "is_active", True)
        service.update(config)
        typer.echo(f"Config {config_id} activated.")
    except Exception as e:
        typer.echo(f"Failed to activate config: {e}")
        raise typer.Exit(code=1)


@archive_config_app.command("deactivate")
def deactivate_config(
    user_input: Optional[str] = user_option,
    config_id: int = typer.Option(
        ..., "--config-id", help="ID of the config to deactivate"
    ),
):
    """Deactivate an archive configuration (set is_active=False)."""
    from core.services.archive_configuration_service import ArchiveConfigurationService

    try:
        # Get user
        user = resolve_cli_user(user_input)

        service = ArchiveConfigurationService()
        config = service.get_by_id(config_id)
        if not config or getattr(config, "user_id", None) != user.id:
            typer.echo(
                f"Config {config_id} not found for user {user.id} ({user.username or user.email})."
            )
            raise typer.Exit(code=1)
        setattr(config, "is_active", False)
        service.update(config)
        typer.echo(f"Config {config_id} deactivated.")
    except Exception as e:
        typer.echo(f"Failed to deactivate config: {e}")
        raise typer.Exit(code=1)


@archive_config_app.command("delete")
def delete_config(
    user_input: Optional[str] = user_option,
    config_id: int = typer.Option(
        ..., "--config-id", help="ID of the config to delete"
    ),
):
    """Delete an archive configuration by ID."""
    from core.services.archive_configuration_service import ArchiveConfigurationService

    try:
        # Get user
        user = resolve_cli_user(user_input)

        service = ArchiveConfigurationService()
        config = service.get_by_id(config_id)
        if not config or getattr(config, "user_id", None) != user.id:
            typer.echo(
                f"Config {config_id} not found for user {user.id} ({user.username or user.email})."
            )
            raise typer.Exit(code=1)
        service.delete(config_id)
        typer.echo(f"Config {config_id} deleted.")
    except Exception as e:
        typer.echo(f"Failed to delete config: {e}")
        raise typer.Exit(code=1)
