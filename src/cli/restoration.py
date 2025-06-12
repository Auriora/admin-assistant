"""
Restoration CLI commands for the admin-assistant.

This module provides CLI commands for appointment restoration operations,
including restoring from audit logs, backup calendars, and managing
restoration configurations.
"""

from datetime import date, datetime
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.services.appointment_restoration_service import AppointmentRestorationService
from core.services.calendar_backup_service import CalendarBackupService, BackupFormat
from core.models.restoration_configuration import RestorationType, DestinationType

# Create the restoration app
restoration_app = typer.Typer(help="Appointment restoration operations", rich_markup_mode="rich")
console = Console()


def print_restoration_summary(result: dict):
    """Print a formatted summary of restoration results."""
    console.print("\n" + "=" * 60)
    console.print("[bold blue]RESTORATION SUMMARY[/bold blue]")
    console.print("=" * 60)

    # Create summary table
    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Count", style="green", width=10)

    table.add_row("Total found:", str(result.get('total_found', 0)))
    table.add_row("Restored:", str(result.get('restored', 0)))
    table.add_row("Failed:", str(result.get('failed', 0)))
    table.add_row("Skipped:", str(result.get('skipped', 0)))

    console.print(table)

    # Show errors if any
    errors = result.get('errors', [])
    if errors:
        console.print(f"\n[red]Errors ({len(errors)}):[/red]")
        for i, error in enumerate(errors[:5], 1):  # Show first 5 errors
            console.print(f"  {i}. {error}")
        if len(errors) > 5:
            console.print(f"  ... and {len(errors) - 5} more errors")

    # Show warnings if any
    warnings = result.get('warnings', [])
    if warnings:
        console.print(f"\n[yellow]Warnings ({len(warnings)}):[/yellow]")
        for i, warning in enumerate(warnings[:3], 1):  # Show first 3 warnings
            console.print(f"  {i}. {warning}")
        if len(warnings) > 3:
            console.print(f"  ... and {len(warnings) - 3} more warnings")

    console.print("=" * 60)


@restoration_app.command("from-audit-logs")
def restore_from_audit_logs(
    user_id: int = typer.Option(1, "--user", help="User ID to restore appointments for"),
    start_date: str = typer.Option("2025-05-29", "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD, default: today)"),
    destination_calendar: str = typer.Option("Recovered", "--destination", help="Destination calendar name"),
    action_types: List[str] = typer.Option(["archive", "restore"], "--action-types", help="Action types to restore from"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Perform analysis without actually restoring"),
):
    """Restore appointments from audit logs."""
    console.print(Panel.fit(
        "[bold blue]Restoring Appointments from Audit Logs[/bold blue]",
        border_style="blue"
    ))

    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    console.print(f"User ID: [cyan]{user_id}[/cyan]")
    console.print(f"Date range: [cyan]{start_date}[/cyan] to [cyan]{end_date}[/cyan]")
    console.print(f"Destination: [cyan]{destination_calendar}[/cyan]")
    console.print(f"Action types: [cyan]{', '.join(action_types)}[/cyan]")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No appointments will be actually restored[/yellow]")

    try:
        service = AppointmentRestorationService(user_id=user_id)

        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

        with console.status("[bold green]Processing restoration..."):
            result = service.restore_from_audit_logs(
                start_date=start_date_obj,
                end_date=end_date_obj,
                destination_calendar=destination_calendar,
                action_types=action_types,
                dry_run=dry_run
            )

        print_restoration_summary(result)

        if result['restored'] > 0 and not dry_run:
            console.print(f"\n[green]✓ Successfully restored {result['restored']} appointments![/green]")
            console.print(f"Check the '[cyan]{destination_calendar}[/cyan]' calendar for restored appointments.")
        elif dry_run and result['restored'] > 0:
            console.print(f"\n[blue]ℹ Would restore {result['restored']} appointments in actual run.[/blue]")

    except Exception as e:
        console.print(f"[red]Error during restoration: {e}[/red]")
        raise typer.Exit(code=1)


@restoration_app.command("from-backup-calendars")
def restore_from_backup_calendars(
    user_id: int = typer.Option(1, "--user", help="User ID to restore appointments for"),
    source_calendars: List[str] = typer.Option(..., "--source", help="Source calendar names"),
    destination_calendar: str = typer.Option(..., "--destination", help="Destination calendar name"),
    start_date: Optional[str] = typer.Option(None, "--start-date", help="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, "--end-date", help="End date filter (YYYY-MM-DD)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Perform analysis without actually restoring"),
):
    """Restore appointments from backup calendars."""
    console.print(Panel.fit(
        "[bold blue]Restoring Appointments from Backup Calendars[/bold blue]",
        border_style="blue"
    ))

    console.print(f"User ID: [cyan]{user_id}[/cyan]")
    console.print(f"Source calendars: [cyan]{', '.join(source_calendars)}[/cyan]")
    console.print(f"Destination: [cyan]{destination_calendar}[/cyan]")

    if start_date and end_date:
        console.print(f"Date filter: [cyan]{start_date}[/cyan] to [cyan]{end_date}[/cyan]")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No appointments will be actually restored[/yellow]")

    try:
        service = AppointmentRestorationService(user_id=user_id)

        start_date_obj = None
        end_date_obj = None
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

        with console.status("[bold green]Processing restoration..."):
            result = service.restore_from_backup_calendars(
                calendar_names=source_calendars,
                destination_calendar=destination_calendar,
                start_date=start_date_obj,
                end_date=end_date_obj,
                dry_run=dry_run
            )

        print_restoration_summary(result)

        if result['restored'] > 0 and not dry_run:
            console.print(f"\n[green]✓ Successfully restored {result['restored']} appointments![/green]")
            console.print(f"Check the '[cyan]{destination_calendar}[/cyan]' calendar for restored appointments.")
        elif dry_run and result['restored'] > 0:
            console.print(f"\n[blue]ℹ Would restore {result['restored']} appointments in actual run.[/blue]")

    except Exception as e:
        console.print(f"[red]Error during restoration: {e}[/red]")
        raise typer.Exit(code=1)


@restoration_app.command("backup-calendar")
def backup_calendar(
    user_id: int = typer.Option(1, "--user", help="User ID to backup calendar for"),
    source_calendar: str = typer.Option(..., "--source", help="Source calendar name"),
    backup_destination: str = typer.Option(..., "--destination", help="Backup destination (file path or calendar name)"),
    backup_format: str = typer.Option("csv", "--format", help="Backup format: csv, json, ics, local_calendar"),
    start_date: Optional[str] = typer.Option(None, "--start-date", help="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, "--end-date", help="End date filter (YYYY-MM-DD)"),
    include_metadata: bool = typer.Option(True, "--include-metadata/--no-metadata", help="Include metadata in backup"),
):
    """Backup a calendar to file or another calendar."""
    console.print(Panel.fit(
        "[bold blue]Backing Up Calendar[/bold blue]",
        border_style="blue"
    ))

    console.print(f"User ID: [cyan]{user_id}[/cyan]")
    console.print(f"Source calendar: [cyan]{source_calendar}[/cyan]")
    console.print(f"Destination: [cyan]{backup_destination}[/cyan]")
    console.print(f"Format: [cyan]{backup_format}[/cyan]")

    if start_date and end_date:
        console.print(f"Date filter: [cyan]{start_date}[/cyan] to [cyan]{end_date}[/cyan]")

    try:
        service = CalendarBackupService(user_id=user_id)

        start_date_obj = None
        end_date_obj = None
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

        with console.status("[bold green]Processing backup..."):
            if backup_format == 'local_calendar':
                result = service.backup_calendar_to_local_calendar(
                    source_calendar_name=source_calendar,
                    backup_calendar_name=backup_destination,
                    start_date=start_date_obj,
                    end_date=end_date_obj
                )
            else:
                backup_format_enum = BackupFormat(backup_format)
                result = service.backup_calendar_to_file(
                    calendar_name=source_calendar,
                    backup_path=backup_destination,
                    backup_format=backup_format_enum,
                    start_date=start_date_obj,
                    end_date=end_date_obj,
                    include_metadata=include_metadata
                )

        # Print backup summary
        console.print("\n" + "=" * 60)
        console.print("[bold blue]BACKUP SUMMARY[/bold blue]")
        console.print("=" * 60)

        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="green")

        table.add_row("Total appointments:", str(result.total_appointments))
        table.add_row("Backed up:", str(result.backed_up))
        table.add_row("Failed:", str(result.failed))
        table.add_row("Backup location:", result.backup_location)
        table.add_row("Backup format:", result.backup_format)

        console.print(table)

        if result.errors:
            console.print(f"\n[red]Errors ({len(result.errors)}):[/red]")
            for i, error in enumerate(result.errors[:5], 1):
                console.print(f"  {i}. {error}")

        console.print("=" * 60)

        if result.backed_up > 0:
            console.print(f"\n[green]✓ Successfully backed up {result.backed_up} appointments![/green]")

    except Exception as e:
        console.print(f"[red]Error during backup: {e}[/red]")
        raise typer.Exit(code=1)


