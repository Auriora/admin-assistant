"""Calendar operations commands."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cli.common.options import user_option
from cli.common.utils import parse_date_range, resolve_cli_user
from core.db import get_session
from core.orchestrators.archive_job_runner import ArchiveJobRunner
from core.utilities import get_graph_client
from core.utilities.auth_utility import get_cached_access_token

calendar_app = typer.Typer(help="Calendar operations", rich_markup_mode="rich")


@calendar_app.callback()
def calendar_callback(ctx: typer.Context):
    """Calendar operations and management.

    Manage calendar data, archiving, backups, and restoration.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@calendar_app.command("archive")
def archive(
    archive_config_name: str = typer.Argument(
        ...,
        help="Name of the archive configuration to use.",
    ),
    date_option: str = typer.Option(
        "yesterday",
        "--date",
        help="Date or date range. Accepts: 'today', 'yesterday', 'last 7 days' (7 days ending yesterday), 'last week' (previous calendar week), 'last 30 days' (30 days ending yesterday), 'last month' (previous calendar month), a single date (e.g. 31-12-2024, 31-Dec, 31-12), or a range (e.g. 1-6 to 7-6, 1-6-2024 - 7-6-2024).",
    ),
    replace: bool = typer.Option(
        False,
        "--replace",
        help="Replace existing appointments in the archive calendar for the specified date range. WARNING: This will delete existing archived appointments before adding new ones. Use with caution.",
    ),
    user_input: Optional[str] = user_option,
):
    """Manually trigger calendar archiving for the configured user and archive configuration."""
    from core.services.archive_configuration_service import ArchiveConfigurationService

    console = Console()
    runner = ArchiveJobRunner()
    session = get_session()
    try:
        start_dt, end_dt = parse_date_range(date_option)
    except Exception as e:
        console.print(f"Error parsing date: {e}")
        raise typer.Exit(code=1)
    try:
        user = resolve_cli_user(user_input)

        # Resolve archive config name to ID
        archive_service = ArchiveConfigurationService()
        archive_config = archive_service.get_by_name(archive_config_name, user.id)
        if not archive_config:
            console.print(f"[red]Archive configuration '{archive_config_name}' not found for user {user.id} ({user.username or user.email}).[/red]")
            raise typer.Exit(code=1)

        access_token = get_cached_access_token()
        if not access_token:
            console.print(
                "[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]"
            )
            raise typer.Exit(code=1)
        graph_client = get_graph_client(user, access_token)
        # If only one date is present, set both to the same value
        if start_dt and not end_dt:
            end_dt = start_dt
        if end_dt and not start_dt:
            start_dt = end_dt
        # Handle replace option with confirmation
        if replace:
            console.print(f"[yellow]WARNING: Replace mode will delete existing archived appointments from {start_dt} to {end_dt}[/yellow]")
            console.print(f"[yellow]Archive calendar: {archive_config.destination_calendar_uri}[/yellow]")

            if not typer.confirm("Are you sure you want to proceed with replace mode?"):
                console.print("Operation cancelled.")
                raise typer.Exit(code=0)

        result = runner.run_archive_job(
            user_id=user.id,
            archive_config_id=archive_config.id,
            start_date=start_dt,
            end_date=end_dt,
            replace_mode=replace,
        )
    except Exception as e:
        console.print(f"Archiving failed: {e}")
        raise typer.Exit(code=1)

    # Print result without debug tags
    console.print("ARCHIVE RESULT")
    console.print(result)


@calendar_app.command("timesheet")
def timesheet(
    timesheet_config_name: str = typer.Argument(
        ...,
        help="Name of the timesheet configuration to use.",
    ),
    date_option: str = typer.Option(
        "yesterday",
        "--date",
        help="Date or date range. Accepts: 'today', 'yesterday', 'last 7 days' (7 days ending yesterday), 'last week' (previous calendar week), 'last 30 days' (30 days ending yesterday), 'last month' (previous calendar month), a single date (e.g. 31-12-2024, 31-Dec, 31-12), or a range (e.g. 1-6 to 7-6, 1-6-2024 - 7-6-2024).",
    ),
    replace: bool = typer.Option(
        False,
        "--replace",
        help="Replace existing appointments in the timesheet calendar for the specified date range. WARNING: This will delete existing archived appointments before adding new ones. Use with caution.",
    ),
    include_travel: bool = typer.Option(
        True,
        "--travel/--no-travel",
        help="Include travel appointments in timesheet archive (default: True).",
    ),
    user_input: Optional[str] = user_option,
):
    """Archive calendar appointments for timesheet/billing purposes using business category filtering.

    This command filters appointments to include only business categories (billable, non-billable, travel),
    excludes personal appointments and 'Free' status appointments, and applies automatic overlap resolution.
    """
    from core.services.archive_configuration_service import ArchiveConfigurationService

    console = Console()
    runner = ArchiveJobRunner()
    session = get_session()
    try:
        start_dt, end_dt = parse_date_range(date_option)
    except Exception as e:
        console.print(f"Error parsing date: {e}")
        raise typer.Exit(code=1)
    try:
        user = resolve_cli_user(user_input)

        # Resolve timesheet config name to ID
        archive_service = ArchiveConfigurationService()
        timesheet_config = archive_service.get_by_name(timesheet_config_name, user.id)
        if not timesheet_config:
            console.print(f"[red]Timesheet configuration '{timesheet_config_name}' not found for user {user.id} ({user.username or user.email}).[/red]")
            raise typer.Exit(code=1)

        # Verify this is a timesheet configuration
        if getattr(timesheet_config, 'archive_purpose', 'general') != 'timesheet':
            console.print(f"[yellow]Warning: Configuration '{timesheet_config_name}' has purpose '{getattr(timesheet_config, 'archive_purpose', 'general')}', not 'timesheet'.[/yellow]")
            console.print("[yellow]Consider using a timesheet-specific configuration for best results.[/yellow]")

        access_token = get_cached_access_token()
        if not access_token:
            console.print(
                "[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]"
            )
            raise typer.Exit(code=1)
        graph_client = get_graph_client(user, access_token)
        # If only one date is present, set both to the same value
        if start_dt and not end_dt:
            end_dt = start_dt
        if end_dt and not start_dt:
            start_dt = end_dt
        # Handle replace option with confirmation
        if replace:
            console.print(f"[yellow]WARNING: Replace mode will delete existing timesheet appointments from {start_dt} to {end_dt}[/yellow]")
            console.print(f"[yellow]Timesheet calendar: {timesheet_config.destination_calendar_uri}[/yellow]")

            if not typer.confirm("Are you sure you want to proceed with replace mode?"):
                console.print("Operation cancelled.")
                raise typer.Exit(code=0)

        result = runner.run_archive_job(
            user_id=user.id,
            archive_config_id=timesheet_config.id,
            start_date=start_dt,
            end_date=end_dt,
            replace_mode=replace,
        )
    except Exception as e:
        console.print(f"Timesheet archiving failed: {e}")
        raise typer.Exit(code=1)

    # Print result without debug tags
    console.print("TIMESHEET RESULT")
    console.print(result)


@calendar_app.command("travel")
def travel_auto_plan():
    """Auto-plan travel."""
    typer.echo("Auto-planning travel...")


@calendar_app.command("analyze-overlaps")
def analyze_overlaps(
    user_input: Optional[str] = user_option,
    start_date: str = typer.Option(
        None, help="Start date (YYYY-MM-DD or flexible format)"
    ),
    end_date: str = typer.Option(None, help="End date (YYYY-MM-DD or flexible format)"),
    auto_resolve: bool = typer.Option(
        False, "--auto-resolve", help="Apply automatic resolution rules"
    ),
    show_details: bool = typer.Option(
        True, "--details/--no-details", help="Show detailed overlap information"
    ),
):
    """Analyze overlapping appointments and optionally auto-resolve."""
    from datetime import datetime, timezone

    from core.models.appointment import Appointment
    from core.services.enhanced_overlap_resolution_service import (
        EnhancedOverlapResolutionService,
    )
    from core.utilities.calendar_overlap_utility import detect_overlaps
    from core.utilities.calendar_recurrence_utility import expand_recurring_events_range
    from cli.common.utils import parse_flexible_date

    console = Console()

    try:
        # Get user first
        user = resolve_cli_user(user_input)

        # Parse date range
        if start_date or end_date:
            if start_date and end_date:
                start_dt = parse_flexible_date(start_date)
                end_dt = parse_flexible_date(end_date)
            elif start_date:
                start_dt = end_dt = parse_flexible_date(start_date)
            else:
                start_dt = end_dt = parse_flexible_date(end_date)
        else:
            # Default to last 7 days
            start_dt, end_dt = parse_date_range("last 7 days")

        console.print(
            f"[blue]Analyzing overlaps for user {user.id} ({user.username or user.email}) from {start_dt} to {end_dt}[/blue]"
        )

        # Get appointments directly from database for all calendars
        session = get_session()

        # Query appointments for the user within the date range
        start_datetime = datetime.combine(start_dt, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        end_datetime = datetime.combine(end_dt, datetime.max.time()).replace(
            tzinfo=timezone.utc
        )

        appointments = (
            session.query(Appointment)
            .filter(
                Appointment.user_id == user.id,
                Appointment.start_time >= start_datetime,
                Appointment.end_time <= end_datetime,
            )
            .all()
        )

        if not appointments:
            console.print(
                "[yellow]No appointments found for the specified date range.[/yellow]"
            )
            return

        # Expand recurring events
        expanded_appointments = expand_recurring_events_range(
            appointments, start_dt, end_dt
        )
        console.print(
            f"[blue]Expanded {len(appointments)} appointments to {len(expanded_appointments)} instances[/blue]"
        )

        # Detect overlaps
        overlap_groups = detect_overlaps(expanded_appointments)

        if not overlap_groups:
            console.print("[green]No overlapping appointments found! ✓[/green]")
            return

        console.print(f"[yellow]Found {len(overlap_groups)} overlap groups[/yellow]")

        # Apply automatic resolution if requested
        if auto_resolve:
            overlap_service = EnhancedOverlapResolutionService()
            resolved_count = 0
            remaining_conflicts = []

            for group in overlap_groups:
                resolution_result = overlap_service.apply_automatic_resolution_rules(
                    group
                )

                if resolution_result["resolved"]:
                    resolved_count += 1

                if resolution_result["conflicts"]:
                    remaining_conflicts.append(resolution_result["conflicts"])

                if show_details and resolution_result["resolution_log"]:
                    console.print(
                        f"[blue]Resolution: {'; '.join(resolution_result['resolution_log'])}[/blue]"
                    )

            # Display resolution summary
            summary_table = Table(title="Overlap Resolution Summary")
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Value", style="green")

            summary_table.add_row("Total Overlap Groups", str(len(overlap_groups)))
            summary_table.add_row("Auto-Resolved", str(resolved_count))
            summary_table.add_row("Remaining Conflicts", str(len(remaining_conflicts)))

            console.print(summary_table)

            if remaining_conflicts:
                console.print(
                    f"\n[red]{len(remaining_conflicts)} overlap groups still need manual resolution[/red]"
                )
                overlap_groups = remaining_conflicts  # Show only unresolved conflicts
            else:
                console.print("\n[green]All overlaps resolved automatically! ✓[/green]")
                return

        # Display overlap details
        if show_details and overlap_groups:
            for i, group in enumerate(
                overlap_groups[:10], 1
            ):  # Limit to first 10 groups
                overlap_table = Table(title=f"Overlap Group {i}")
                overlap_table.add_column("Subject", style="green")
                overlap_table.add_column("Start Time", style="blue")
                overlap_table.add_column("End Time", style="blue")
                overlap_table.add_column("Show As", style="yellow")
                overlap_table.add_column("Importance", style="magenta")
                overlap_table.add_column("Categories", style="cyan")

                for appt in group:
                    categories = getattr(appt, "categories", [])
                    if isinstance(categories, list):
                        categories_str = ", ".join(categories) if categories else "None"
                    else:
                        categories_str = str(categories) if categories else "None"

                    overlap_table.add_row(
                        str(getattr(appt, "subject", "No Subject")),
                        str(getattr(appt, "start_time", "Unknown")),
                        str(getattr(appt, "end_time", "Unknown")),
                        str(getattr(appt, "show_as", "Unknown")),
                        str(getattr(appt, "importance", "Unknown")),
                        categories_str,
                    )

                console.print(overlap_table)
                console.print()  # Add spacing between groups

            if len(overlap_groups) > 10:
                console.print(
                    f"[yellow]... and {len(overlap_groups) - 10} more overlap groups[/yellow]"
                )

        # Final summary
        if not auto_resolve:
            console.print(
                f"\n[yellow]Found {len(overlap_groups)} overlap groups that need attention.[/yellow]"
            )
            console.print(
                "[blue]Use --auto-resolve to apply automatic resolution rules.[/blue]"
            )

    except Exception as e:
        console.print(f"[red]Error analyzing overlaps: {e}[/red]")
        raise typer.Exit(code=1)


@calendar_app.command("list")
def list_calendars(
    user_input: Optional[str] = user_option,
    datastore: str = typer.Option(
        "all",
        "--datastore",
        help="Datastore to list calendars from: local, msgraph, or all",
        case_sensitive=False,
        autocompletion=lambda ctx, args, incomplete: [
            d for d in ["local", "msgraph", "all"] if d.startswith(incomplete.lower())
        ],
    ),
):
    """List all calendars for a user across datastores (local, msgraph, or all)."""
    from core.repositories import get_calendar_repository
    from core.services.calendar_service import CalendarService

    console = Console()

    try:
        user = resolve_cli_user(user_input)

        if datastore.lower() in ["local", "all"]:
            # List local calendars
            session = get_session()
            local_repo = get_calendar_repository(user, store="local", session=session)
            local_service = CalendarService(local_repo)
            local_calendars = local_service.list()

            if local_calendars:
                local_table = Table(title=f"Local Calendars for {user.username or user.email}")
                local_table.add_column("ID", style="cyan")
                local_table.add_column("Name", style="green")
                local_table.add_column("Description", style="white")

                for cal in local_calendars:
                    local_table.add_row(
                        str(cal.id),
                        cal.name,
                        cal.description or ""
                    )

                console.print(local_table)
            elif datastore.lower() == "local":
                console.print(f"[yellow]No local calendars found for user {user.username or user.email}[/yellow]")

        if datastore.lower() in ["msgraph", "all"]:
            # List MS Graph calendars
            access_token = get_cached_access_token()
            if not access_token:
                console.print("[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]")
                if datastore.lower() == "msgraph":
                    raise typer.Exit(code=1)
            else:
                graph_client = get_graph_client(user, access_token)
                msgraph_repo = get_calendar_repository(user, store="msgraph", msgraph_client=graph_client)
                msgraph_service = CalendarService(msgraph_repo)
                msgraph_calendars = msgraph_service.list()

                if msgraph_calendars:
                    msgraph_table = Table(title=f"MS Graph Calendars for {user.username or user.email}")
                    msgraph_table.add_column("ID", style="cyan")
                    msgraph_table.add_column("Name", style="green")
                    msgraph_table.add_column("Description", style="white")

                    for cal in msgraph_calendars:
                        msgraph_table.add_row(
                            getattr(cal, 'ms_calendar_id', str(cal.id)),
                            cal.name,
                            cal.description or ""
                        )

                    console.print(msgraph_table)
                elif datastore.lower() == "msgraph":
                    console.print(f"[yellow]No MS Graph calendars found for user {user.username or user.email}[/yellow]")

    except Exception as e:
        console.print(f"[red]Failed to list calendars: {e}[/red]")
        raise typer.Exit(code=1)


@calendar_app.command("create")
def create_calendar(
    user_input: Optional[str] = user_option,
    store: str = typer.Option(
        ..., "--store", help="Calendar store: local or msgraph", case_sensitive=False
    ),
    name: str = typer.Option(None, "--name", help="Calendar name"),
    description: str = typer.Option(None, "--description", help="Calendar description"),
):
    """Create a new calendar for a user in the selected store (local or msgraph)."""
    from core.models.calendar import Calendar
    from core.repositories import get_calendar_repository
    from core.services.calendar_service import CalendarService

    console = Console()

    # Prompt for missing fields
    if not name:
        name = typer.prompt("Calendar name")

    if not description:
        description = typer.prompt("Calendar description (optional)", default="")

    try:
        user = resolve_cli_user(user_input)

        # Get repository based on store
        if store.lower() == "local":
            session = get_session()
            repository = get_calendar_repository(user, store="local", session=session)
        elif store.lower() == "msgraph":
            access_token = get_cached_access_token()
            if not access_token:
                console.print("[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]")
                raise typer.Exit(code=1)
            graph_client = get_graph_client(user, access_token)
            repository = get_calendar_repository(user, store="msgraph", msgraph_client=graph_client)
        else:
            console.print(f"[red]Invalid store '{store}'. Must be 'local' or 'msgraph'.[/red]")
            raise typer.Exit(code=1)

        service = CalendarService(repository)

        calendar = Calendar(
            user_id=user.id,
            name=name.strip(),
            description=description.strip() if description else None,
        )

        service.create(calendar)
        console.print(f"[green]Calendar '{name}' created successfully in {store} store.[/green]")

    except Exception as e:
        console.print(f"[red]Failed to create calendar: {e}[/red]")
        raise typer.Exit(code=1)


@calendar_app.command("backup")
def backup_calendar(
    backup_config_name: str = typer.Argument(
        ...,
        help="Name of the backup configuration to use.",
    ),
    date_option: str = typer.Option(
        "yesterday",
        "--date",
        help="Date or date range for backup. Same format as archive command.",
    ),
    replace: bool = typer.Option(
        False,
        "--replace",
        help="Replace existing backup file/calendar. WARNING: This will overwrite existing backups.",
    ),
    user_input: Optional[str] = user_option,
):
    """Manually trigger calendar backup using a backup configuration."""
    from core.orchestrators.backup_job_runner import BackupJobRunner
    from core.services.backup_configuration_service import BackupConfigurationService

    console = Console()

    try:
        start_dt, end_dt = parse_date_range(date_option)
    except Exception as e:
        console.print(f"[red]Error parsing date: {e}[/red]")
        raise typer.Exit(code=1)

    try:
        user = resolve_cli_user(user_input)

        # Resolve backup config name to configuration
        backup_service = BackupConfigurationService()
        backup_configs = backup_service.list(user_id=user.id)
        backup_config = next((c for c in backup_configs if c.name == backup_config_name), None)

        if not backup_config:
            console.print(f"[red]Backup configuration '{backup_config_name}' not found for user {user.id} ({user.username or user.email}).[/red]")
            raise typer.Exit(code=1)

        # Handle replace option with confirmation
        if replace:
            console.print(f"[yellow]WARNING: Replace mode will overwrite existing backup[/yellow]")
            console.print(f"[yellow]Backup destination: {backup_config.destination_uri}[/yellow]")

            if not typer.confirm("Are you sure you want to proceed with replace mode?"):
                console.print("Operation cancelled.")
                raise typer.Exit(code=0)

        # Run backup job
        runner = BackupJobRunner()
        result = runner.run_backup_job(
            user_id=user.id,
            backup_config_id=backup_config.id,
            start_date=start_dt,
            end_date=end_dt,
            replace_mode=replace,
        )

        # Display results
        if result.get("status") == "success":
            console.print(f"\n[green]✓ Backup completed successfully![/green]")
            console.print(f"Total appointments: {result.get('total_appointments', 0)}")
            console.print(f"Successfully backed up: {result.get('backed_up', 0)}")
            if result.get('failed', 0) > 0:
                console.print(f"[yellow]Failed: {result.get('failed', 0)}[/yellow]")
            console.print(f"Backup location: {result.get('backup_location', 'N/A')}")

            errors = result.get('errors', [])
            if errors:
                console.print(f"\n[yellow]Errors encountered:[/yellow]")
                for error in errors[:5]:  # Show first 5 errors
                    console.print(f"  • {error}")
                if len(errors) > 5:
                    console.print(f"  ... and {len(errors) - 5} more errors")
        else:
            console.print(f"[red]Backup failed: {result.get('error', 'Unknown error')}[/red]")
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[red]Backup operation failed: {e}[/red]")
        raise typer.Exit(code=1)
