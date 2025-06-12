"""Category management commands."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cli.common.options import user_option
from cli.common.utils import parse_date_range, parse_flexible_date, resolve_cli_user
from core.db import get_session
from core.utilities import get_graph_client
from core.utilities.auth_utility import get_cached_access_token

category_app = typer.Typer(help="Category management operations", rich_markup_mode="rich")


@category_app.command("list")
def list_category(
    user_input: Optional[str] = user_option,
    store: str = typer.Option(
        "local",
        "--store",
        help="Category store: local or msgraph.",
        show_default=True,
        case_sensitive=False,
        autocompletion=lambda ctx, args, incomplete: [
            d for d in ["local", "msgraph"] if d.startswith(incomplete.lower())
        ],
    ),
):
    """List all categories for a user from the specified store."""
    from core.repositories import get_category_repository
    from core.services.category_service import CategoryService

    console = Console()

    try:
        # Get user
        user = resolve_cli_user(user_input)

        # Get repository based on store
        if store == "local":
            session = get_session()
            repository = get_category_repository(user, store="local", session=session)
        elif store == "msgraph":
            access_token = get_cached_access_token()
            if not access_token:
                console.print(
                    "[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]"
                )
                raise typer.Exit(code=1)
            graph_client = get_graph_client(user, access_token)
            repository = get_category_repository(
                user, store="msgraph", msgraph_client=graph_client
            )
        else:
            console.print(
                f"[red]Invalid store '{store}'. Must be 'local' or 'msgraph'.[/red]"
            )
            raise typer.Exit(code=1)

        service = CategoryService(repository)
        categories = service.list()

        if not categories:
            console.print(
                f"[yellow]No categories found for user {user.id} ({user.username or user.email}) in {store} store.[/yellow]"
            )
            return

        table = Table(
            title=f"Categories for user {user.id} ({user.username or user.email}) (store: {store})"
        )
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Description", style="white")
        table.add_column("Store", style="blue")

        for category in categories:
            # For local categories, use the database ID; for msgraph, use a placeholder
            category_id = str(getattr(category, "id", "N/A"))
            table.add_row(
                category_id, category.name, category.description or "", store.title()
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing categories: {e}[/red]")
        raise typer.Exit(code=1)


@category_app.command("add")
def add_category(
    user_input: Optional[str] = user_option,
    store: str = typer.Option(
        "local",
        "--store",
        help="Category store: local or msgraph.",
        show_default=True,
        case_sensitive=False,
        autocompletion=lambda ctx, args, incomplete: [
            d for d in ["local", "msgraph"] if d.startswith(incomplete.lower())
        ],
    ),
    name: str = typer.Option(None, "--name", help="Category name"),
    description: str = typer.Option(None, "--description", help="Category description"),
):
    """Add a new category for a user in the specified store."""
    from core.models.category import Category
    from core.repositories import get_category_repository
    from core.services.category_service import CategoryService

    console = Console()

    # Prompt for missing fields
    if not name:
        name = typer.prompt("Category name")

    if not description:
        description = typer.prompt("Category description (optional)", default="")

    try:
        # Get user
        user = resolve_cli_user(user_input)

        # Get repository based on store
        if store == "local":
            session = get_session()
            repository = get_category_repository(user, store="local", session=session)
        elif store == "msgraph":
            access_token = get_cached_access_token()
            if not access_token:
                console.print(
                    "[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]"
                )
                raise typer.Exit(code=1)
            graph_client = get_graph_client(user, access_token)
            repository = get_category_repository(
                user, store="msgraph", msgraph_client=graph_client
            )
        else:
            console.print(
                f"[red]Invalid store '{store}'. Must be 'local' or 'msgraph'.[/red]"
            )
            raise typer.Exit(code=1)

        service = CategoryService(repository)

        category = Category(
            user_id=user.id,
            name=name.strip(),
            description=description.strip() if description else None,
        )

        service.create(category)
        console.print(
            f"[green]Category '{name}' created successfully in {store} store.[/green]"
        )

    except Exception as e:
        console.print(f"[red]Error creating category: {e}[/red]")
        raise typer.Exit(code=1)


@category_app.command("edit")
def edit_category(
    user_input: Optional[str] = user_option,
    store: str = typer.Option(
        "local",
        "--store",
        help="Category store: local or msgraph.",
        show_default=True,
        case_sensitive=False,
        autocompletion=lambda ctx, args, incomplete: [
            d for d in ["local", "msgraph"] if d.startswith(incomplete.lower())
        ],
    ),
    category_id: str = typer.Option(..., "--id", help="Category ID to edit"),
    name: str = typer.Option(None, "--name", help="New category name"),
    description: str = typer.Option(
        None, "--description", help="New category description"
    ),
):
    """Edit an existing category in the specified store."""
    from core.repositories import get_category_repository
    from core.services.category_service import CategoryService

    console = Console()

    try:
        # Get user
        user = resolve_cli_user(user_input)

        # Get repository based on store
        if store == "local":
            session = get_session()
            repository = get_category_repository(user, store="local", session=session)
        elif store == "msgraph":
            access_token = get_cached_access_token()
            if not access_token:
                console.print(
                    "[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]"
                )
                raise typer.Exit(code=1)
            graph_client = get_graph_client(user, access_token)
            repository = get_category_repository(
                user, store="msgraph", msgraph_client=graph_client
            )
        else:
            console.print(
                f"[red]Invalid store '{store}'. Must be 'local' or 'msgraph'.[/red]"
            )
            raise typer.Exit(code=1)

        service = CategoryService(repository)
        category = service.get_by_id(category_id)

        if not category:
            console.print(
                f"[red]Category {category_id} not found for user {user.id} ({user.username or user.email}) in {store} store.[/red]"
            )
            raise typer.Exit(code=1)

        # Update fields if provided
        if name is not None:
            category.name = name.strip()

        if description is not None:
            category.description = description.strip() if description else None

        service.update(category)
        console.print(
            f"[green]Category {category_id} updated successfully in {store} store.[/green]"
        )

    except Exception as e:
        console.print(f"[red]Error updating category: {e}[/red]")
        raise typer.Exit(code=1)


@category_app.command("delete")
def delete_category(
    user_input: Optional[str] = user_option,
    store: str = typer.Option(
        "local",
        "--store",
        help="Category store: local or msgraph.",
        show_default=True,
        case_sensitive=False,
        autocompletion=lambda ctx, args, incomplete: [
            d for d in ["local", "msgraph"] if d.startswith(incomplete.lower())
        ],
    ),
    category_id: str = typer.Option(..., "--id", help="Category ID to delete"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
):
    """Delete a category from the specified store."""
    from core.repositories import get_category_repository
    from core.services.category_service import CategoryService

    console = Console()

    try:
        # Get user
        user = resolve_cli_user(user_input)

        # Get repository based on store
        if store == "local":
            session = get_session()
            repository = get_category_repository(user, store="local", session=session)
        elif store == "msgraph":
            access_token = get_cached_access_token()
            if not access_token:
                console.print(
                    "[yellow]No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.[/yellow]"
                )
                raise typer.Exit(code=1)
            graph_client = get_graph_client(user, access_token)
            repository = get_category_repository(
                user, store="msgraph", msgraph_client=graph_client
            )
        else:
            console.print(
                f"[red]Invalid store '{store}'. Must be 'local' or 'msgraph'.[/red]"
            )
            raise typer.Exit(code=1)

        service = CategoryService(repository)
        category = service.get_by_id(category_id)

        if not category:
            console.print(
                f"[red]Category {category_id} not found for user {user.id} ({user.username or user.email}) in {store} store.[/red]"
            )
            raise typer.Exit(code=1)

        if not confirm:
            delete_confirm = typer.confirm(
                f"Are you sure you want to delete category '{category.name}' from {store} store?"
            )
            if not delete_confirm:
                console.print("[yellow]Category deletion cancelled.[/yellow]")
                return

        service.delete(category_id)
        console.print(
            f"[green]Category '{category.name}' deleted successfully from {store} store.[/green]"
        )

    except Exception as e:
        console.print(f"[red]Error deleting category: {e}[/red]")
        raise typer.Exit(code=1)


@category_app.command("validate")
def validate_category(
    user_input: Optional[str] = user_option,
    start_date: str = typer.Option(
        None, help="Start date (YYYY-MM-DD or flexible format)"
    ),
    end_date: str = typer.Option(None, help="End date (YYYY-MM-DD or flexible format)"),
    show_stats: bool = typer.Option(
        True, "--stats/--no-stats", help="Show category statistics"
    ),
    show_issues: bool = typer.Option(
        True, "--issues/--no-issues", help="Show validation issues"
    ),
):
    """Validate appointment categories for a user and date range."""
    from datetime import datetime, timezone

    from core.models.appointment import Appointment
    from core.services.category_processing_service import CategoryProcessingService

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
            f"[blue]Validating categories for user {user.id} ({user.username or user.email}) from {start_dt} to {end_dt}[/blue]"
        )

        # Get appointments directly from database for all calendars
        from core.models.appointment import Appointment

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

        # Validate categories
        category_service = CategoryProcessingService()
        stats = category_service.get_category_statistics(appointments)

        if show_stats:
            # Display statistics table
            stats_table = Table(title="Category Validation Statistics")
            stats_table.add_column("Metric", style="cyan")
            stats_table.add_column("Value", style="green")

            stats_table.add_row("Total Appointments", str(stats["total_appointments"]))
            stats_table.add_row(
                "Appointments with Categories",
                str(stats["appointments_with_categories"]),
            )
            stats_table.add_row(
                "Personal Appointments", str(stats["personal_appointments"])
            )
            stats_table.add_row("Valid Categories", str(stats["valid_categories"]))
            stats_table.add_row("Invalid Categories", str(stats["invalid_categories"]))
            stats_table.add_row("Unique Customers", str(len(stats["customers"])))

            console.print(stats_table)

            # Display customers and billing types
            if stats["customers"]:
                console.print(
                    f"\n[bold]Customers found:[/bold] {', '.join(sorted(stats['customers']))}"
                )

            if stats["billing_types"]:
                billing_summary = ", ".join(
                    [f"{bt}: {count}" for bt, count in stats["billing_types"].items()]
                )
                console.print(f"[bold]Billing types:[/bold] {billing_summary}")

        if show_issues and stats["issues"]:
            # Display validation issues
            issues_table = Table(title="Validation Issues")
            issues_table.add_column("Issue", style="red")

            for issue in stats["issues"][:20]:  # Limit to first 20 issues
                issues_table.add_row(issue)

            if len(stats["issues"]) > 20:
                issues_table.add_row(f"... and {len(stats['issues']) - 20} more issues")

            console.print(issues_table)

        # Summary
        if stats["invalid_categories"] > 0:
            console.print(
                f"\n[red]Found {stats['invalid_categories']} appointments with invalid categories.[/red]"
            )
            console.print(
                "[yellow]Consider fixing these categories to improve timesheet accuracy.[/yellow]"
            )
        else:
            console.print("\n[green]All appointments have valid categories! ✓[/green]")

    except Exception as e:
        console.print(f"[red]Error validating categories: {e}[/red]")
        raise typer.Exit(code=1)
