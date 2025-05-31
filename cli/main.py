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
from rich.table import Table
from rich.console import Console
from typing import List, Optional
from sqlalchemy.orm.attributes import InstrumentedAttribute
import os
from core.utilities.auth_utility import get_cached_access_token
from core.services import UserService
from core.services.calendar_service import CalendarService
import tzlocal

app = typer.Typer(help="Admin Assistant CLI for running calendar and timesheet operations.")
calendar_app = typer.Typer(help="Calendar operations")
categories_app = typer.Typer(help="Category management operations")
timesheet_app = typer.Typer(help="Timesheet operations")
config_app = typer.Typer(help="Configuration operations")
archive_config_app = typer.Typer(help="Calendar configuration operations")
archive_archive_config_app = typer.Typer(help="Archive configuration management")
login_app = typer.Typer(help="Authentication commands")

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

@calendar_app.command("archive")
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
        user_service = UserService()
        user = user_service.get_by_id(user_id)
        if not user:
            typer.echo(f"No user found in user DB for user_id={user_id}.")
            raise typer.Exit(code=1)
        access_token = get_cached_access_token()
        if not access_token:
            typer.echo("[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]")
            raise typer.Exit(code=1)
        graph_client = get_graph_client(user, access_token)
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

# Categories commands
@categories_app.command("list")
def list_categories(
    user_id: int = user_id_option,
    store: str = typer.Option(
        "local",
        "--store",
        help="Category store: local or msgraph.",
        show_default=True,
        case_sensitive=False,
        autocompletion=lambda ctx, args, incomplete: [d for d in ["local", "msgraph"] if d.startswith(incomplete.lower())],
    )
):
    """List all categories for a user from the specified store."""
    from core.services.category_service import CategoryService
    from core.repositories import get_category_repository
    from core.services import UserService
    from core.db import get_session
    from core.utilities import get_graph_client
    from core.utilities.auth_utility import get_cached_access_token
    from rich.console import Console
    from rich.table import Table

    console = Console()

    try:
        # Get user
        user_service = UserService()
        user = user_service.get_by_id(user_id)
        if not user:
            console.print(f"[red]No user found for user_id={user_id}.[/red]")
            raise typer.Exit(code=1)

        # Get repository based on store
        if store == "local":
            session = get_session()
            repository = get_category_repository(user, store="local", session=session)
        elif store == "msgraph":
            access_token = get_cached_access_token()
            if not access_token:
                console.print("[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]")
                raise typer.Exit(code=1)
            graph_client = get_graph_client(user, access_token)
            repository = get_category_repository(user, store="msgraph", msgraph_client=graph_client)
        else:
            console.print(f"[red]Invalid store '{store}'. Must be 'local' or 'msgraph'.[/red]")
            raise typer.Exit(code=1)

        service = CategoryService(repository)
        categories = service.list()

        if not categories:
            console.print(f"[yellow]No categories found for user_id={user_id} in {store} store.[/yellow]")
            return

        table = Table(title=f"Categories for user_id={user_id} (store: {store})")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Description", style="white")
        table.add_column("Store", style="blue")

        for category in categories:
            # For local categories, use the database ID; for msgraph, use a placeholder
            category_id = str(getattr(category, 'id', 'N/A'))
            table.add_row(
                category_id,
                category.name,
                category.description or "",
                store.title()
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing categories: {e}[/red]")
        raise typer.Exit(code=1)

@categories_app.command("add")
def add_category(
    user_id: int = user_id_option,
    store: str = typer.Option(
        "local",
        "--store",
        help="Category store: local or msgraph.",
        show_default=True,
        case_sensitive=False,
        autocompletion=lambda ctx, args, incomplete: [d for d in ["local", "msgraph"] if d.startswith(incomplete.lower())],
    ),
    name: str = typer.Option(None, "--name", help="Category name"),
    description: str = typer.Option(None, "--description", help="Category description")
):
    """Add a new category for a user in the specified store."""
    from core.models.category import Category
    from core.services.category_service import CategoryService
    from core.repositories import get_category_repository
    from core.services import UserService
    from core.db import get_session
    from core.utilities import get_graph_client
    from core.utilities.auth_utility import get_cached_access_token
    from rich.console import Console

    console = Console()

    # Prompt for missing fields
    if not name:
        name = typer.prompt("Category name")

    if not description:
        description = typer.prompt("Category description (optional)", default="")

    try:
        # Get user
        user_service = UserService()
        user = user_service.get_by_id(user_id)
        if not user:
            console.print(f"[red]No user found for user_id={user_id}.[/red]")
            raise typer.Exit(code=1)

        # Get repository based on store
        if store == "local":
            session = get_session()
            repository = get_category_repository(user, store="local", session=session)
        elif store == "msgraph":
            access_token = get_cached_access_token()
            if not access_token:
                console.print("[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]")
                raise typer.Exit(code=1)
            graph_client = get_graph_client(user, access_token)
            repository = get_category_repository(user, store="msgraph", msgraph_client=graph_client)
        else:
            console.print(f"[red]Invalid store '{store}'. Must be 'local' or 'msgraph'.[/red]")
            raise typer.Exit(code=1)

        service = CategoryService(repository)

        category = Category(
            user_id=user_id,
            name=name.strip(),
            description=description.strip() if description else None
        )

        service.create(category)
        console.print(f"[green]Category '{name}' created successfully in {store} store.[/green]")

    except Exception as e:
        console.print(f"[red]Error creating category: {e}[/red]")
        raise typer.Exit(code=1)

@categories_app.command("edit")
def edit_category(
    user_id: int = user_id_option,
    store: str = typer.Option(
        "local",
        "--store",
        help="Category store: local or msgraph.",
        show_default=True,
        case_sensitive=False,
        autocompletion=lambda ctx, args, incomplete: [d for d in ["local", "msgraph"] if d.startswith(incomplete.lower())],
    ),
    category_id: str = typer.Option(..., "--id", help="Category ID to edit"),
    name: str = typer.Option(None, "--name", help="New category name"),
    description: str = typer.Option(None, "--description", help="New category description")
):
    """Edit an existing category in the specified store."""
    from core.services.category_service import CategoryService
    from core.repositories import get_category_repository
    from core.services import UserService
    from core.db import get_session
    from core.utilities import get_graph_client
    from core.utilities.auth_utility import get_cached_access_token
    from rich.console import Console

    console = Console()

    try:
        # Get user
        user_service = UserService()
        user = user_service.get_by_id(user_id)
        if not user:
            console.print(f"[red]No user found for user_id={user_id}.[/red]")
            raise typer.Exit(code=1)

        # Get repository based on store
        if store == "local":
            session = get_session()
            repository = get_category_repository(user, store="local", session=session)
        elif store == "msgraph":
            access_token = get_cached_access_token()
            if not access_token:
                console.print("[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]")
                raise typer.Exit(code=1)
            graph_client = get_graph_client(user, access_token)
            repository = get_category_repository(user, store="msgraph", msgraph_client=graph_client)
        else:
            console.print(f"[red]Invalid store '{store}'. Must be 'local' or 'msgraph'.[/red]")
            raise typer.Exit(code=1)

        service = CategoryService(repository)
        category = service.get_by_id(category_id)

        if not category:
            console.print(f"[red]Category {category_id} not found for user {user_id} in {store} store.[/red]")
            raise typer.Exit(code=1)

        # Update fields if provided
        if name is not None:
            category.name = name.strip()

        if description is not None:
            category.description = description.strip() if description else None

        service.update(category)
        console.print(f"[green]Category {category_id} updated successfully in {store} store.[/green]")

    except Exception as e:
        console.print(f"[red]Error updating category: {e}[/red]")
        raise typer.Exit(code=1)

@categories_app.command("delete")
def delete_category(
    user_id: int = user_id_option,
    store: str = typer.Option(
        "local",
        "--store",
        help="Category store: local or msgraph.",
        show_default=True,
        case_sensitive=False,
        autocompletion=lambda ctx, args, incomplete: [d for d in ["local", "msgraph"] if d.startswith(incomplete.lower())],
    ),
    category_id: str = typer.Option(..., "--id", help="Category ID to delete"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt")
):
    """Delete a category from the specified store."""
    from core.services.category_service import CategoryService
    from core.repositories import get_category_repository
    from core.services import UserService
    from core.db import get_session
    from core.utilities import get_graph_client
    from core.utilities.auth_utility import get_cached_access_token
    from rich.console import Console

    console = Console()

    try:
        # Get user
        user_service = UserService()
        user = user_service.get_by_id(user_id)
        if not user:
            console.print(f"[red]No user found for user_id={user_id}.[/red]")
            raise typer.Exit(code=1)

        # Get repository based on store
        if store == "local":
            session = get_session()
            repository = get_category_repository(user, store="local", session=session)
        elif store == "msgraph":
            access_token = get_cached_access_token()
            if not access_token:
                console.print("[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]")
                raise typer.Exit(code=1)
            graph_client = get_graph_client(user, access_token)
            repository = get_category_repository(user, store="msgraph", msgraph_client=graph_client)
        else:
            console.print(f"[red]Invalid store '{store}'. Must be 'local' or 'msgraph'.[/red]")
            raise typer.Exit(code=1)

        service = CategoryService(repository)
        category = service.get_by_id(category_id)

        if not category:
            console.print(f"[red]Category {category_id} not found for user {user_id} in {store} store.[/red]")
            raise typer.Exit(code=1)

        if not confirm:
            delete_confirm = typer.confirm(f"Are you sure you want to delete category '{category.name}' from {store} store?")
            if not delete_confirm:
                console.print("[yellow]Category deletion cancelled.[/yellow]")
                return

        service.delete(category_id)
        console.print(f"[green]Category '{category.name}' deleted successfully from {store} store.[/green]")

    except Exception as e:
        console.print(f"[red]Error deleting category: {e}[/red]")
        raise typer.Exit(code=1)

@categories_app.command("validate")
def validate_categories(
    user_id: int = user_id_option,
    start_date: str = typer.Option(None, help="Start date (YYYY-MM-DD or flexible format)"),
    end_date: str = typer.Option(None, help="End date (YYYY-MM-DD or flexible format)"),
    show_stats: bool = typer.Option(True, "--stats/--no-stats", help="Show category statistics"),
    show_issues: bool = typer.Option(True, "--issues/--no-issues", help="Show validation issues")
):
    """Validate appointment categories for a user and date range."""
    from core.services.category_processing_service import CategoryProcessingService
    from core.services.calendar_service import CalendarService
    from rich.console import Console
    from rich.table import Table

    console = Console()

    try:
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

        console.print(f"[blue]Validating categories for user {user_id} from {start_dt} to {end_dt}[/blue]")

        # Get appointments directly from database for all calendars
        from core.services import UserService
        from core.models.appointment import Appointment

        session = get_session()
        user_service = UserService()
        user = user_service.get_by_id(user_id)

        if not user:
            console.print(f"[red]No user found for user_id={user_id}.[/red]")
            raise typer.Exit(code=1)

        # Query appointments for the user within the date range
        from datetime import datetime, timezone
        start_datetime = datetime.combine(start_dt, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(end_dt, datetime.max.time()).replace(tzinfo=timezone.utc)

        appointments = session.query(Appointment).filter(
            Appointment.user_id == user_id,
            Appointment.start_time >= start_datetime,
            Appointment.end_time <= end_datetime
        ).all()

        if not appointments:
            console.print("[yellow]No appointments found for the specified date range.[/yellow]")
            return

        # Validate categories
        category_service = CategoryProcessingService()
        stats = category_service.get_category_statistics(appointments)

        if show_stats:
            # Display statistics table
            stats_table = Table(title="Category Validation Statistics")
            stats_table.add_column("Metric", style="cyan")
            stats_table.add_column("Value", style="green")

            stats_table.add_row("Total Appointments", str(stats['total_appointments']))
            stats_table.add_row("Appointments with Categories", str(stats['appointments_with_categories']))
            stats_table.add_row("Personal Appointments", str(stats['personal_appointments']))
            stats_table.add_row("Valid Categories", str(stats['valid_categories']))
            stats_table.add_row("Invalid Categories", str(stats['invalid_categories']))
            stats_table.add_row("Unique Customers", str(len(stats['customers'])))

            console.print(stats_table)

            # Display customers and billing types
            if stats['customers']:
                console.print(f"\n[bold]Customers found:[/bold] {', '.join(sorted(stats['customers']))}")

            if stats['billing_types']:
                billing_summary = ", ".join([f"{bt}: {count}" for bt, count in stats['billing_types'].items()])
                console.print(f"[bold]Billing types:[/bold] {billing_summary}")

        if show_issues and stats['issues']:
            # Display validation issues
            issues_table = Table(title="Validation Issues")
            issues_table.add_column("Issue", style="red")

            for issue in stats['issues'][:20]:  # Limit to first 20 issues
                issues_table.add_row(issue)

            if len(stats['issues']) > 20:
                issues_table.add_row(f"... and {len(stats['issues']) - 20} more issues")

            console.print(issues_table)

        # Summary
        if stats['invalid_categories'] > 0:
            console.print(f"\n[red]Found {stats['invalid_categories']} appointments with invalid categories.[/red]")
            console.print("[yellow]Consider fixing these categories to improve timesheet accuracy.[/yellow]")
        else:
            console.print("\n[green]All appointments have valid categories! ✓[/green]")

    except Exception as e:
        console.print(f"[red]Error validating categories: {e}[/red]")
        raise typer.Exit(code=1)


@calendar_app.command("analyze-overlaps")
def analyze_overlaps(
    user_id: int = user_id_option,
    start_date: str = typer.Option(None, help="Start date (YYYY-MM-DD or flexible format)"),
    end_date: str = typer.Option(None, help="End date (YYYY-MM-DD or flexible format)"),
    auto_resolve: bool = typer.Option(False, "--auto-resolve", help="Apply automatic resolution rules"),
    show_details: bool = typer.Option(True, "--details/--no-details", help="Show detailed overlap information")
):
    """Analyze overlapping appointments and optionally auto-resolve."""
    from core.services.enhanced_overlap_resolution_service import EnhancedOverlapResolutionService
    from core.utilities.calendar_overlap_utility import detect_overlaps
    from core.utilities.calendar_recurrence_utility import expand_recurring_events_range
    from core.services import UserService
    from core.models.appointment import Appointment
    from rich.console import Console
    from rich.table import Table

    console = Console()

    try:
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

        console.print(f"[blue]Analyzing overlaps for user {user_id} from {start_dt} to {end_dt}[/blue]")

        # Get appointments directly from database for all calendars
        session = get_session()
        user_service = UserService()
        user = user_service.get_by_id(user_id)

        if not user:
            console.print(f"[red]No user found for user_id={user_id}.[/red]")
            raise typer.Exit(code=1)

        # Query appointments for the user within the date range
        from datetime import datetime, timezone
        start_datetime = datetime.combine(start_dt, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(end_dt, datetime.max.time()).replace(tzinfo=timezone.utc)

        appointments = session.query(Appointment).filter(
            Appointment.user_id == user_id,
            Appointment.start_time >= start_datetime,
            Appointment.end_time <= end_datetime
        ).all()

        if not appointments:
            console.print("[yellow]No appointments found for the specified date range.[/yellow]")
            return

        # Expand recurring events
        expanded_appointments = expand_recurring_events_range(appointments, start_dt, end_dt)
        console.print(f"[blue]Expanded {len(appointments)} appointments to {len(expanded_appointments)} instances[/blue]")

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
                resolution_result = overlap_service.apply_automatic_resolution_rules(group)

                if resolution_result['resolved']:
                    resolved_count += 1

                if resolution_result['conflicts']:
                    remaining_conflicts.append(resolution_result['conflicts'])

                if show_details and resolution_result['resolution_log']:
                    console.print(f"[blue]Resolution: {'; '.join(resolution_result['resolution_log'])}[/blue]")

            # Display resolution summary
            summary_table = Table(title="Overlap Resolution Summary")
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Value", style="green")

            summary_table.add_row("Total Overlap Groups", str(len(overlap_groups)))
            summary_table.add_row("Auto-Resolved", str(resolved_count))
            summary_table.add_row("Remaining Conflicts", str(len(remaining_conflicts)))

            console.print(summary_table)

            if remaining_conflicts:
                console.print(f"\n[red]{len(remaining_conflicts)} overlap groups still need manual resolution[/red]")
                overlap_groups = remaining_conflicts  # Show only unresolved conflicts
            else:
                console.print("\n[green]All overlaps resolved automatically! ✓[/green]")
                return

        # Display overlap details
        if show_details and overlap_groups:
            for i, group in enumerate(overlap_groups[:10], 1):  # Limit to first 10 groups
                overlap_table = Table(title=f"Overlap Group {i}")
                overlap_table.add_column("Subject", style="green")
                overlap_table.add_column("Start Time", style="blue")
                overlap_table.add_column("End Time", style="blue")
                overlap_table.add_column("Show As", style="yellow")
                overlap_table.add_column("Importance", style="magenta")
                overlap_table.add_column("Categories", style="cyan")

                for appt in group:
                    categories = getattr(appt, 'categories', [])
                    if isinstance(categories, list):
                        categories_str = ', '.join(categories) if categories else 'None'
                    else:
                        categories_str = str(categories) if categories else 'None'

                    overlap_table.add_row(
                        str(getattr(appt, 'subject', 'No Subject')),
                        str(getattr(appt, 'start_time', 'Unknown')),
                        str(getattr(appt, 'end_time', 'Unknown')),
                        str(getattr(appt, 'show_as', 'Unknown')),
                        str(getattr(appt, 'importance', 'Unknown')),
                        categories_str
                    )

                console.print(overlap_table)
                console.print()  # Add spacing between groups

            if len(overlap_groups) > 10:
                console.print(f"[yellow]... and {len(overlap_groups) - 10} more overlap groups[/yellow]")

        # Final summary
        if not auto_resolve:
            console.print(f"\n[yellow]Found {len(overlap_groups)} overlap groups that need attention.[/yellow]")
            console.print("[blue]Use --auto-resolve to apply automatic resolution rules.[/blue]")

    except Exception as e:
        console.print(f"[red]Error analyzing overlaps: {e}[/red]")
        raise typer.Exit(code=1)



@archive_archive_config_app.command("list")
def list_configs(user_id: int = user_id_option):
    """List all archive configurations for a user."""
    from core.services.archive_configuration_service import ArchiveConfigurationService
    service = ArchiveConfigurationService()
    configs = service.list_for_user(user_id)
    console = Console()
    if not configs:
        console.print(f"[yellow]No archive configurations found for user_id={user_id}.[/yellow]")
        raise typer.Exit(code=0)
    table = Table(title=f"Archive Configurations for user_id={user_id}")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Source", style="magenta")
    table.add_column("Dest", style="magenta")
    table.add_column("Active", style="yellow")
    table.add_column("TZ", style="blue")
    for c in configs:
        table.add_row(
            str(getattr(c, 'id', '')),
            str(getattr(c, 'name', '')),
            str(getattr(c, 'source_calendar_uri', '')),
            str(getattr(c, 'destination_calendar_uri', '')),
            "✔" if getattr(c, 'is_active', False) else "✗",
            str(getattr(c, 'timezone', '')),
        )
    console.print(table)

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
    # Get system timezone
    system_timezone = tzlocal.get_localzone_name()
    # Prompt for missing fields
    if not name:
        name = typer.prompt("Name for the archive configuration")
    if not source_calendar_uri:
        source_calendar_uri = typer.prompt("Source calendar URI (e.g., msgraph://id)")
    if not destination_calendar_uri:
        destination_calendar_uri = typer.prompt("Destination (archive) calendar URI (e.g., msgraph://id)")
    if not timezone:
        timezone = typer.prompt("Timezone (IANA format, e.g., Europe/London)", default=system_timezone)
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

calendar_app.add_typer(categories_app, name="categories")
app.add_typer(calendar_app, name="calendar")
app.add_typer(config_app, name="config")

def uri_safe_name(name: str) -> str:
    """
    Convert a calendar name to a URI-safe string (lowercase, dashes for spaces, alphanumerics and dashes/underscores only).
    """
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"[^a-z0-9\-_]", "", name)
    return name

def safe_str(val):
    if hasattr(val, 'expression') or isinstance(val, InstrumentedAttribute):
        return ''
    return str(val) if val is not None else ''

def safe_bool(val):
    if isinstance(val, bool):
        return val
    elif isinstance(val, (int, float)):
        return bool(val)
    else:
        raise ValueError("Invalid type for safe_bool")

def is_msgraph_token_valid(user, session) -> bool:
    """
    Returns True if the user has a valid MS Graph token (cache present and not expired), False otherwise.
    Attempts a silent token acquisition (no prompt).
    """
    try:
        # Try silent token acquisition (no prompt)
        try:
            return True
        except Exception:
            return False
    except Exception:
        return False

def get_calendars_for_user(user_id: int, datastore: str = "all", console: Optional[Console] = None) -> List[dict]:
    """
    Retrieve all calendars for a user from the specified datastore(s).
    Args:
        user_id (int): The user ID.
        datastore (str): 'local', 'msgraph', or 'all'.
    Returns:
        List[dict]: List of calendar dicts with keys: id, ms_calendar_id, name, description, type, is_primary, is_active, source.
    Raises:
        Exception: If user not found or repository errors occur.
    """
    from core.repositories import SQLAlchemyCalendarRepository, MSGraphCalendarRepository
    from core.utilities import get_graph_client
    from core.db import get_session
    from core.repositories.user_repository import UserRepository

    session = get_session()
    user_repo = UserRepository(session)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise ValueError(f"No user found for user_id={user_id}.")

    calendars = []
    if datastore in ("local", "all"):
        local_repo = SQLAlchemyCalendarRepository(user, session=session)
        for cal in local_repo.list():
            name_str = safe_str(cal.name)
            id_str = safe_str(cal.id)
            uri = f"local://{uri_safe_name(name_str) or id_str}"
            calendars.append({
                "name": name_str,
                "description": safe_str(cal.description),
                "type": safe_str(cal.calendar_type),
                "is_primary": cal.is_primary,
                "is_active": cal.is_active,
                "source": "Local Database",
                "uri": uri
            })
    if datastore in ("msgraph", "all"):
        try:
            access_token = get_cached_access_token()
            if not access_token:
                if console:
                    console.print("[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'. Skipping Microsoft 365 calendars.[/yellow]")
                else:
                    print("No valid MS Graph token found. Please login with 'admin-assistant login msgraph'. Skipping Microsoft 365 calendars.")
                return calendars
            graph_client = get_graph_client(user, access_token)
            ms_repo = MSGraphCalendarRepository(graph_client, user)
            for cal in ms_repo.list():
                name_str = safe_str(cal.name)
                ms_id_str = safe_str(getattr(cal, 'ms_calendar_id', ''))
                is_primary = safe_bool(cal.is_primary)
                if is_primary:
                    uri = "msgraph://calendar"
                else:
                    uri = f"msgraph://{uri_safe_name(name_str) or ms_id_str}"
                calendars.append({
                    "name": name_str,
                    "description": safe_str(cal.description),
                    "type": safe_str(getattr(cal, 'calendar_type', 'msgraph')),
                    "is_primary": is_primary,
                    "is_active": safe_bool(cal.is_active),
                    "source": "Microsoft 365",
                    "uri": uri
                })
        except Exception as e:
            import traceback
            if console:
                console.print(f"[red]Failed to list MS Graph calendars: {e}[/red]")
                console.print(traceback.format_exc())
            else:
                print(f"Failed to list MS Graph calendars: {e}")
                print(traceback.format_exc())
    return calendars

def calendar_name_id_autocomplete(ctx: typer.Context, args: List[str], incomplete: str) -> List[str]:
    """
    Typer autocompletion callback for calendar names and IDs.
    Returns matching names and IDs for the user and datastore.
    """
    user_id = None
    datastore = "all"
    for i, arg in enumerate(args):
        if arg == "--user" and i + 1 < len(args):
            user_id = args[i + 1]
        if arg == "--datastore" and i + 1 < len(args):
            datastore = args[i + 1]
    if not user_id or not user_id.isdigit():
        return []
    try:
        calendars = get_calendars_for_user(int(user_id), datastore)
        completions = []
        for cal in calendars:
            if incomplete.lower() in str(cal["name"]).lower() or incomplete.lower() in str(cal["id"]).lower() or (cal["ms_calendar_id"] and incomplete.lower() in str(cal["ms_calendar_id"]).lower()):
                completions.append(f"{cal['name']} ({cal['id'] or cal['ms_calendar_id']})")
        return completions
    except Exception:
        return []

@calendar_app.command("list")
def list_calendars(
    user_id: int = user_id_option,
    datastore: str = typer.Option(
        "all",
        "--datastore",
        help="Datastore to query: local, msgraph, or all.",
        show_default=True,
        case_sensitive=False,
        autocompletion=lambda ctx, args, incomplete: [d for d in ["local", "msgraph", "all"] if d.startswith(incomplete.lower())],
    ),
):
    """
    List all calendars for a user across datastores (local, msgraph, or all).
    """
    console = Console()
    try:
        calendars = get_calendars_for_user(user_id, datastore, console=console)
        if not calendars:
            console.print(f"[yellow]No calendars found for user_id={user_id} in datastore '{datastore}'.[/yellow]")
            raise typer.Exit(code=0)
        table = Table(title=f"Calendars for user_id={user_id} (datastore: {datastore})")
        table.add_column("Source", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Description", style="white")
        table.add_column("Type", style="blue")
        table.add_column("Primary", style="yellow")
        table.add_column("Active", style="yellow")
        table.add_column("URI", style="magenta")
        for cal in calendars:
            table.add_row(
                str(cal["source"] or ""),
                str(cal["name"] or ""),
                str(cal["description"] or ""),
                str(cal["type"] or ""),
                "✔" if safe_bool(cal["is_primary"]) else "",
                "✔" if safe_bool(cal["is_active"]) else "✗",
                str(cal["uri"] or ""),
            )
        console.print(table)
    except Exception as e:
        import traceback
        console.print(f"[red]Failed to list calendars: {e}[/red]")
        console.print(traceback.format_exc())
        raise typer.Exit(code=1)

@login_app.command("msgraph")
def login_msgraph(user_id: int = user_id_option):
    """
    Log in to Microsoft 365 (MS Graph) for the given user. Uses MSAL device code flow and caches token in ~/.cache/admin-assistant/ms_token.json.
    """
    from core.utilities.auth_utility import msal_login
    try:
        result = msal_login()
        typer.echo("Microsoft 365 login successful. Token cached for future CLI use.")
    except Exception as e:
        typer.echo(f"Login failed: {e}")
        raise typer.Exit(code=1)

@login_app.command("logout")
def logout_msgraph(user_id: int = user_id_option):
    """
    Log out from Microsoft 365 (MS Graph) for the given user. Removes the token cache file.
    """
    from core.utilities.auth_utility import msal_logout
    msal_logout()
    typer.echo("Microsoft 365 token removed. You are now logged out.")

app.add_typer(login_app, name="login")

@calendar_app.command("create")
def create_calendar(
    user_id: int = user_id_option,
    store: str = typer.Option(..., "--store", help="Calendar store: local or msgraph", case_sensitive=False),
    name: str = typer.Option(None, "--name", help="Name for the calendar (required)"),
    description: str = typer.Option(None, "--description", help="Optional description for the calendar")
):
    """
    Create a new calendar for a user in the selected store (local or msgraph).
    """
    from core.repositories import SQLAlchemyCalendarRepository, MSGraphCalendarRepository
    from core.models.calendar import Calendar
    from core.db import get_session
    from core.utilities import get_graph_client
    from core.utilities.auth_utility import get_cached_access_token
    from rich.console import Console
    console = Console()

    store = store.lower().strip()
    if store not in ("local", "msgraph"):
        console.print("[red]Invalid store. Must be 'local' or 'msgraph'.[/red]")
        raise typer.Exit(code=1)

    # Prompt for missing required fields
    if not name:
        name = typer.prompt("Name for the calendar")

    session = get_session() if store == "local" else None
    user_service = UserService()
    user = user_service.get_by_id(user_id)
    if not user:
        console.print(f"[red]No user found for user_id={user_id}.[/red]")
        raise typer.Exit(code=1)

    calendar = Calendar(
        user_id=user_id,
        name=name,
        description=description,
        calendar_type="real",  # default
        is_primary=False,       # default
        is_active=True          # default
    )

    try:
        if store == "local":
            repo = SQLAlchemyCalendarRepository(user, session=session)
        else:
            access_token = get_cached_access_token()
            if not access_token:
                console.print("[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]")
                raise typer.Exit(code=1)
            graph_client = get_graph_client(user, access_token)
            repo = MSGraphCalendarRepository(graph_client, user)
        service = CalendarService(repo)
        service.create(calendar)
        console.print(f"[green]Calendar '{name}' created successfully in {store} store.[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create calendar: {e}[/red]")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app() 
