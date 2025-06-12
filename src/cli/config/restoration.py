"""
Restoration configuration management commands.
"""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from cli.common.options import user_option
from cli.common.utils import resolve_cli_user
from core.services.appointment_restoration_service import AppointmentRestorationService

# Create console for rich output
console = Console()

# Create the restoration config app
restoration_config_app = typer.Typer(help="Restoration configuration management", rich_markup_mode="rich")


@restoration_config_app.command("list")
def list_configs(
    user_input: Optional[str] = user_option,
):
    """List restoration configurations."""
    console.print(Panel.fit(
        "[bold blue]Restoration Configurations[/bold blue]",
        border_style="blue"
    ))

    try:
        # Get user
        user = resolve_cli_user(user_input)

        service = AppointmentRestorationService(user_id=user.id)
        configurations = service.list_configurations()

        if not configurations:
            console.print(f"[yellow]No restoration configurations found for user {user.id} ({user.username or user.email}).[/yellow]")
            return

        console.print(f"Found [cyan]{len(configurations)}[/cyan] configuration(s):\n")

        table = Table()
        table.add_column("ID", style="cyan", width=8)
        table.add_column("Name", style="green", width=25)
        table.add_column("Source", style="blue", width=15)
        table.add_column("Destination", style="blue", width=15)
        table.add_column("Status", style="yellow", width=10)
        table.add_column("Created", style="white", width=12)

        for config in configurations:
            status = "[green]ACTIVE[/green]" if config.is_active else "[red]INACTIVE[/red]"
            created = config.created_at.strftime("%Y-%m-%d") if config.created_at else "Unknown"

            table.add_row(
                str(config.id),
                config.name,
                config.source_type.replace('_', ' ').title(),
                config.destination_type.replace('_', ' ').title(),
                status,
                created
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing configurations: {e}[/red]")
        raise typer.Exit(code=1)
