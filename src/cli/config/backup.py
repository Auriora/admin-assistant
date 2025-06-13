"""Backup configuration management commands."""

from typing import Optional

import typer
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

backup_config_app = typer.Typer(help="Backup configuration management", rich_markup_mode="rich")


@backup_config_app.callback()
def backup_config_callback(ctx: typer.Context):
    """Backup configuration management commands.

    Manage backup configurations for calendar operations.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@backup_config_app.command("list")
def list_backup_configs(user_input: Optional[str] = user_option):
    """List all backup configurations for a user."""
    from core.services.backup_configuration_service import BackupConfigurationService

    console = Console()

    try:
        user = resolve_cli_user(user_input)

        backup_service = BackupConfigurationService()
        configs = backup_service.list(user_id=user.id)

        if not configs:
            console.print(f"[yellow]No backup configurations found for user {user.id} ({user.username or user.email})[/yellow]")
            return

        table = Table(title=f"Backup Configurations for {user.username or user.email}")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Source URI", style="blue")
        table.add_column("Destination URI", style="blue")
        table.add_column("Format", style="yellow")
        table.add_column("Active", style="red")

        for config in configs:
            table.add_row(
                str(config.id),
                config.name,
                config.source_calendar_uri,
                config.destination_uri,
                config.backup_format,
                "✓" if config.is_active else "✗"
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing backup configurations: {e}[/red]")
        raise typer.Exit(code=1)


@backup_config_app.command("create")
def create_backup_config(
    user_input: Optional[str] = user_option,
    name: str = typer.Option(None, "--name", help="Name for the backup configuration"),
    source_calendar_uri: str = typer.Option(
        None, "--source-uri", help="Source calendar URI (e.g., msgraph://user@example.com/calendars/\"Work Calendar\")"
    ),
    destination_uri: str = typer.Option(
        None, "--destination-uri", help="Destination URI (e.g., file:///backups/work.csv, local://user@example.com/calendars/Backup)"
    ),
    backup_format: str = typer.Option("csv", "--format", help="Backup format: csv, json, ics, local_calendar"),
    include_metadata: bool = typer.Option(True, "--metadata/--no-metadata", help="Include metadata in backup"),
    timezone: str = typer.Option("UTC", "--timezone", help="Timezone for backup operations"),
):
    """Create a new backup configuration."""
    from core.services.backup_configuration_service import BackupConfigurationService

    console = Console()

    try:
        user = resolve_cli_user(user_input)
        account_context = get_account_context_for_user(user)

        # Prompt for missing fields with enhanced examples
        if not name:
            name = typer.prompt("Backup configuration name")

        if not source_calendar_uri:
            console.print(f"\n[blue]Examples for source calendar URI:[/blue]")
            console.print(f"  msgraph://{account_context}/calendars/primary")
            console.print(f"  msgraph://{account_context}/calendars/\"Work Calendar\"")
            console.print(f"  msgraph://calendars/primary (legacy format)")
            source_calendar_uri = typer.prompt("Source calendar URI")

        if not destination_uri:
            console.print(f"\n[blue]Examples for destination URI:[/blue]")
            console.print(f"  file:///backups/work.csv")
            console.print(f"  local://{account_context}/calendars/\"Backup Calendar\"")
            console.print(f"  file:///home/user/backups/calendar.json")
            destination_uri = typer.prompt("Destination URI")

        # Validate source URI and provide suggestions
        source_valid, source_error = validate_uri_account_context(source_calendar_uri, user)
        if not source_valid:
            console.print(f"[yellow]Warning - Source URI: {source_error}[/yellow]")
            suggested_source = suggest_uri_with_account_context(source_calendar_uri, user)
            if suggested_source != source_calendar_uri:
                console.print(f"[blue]Suggested format: {suggested_source}[/blue]")
                if typer.confirm("Use suggested format?"):
                    source_calendar_uri = suggested_source

        backup_service = BackupConfigurationService()
        backup_config = backup_service.create_from_parameters(
            user_id=user.id,
            name=name,
            source_calendar_uri=source_calendar_uri,
            destination_uri=destination_uri,
            backup_format=backup_format,
            include_metadata=include_metadata,
            timezone=timezone,
        )

        console.print(f"[green]Backup configuration '{name}' created successfully with ID {backup_config.id}[/green]")

    except Exception as e:
        console.print(f"[red]Failed to create backup configuration: {e}[/red]")
        raise typer.Exit(code=1)
