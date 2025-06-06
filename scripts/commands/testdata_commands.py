#!/usr/bin/env python3
"""
Test data generation commands for the admin-assistant project.
"""
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

console = Console()

# Create test data CLI app
testdata_app = typer.Typer(
    name="testdata",
    help="Test data generation commands",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@testdata_app.command()
def appointments(
    user_email: str = typer.Option(
        "bcherrington.993834@outlook.com",
        "--user-email",
        "-u",
        help="User email for the Outlook account"
    ),
    days_back: int = typer.Option(
        30,
        "--days-back",
        "-b",
        help="Number of days back to create appointments"
    ),
    days_forward: int = typer.Option(
        30,
        "--days-forward",
        "-f",
        help="Number of days forward to create appointments"
    ),
    count: int = typer.Option(
        100,
        "--count",
        "-c",
        help="Total number of appointments to create"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be created without actually creating appointments"
    ),
    include_overlaps: bool = typer.Option(
        True,
        "--include-overlaps/--no-overlaps",
        help="Include overlapping appointments for testing conflict resolution"
    ),
    include_recurring: bool = typer.Option(
        True,
        "--include-recurring/--no-recurring",
        help="Include recurring appointments"
    ),
    include_private: bool = typer.Option(
        True,
        "--include-private/--no-private",
        help="Include private appointments"
    ),
    include_invalid_categories: bool = typer.Option(
        True,
        "--include-invalid-categories/--no-invalid-categories",
        help="Include appointments with invalid categories for testing validation"
    )
):
    """
    Generate comprehensive test appointments for system testing.
    
    Creates a diverse set of appointments covering all archiving and backup scenarios:
    - Various category types (billable, non-billable, special, invalid)
    - Different appointment types (regular, recurring, all-day, overlapping)
    - Multiple time scenarios and locations
    - Privacy and sensitivity variations
    """
    console.print(Panel.fit(
        f"[bold blue]Generating Test Appointments[/bold blue]\n\n"
        f"User: {user_email}\n"
        f"Date Range: {days_back} days back to {days_forward} days forward\n"
        f"Total Count: {count}\n"
        f"Dry Run: {dry_run}",
        border_style="blue"
    ))
    
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No appointments will be created[/yellow]\n")
    
    try:
        from scripts.utils.appointment_generator import AppointmentGenerator
        
        generator = AppointmentGenerator(
            user_email=user_email,
            days_back=days_back,
            days_forward=days_forward,
            include_overlaps=include_overlaps,
            include_recurring=include_recurring,
            include_private=include_private,
            include_invalid_categories=include_invalid_categories
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating appointments...", total=None)
            
            result = generator.generate_appointments(count, dry_run=dry_run)
            
            progress.update(task, description="Complete!")
        
        # Display results
        console.print(f"\n[green]✓[/green] Generated {result['created']} appointments")
        
        if result.get('categories_created'):
            console.print(f"[green]✓[/green] Created {result['categories_created']} categories")
        
        if result.get('overlaps'):
            console.print(f"[yellow]⚠[/yellow] {result['overlaps']} overlapping appointments (intentional for testing)")
        
        if result.get('recurring'):
            console.print(f"[blue]ℹ[/blue] {result['recurring']} recurring appointment series")
        
        if result.get('private'):
            console.print(f"[magenta]🔒[/magenta] {result['private']} private appointments")
        
        if result.get('invalid_categories'):
            console.print(f"[red]⚠[/red] {result['invalid_categories']} appointments with invalid categories (for testing)")

        # Show modification statistics
        if result.get('modifications'):
            console.print(f"\n[bold]Modification Types Generated:[/bold]")
            if result.get('extensions'):
                console.print(f"[blue]📈[/blue] {result['extensions']} extension appointments")
            if result.get('shortenings'):
                console.print(f"[yellow]📉[/yellow] {result['shortenings']} shortening appointments")
            if result.get('early_starts'):
                console.print(f"[green]⏪[/green] {result['early_starts']} early start appointments")
            if result.get('late_starts'):
                console.print(f"[red]⏩[/red] {result['late_starts']} late start appointments")
            console.print(f"[cyan]🔧[/cyan] {result['modifications']} total modification appointments")

        if result.get('edge_cases'):
            console.print(f"[purple]⚡[/purple] {result['edge_cases']} edge case appointments")

        if result.get('boundary_cases'):
            console.print(f"[orange]🎯[/orange] {result['boundary_cases']} boundary case appointments")

        console.print(f"\n[dim]Appointments created in Outlook calendar for {user_email}[/dim]")
        
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependency: {e}")
        console.print("Make sure you're running from the project root with the virtual environment activated.")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error generating appointments:[/red] {e}")
        raise typer.Exit(1)


@testdata_app.command()
def categories(
    user_email: str = typer.Option(
        "bcherrington.993834@outlook.com",
        "--user-email",
        "-u",
        help="User email for the Outlook account"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be created without actually creating categories"
    )
):
    """
    Generate standard test categories for appointment testing.
    
    Creates a comprehensive set of categories following the admin-assistant format:
    - Customer Name - Billing Type format
    - Special categories (Admin, Break, Online)
    - Various customer types for realistic testing
    """
    console.print(Panel.fit(
        f"[bold blue]Generating Test Categories[/bold blue]\n\n"
        f"User: {user_email}\n"
        f"Dry Run: {dry_run}",
        border_style="blue"
    ))
    
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No categories will be created[/yellow]\n")
    
    try:
        from scripts.utils.category_generator import CategoryGenerator
        
        generator = CategoryGenerator(user_email=user_email)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating categories...", total=None)
            
            result = generator.generate_categories(dry_run=dry_run)
            
            progress.update(task, description="Complete!")
        
        # Display results
        console.print(f"\n[green]✓[/green] Generated {result['created']} categories")
        
        if result.get('existing'):
            console.print(f"[yellow]ℹ[/yellow] {result['existing']} categories already existed")
        
        console.print(f"\n[dim]Categories created in Outlook for {user_email}[/dim]")
        
        # Show created categories
        if result.get('categories'):
            console.print("\n[bold]Created Categories:[/bold]")
            for category in result['categories']:
                console.print(f"  • {category}")
        
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependency: {e}")
        console.print("Make sure you're running from the project root with the virtual environment activated.")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error generating categories:[/red] {e}")
        raise typer.Exit(1)


@testdata_app.command()
def clear_appointments(
    user_email: str = typer.Option(
        "bcherrington.993834@outlook.com",
        "--user-email",
        "-u",
        help="User email for the Outlook account"
    ),
    confirm: bool = typer.Option(
        False,
        "--confirm",
        help="Confirm deletion without prompting"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be deleted without actually deleting"
    )
):
    """
    Clear all appointments from the Outlook calendar.

    This will delete ALL appointments in a wide date range (2 years back to 2 years forward).
    Use with caution - this will delete all appointments!
    """
    if not dry_run and not confirm:
        if not typer.confirm(
            f"This will delete ALL appointments for {user_email}. Are you sure?"
        ):
            console.print("Cancelled.")
            raise typer.Exit()

    console.print(Panel.fit(
        f"[bold red]Clearing All Appointments[/bold red]\n\n"
        f"User: {user_email}\n"
        f"Dry Run: {dry_run}",
        border_style="red"
    ))

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No appointments will be deleted[/yellow]\n")

    try:
        import asyncio
        from scripts.utils.clear_all_appointments import clear_all_appointments

        if dry_run:
            console.print("Would delete all appointments from calendar")
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Clearing appointments...", total=None)

            deleted_count = asyncio.run(clear_all_appointments(user_email))

            progress.update(task, description="Complete!")

        console.print(f"\n[green]✓[/green] Deleted {deleted_count} appointments")

    except Exception as e:
        console.print(f"[red]✗[/red] Error clearing appointments: {e}")
        raise typer.Exit(1)


@testdata_app.command()
def cleanup(
    user_email: str = typer.Option(
        "bcherrington.993834@outlook.com",
        "--user-email",
        "-u",
        help="User email for the Outlook account"
    ),
    confirm: bool = typer.Option(
        False,
        "--confirm",
        help="Confirm deletion without prompting"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be deleted without actually deleting"
    )
):
    """
    Clean up test appointments and categories.

    Removes test data created by the appointment and category generators.
    Use with caution - this will delete appointments!
    """
    if not dry_run and not confirm:
        if not typer.confirm(
            f"This will delete test appointments for {user_email}. Are you sure?"
        ):
            console.print("Cancelled.")
            raise typer.Exit()
    
    console.print(Panel.fit(
        f"[bold red]Cleaning Up Test Data[/bold red]\n\n"
        f"User: {user_email}\n"
        f"Dry Run: {dry_run}",
        border_style="red"
    ))
    
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No data will be deleted[/yellow]\n")
    
    try:
        from scripts.utils.test_data_cleanup import TestDataCleanup
        
        cleanup_tool = TestDataCleanup(user_email=user_email)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Cleaning up test data...", total=None)
            
            result = cleanup_tool.cleanup_test_data(dry_run=dry_run)
            
            progress.update(task, description="Complete!")
        
        # Display results
        console.print(f"\n[green]✓[/green] Deleted {result['appointments_deleted']} appointments")
        console.print(f"[green]✓[/green] Deleted {result['categories_deleted']} categories")
        
        console.print(f"\n[dim]Test data cleanup complete for {user_email}[/dim]")
        
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependency: {e}")
        console.print("Make sure you're running from the project root with the virtual environment activated.")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error cleaning up test data:[/red] {e}")
        raise typer.Exit(1)


@testdata_app.command()
def verify_appointments(
    user_email: str = typer.Option(
        "bcherrington.993834@outlook.com",
        "--user-email",
        "-u",
        help="User email for the Outlook account"
    ),
    show_details: bool = typer.Option(
        False,
        "--details",
        help="Show detailed appointment information"
    ),
    filter_modifications: bool = typer.Option(
        False,
        "--modifications-only",
        help="Show only modification-related appointments"
    )
):
    """
    Read back and verify appointments from the Outlook calendar.

    Shows statistics about appointment types and modification coverage.
    """
    console.print(Panel.fit(
        f"[bold blue]Verifying Appointments[/bold blue]\n\n"
        f"User: {user_email}\n"
        f"Show Details: {show_details}\n"
        f"Filter Modifications: {filter_modifications}",
        border_style="blue"
    ))

    try:
        import asyncio
        from datetime import datetime, timedelta, timezone
        from core.models.user import User
        from core.repositories.user_repository import UserRepository
        from core.repositories.appointment_repository_msgraph import MSGraphAppointmentRepository
        from core.db import SessionLocal
        from core.utilities.auth_utility import get_cached_access_token
        from core.utilities.graph_utility import get_graph_client
        from core.services.meeting_modification_service import MeetingModificationService

        async def verify_appointments_async():
            session = SessionLocal()
            try:
                user_repo = UserRepository(session)
                user = user_repo.get_by_email(user_email)

                if not user:
                    raise ValueError(f"User not found: {user_email}")

                # Get MS Graph access token and create client
                access_token = get_cached_access_token()
                if not access_token:
                    raise ValueError("No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.")

                graph_client = get_graph_client(user, access_token)
                appointment_repo = MSGraphAppointmentRepository(graph_client, user)

                # Get appointments from a wide date range
                start_date = (datetime.now(timezone.utc) - timedelta(days=90)).date()
                end_date = (datetime.now(timezone.utc) + timedelta(days=90)).date()

                appointments = await appointment_repo.alist_for_user(start_date, end_date)

                return appointments

            finally:
                session.close()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Reading appointments...", total=None)

            appointments = asyncio.run(verify_appointments_async())

            progress.update(task, description="Complete!")

        # Analyze appointments
        modification_service = MeetingModificationService()

        stats = {
            'total': len(appointments),
            'extensions': 0,
            'shortened': 0,
            'early_start': 0,
            'late_start': 0,
            'regular': 0,
            'overlaps': 0,
            'recurring': 0,
            'private': 0,
            'invalid_categories': 0,
            'edge_cases': 0,
            'modification_patterns': {}
        }

        modification_appointments = []
        regular_appointments = []

        for appt in appointments:
            subject = getattr(appt, 'subject', '')
            categories = getattr(appt, 'categories', [])
            sensitivity = getattr(appt, 'sensitivity', 'normal')

            # Check for modification type
            mod_type = modification_service.detect_modification_type(subject)
            if mod_type:
                stats[mod_type] += 1
                modification_appointments.append((mod_type, appt))

                # Track specific patterns
                if mod_type not in stats['modification_patterns']:
                    stats['modification_patterns'][mod_type] = []
                stats['modification_patterns'][mod_type].append(subject)
            else:
                stats['regular'] += 1
                regular_appointments.append(appt)

            # Check for other characteristics
            if sensitivity == 'private':
                stats['private'] += 1

            if 'Extended' in subject or 'Extension' in subject:
                stats['edge_cases'] += 1

            # Check for invalid categories (basic check)
            if categories:
                for cat in categories:
                    if cat and (' - ' not in cat or cat.count(' - ') != 1):
                        stats['invalid_categories'] += 1
                        break

        # Display results
        console.print(f"\n[green]✓[/green] Found {stats['total']} appointments")

        console.print("\n[bold]Modification Type Coverage:[/bold]")
        console.print(f"  Extensions: {stats['extensions']}")
        console.print(f"  Shortened: {stats['shortened']}")
        console.print(f"  Early Start: {stats['early_start']}")
        console.print(f"  Late Start: {stats['late_start']}")
        console.print(f"  Regular: {stats['regular']}")

        console.print(f"\n[bold]Other Statistics:[/bold]")
        console.print(f"  Private: {stats['private']}")
        console.print(f"  Edge Cases: {stats['edge_cases']}")
        console.print(f"  Invalid Categories: {stats['invalid_categories']}")

        if show_details and modification_appointments:
            console.print(f"\n[bold]Modification Appointments ({len(modification_appointments)}):[/bold]")
            for mod_type, appt in modification_appointments[:20]:  # Show first 20
                subject = getattr(appt, 'subject', 'Unknown')
                start_time = getattr(appt, 'start_time', 'Unknown')
                categories = getattr(appt, 'categories', [])
                console.print(f"  [{mod_type.upper()}] {subject} - {start_time} ({categories})")

            if len(modification_appointments) > 20:
                console.print(f"  ... and {len(modification_appointments) - 20} more")

        if filter_modifications:
            console.print(f"\n[bold]Modification Patterns Found:[/bold]")
            for mod_type, subjects in stats['modification_patterns'].items():
                console.print(f"  {mod_type.upper()}: {len(subjects)} appointments")
                for subject in set(subjects)[:5]:  # Show unique subjects, max 5
                    console.print(f"    - {subject}")
                if len(set(subjects)) > 5:
                    console.print(f"    ... and {len(set(subjects)) - 5} more patterns")

        # Coverage assessment
        required_types = ['extension', 'shortened', 'early_start', 'late_start']
        missing_types = [t for t in required_types if stats[t] == 0]

        if missing_types:
            console.print(f"\n[yellow]⚠[/yellow] Missing modification types: {', '.join(missing_types)}")
        else:
            console.print(f"\n[green]✓[/green] All modification types are covered!")

    except Exception as e:
        console.print(f"[red]✗[/red] Error verifying appointments: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    testdata_app()
