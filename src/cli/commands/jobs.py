"""Background job management commands."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cli.common.options import user_option
from cli.common.utils import resolve_cli_user, parse_date_range

jobs_app = typer.Typer(help="Background job management", rich_markup_mode="rich")


@jobs_app.command("schedule")
def schedule_archive_job(
    user_input: Optional[str] = user_option,
    schedule_type: str = typer.Option("daily", "--type", help="Schedule type (daily or weekly)"),
    hour: int = typer.Option(23, "--hour", help="Hour to run (0-23)"),
    minute: int = typer.Option(59, "--minute", help="Minute to run (0-59)"),
    day_of_week: Optional[int] = typer.Option(None, "--day", help="Day of week for weekly jobs (0=Monday, 6=Sunday)")
):
    """Schedule recurring archive jobs for a user."""
    from flask_apscheduler import APScheduler
    from core.services.background_job_service import BackgroundJobService
    from core.services.scheduled_archive_service import ScheduledArchiveService

    console = Console()

    try:
        # Validate schedule type
        if schedule_type not in ["daily", "weekly"]:
            console.print(f"[red]Invalid schedule type: {schedule_type}. Must be 'daily' or 'weekly'.[/red]")
            raise typer.Exit(code=1)

        user = resolve_cli_user(user_input)

        # Initialize services
        scheduler = APScheduler()
        bg_service = BackgroundJobService(scheduler)
        scheduled_service = ScheduledArchiveService()

        # Schedule the jobs
        result = scheduled_service.update_user_schedule(
            user_id=user.id,
            schedule_type=schedule_type,
            hour=hour,
            minute=minute,
            day_of_week=day_of_week
        )

        if not result["updated_jobs"]:
            console.print("[yellow]No active archive configurations found for user. No jobs scheduled.[/yellow]")
            return

        console.print(f"[green]Successfully scheduled jobs for user {user.username or user.email}:[/green]")
        for job in result["updated_jobs"]:
            console.print(f"  • Job ID: {job['job_id']}")
            console.print(f"    Config: {job['config_name']} (ID: {job['config_id']})")
            console.print(f"    Schedule: {job['schedule_type']}")

        if result["failed_jobs"]:
            console.print("[yellow]Some jobs failed to schedule:[/yellow]")
            for failed in result["failed_jobs"]:
                console.print(f"  • {failed}")

    except Exception as e:
        console.print(f"[red]Failed to schedule jobs: {e}[/red]")
        raise typer.Exit(code=1)


@jobs_app.command("trigger")
def trigger_manual_archive(
    user_input: Optional[str] = user_option,
    start_date: Optional[str] = typer.Option(None, "--start", help="Start date for archive"),
    end_date: Optional[str] = typer.Option(None, "--end", help="End date for archive"),
    config_id: Optional[int] = typer.Option(None, "--config", help="Archive configuration ID")
):
    """Trigger a manual archive job."""
    from flask_apscheduler import APScheduler
    from core.services.background_job_service import BackgroundJobService
    from core.services.archive_configuration_service import ArchiveConfigurationService

    console = Console()

    try:
        user = resolve_cli_user(user_input)

        # Parse date range if provided
        if start_date and end_date:
            from cli.common.utils import parse_flexible_date
            start = parse_flexible_date(start_date)
            end = parse_flexible_date(end_date)
        elif start_date:
            start, end = parse_date_range(start_date)
        else:
            start, end = parse_date_range("yesterday")

        # Get archive configuration
        archive_service = ArchiveConfigurationService()
        if config_id:
            config = archive_service.get_by_id(config_id)
            if not config or config.user_id != user.id:
                console.print(f"[red]Archive configuration {config_id} not found for user.[/red]")
                raise typer.Exit(code=1)
        else:
            config = archive_service.get_active_config_for_user(user.id)
            if not config:
                console.print("[red]No active archive configuration found for user.[/red]")
                raise typer.Exit(code=1)

        # Initialize services and trigger job
        scheduler = APScheduler()
        bg_service = BackgroundJobService(scheduler)

        job_id = bg_service.trigger_manual_archive(
            user_id=user.id,
            config_id=config.id,
            start_date=start,
            end_date=end
        )

        console.print(f"[green]Manual archive job triggered successfully![/green]")
        console.print(f"Job ID: {job_id}")
        console.print(f"User: {user.username or user.email}")
        console.print(f"Config: {config.name}")
        console.print(f"Date range: {start} to {end}")

    except Exception as e:
        console.print(f"[red]Failed to trigger manual archive: {e}[/red]")
        raise typer.Exit(code=1)


@jobs_app.command("remove")
def remove_scheduled_jobs(
    user_input: Optional[str] = user_option,
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt")
):
    """Remove all scheduled jobs for a user."""
    from flask_apscheduler import APScheduler
    from core.services.background_job_service import BackgroundJobService
    from core.services.scheduled_archive_service import ScheduledArchiveService

    console = Console()

    try:
        user = resolve_cli_user(user_input)

        # Confirmation prompt unless --confirm is used
        if not confirm:
            confirm_removal = typer.confirm(
                f"Are you sure you want to remove all scheduled jobs for user {user.username or user.email}?"
            )
            if not confirm_removal:
                console.print("[yellow]Operation cancelled.[/yellow]")
                return

        # Initialize services
        scheduler = APScheduler()
        bg_service = BackgroundJobService(scheduler)
        scheduled_service = ScheduledArchiveService()

        # Remove jobs
        result = scheduled_service.remove_user_schedule(user.id)

        if result["removed_jobs"]:
            console.print(f"[green]Successfully removed jobs for user {user.username or user.email}:[/green]")
            for job_id in result["removed_jobs"]:
                console.print(f"  • {job_id}")
        else:
            console.print("[yellow]No scheduled jobs found to remove.[/yellow]")

        if result["failed_removals"]:
            console.print("[yellow]Some jobs failed to remove:[/yellow]")
            for failed in result["failed_removals"]:
                console.print(f"  • {failed}")

    except Exception as e:
        console.print(f"[red]Failed to remove scheduled jobs: {e}[/red]")
        raise typer.Exit(code=1)


@jobs_app.command("status")
def get_job_status(user_input: Optional[str] = user_option):
    """Get job status for a user."""
    from flask_apscheduler import APScheduler

    console = Console()

    try:
        user = resolve_cli_user(user_input)

        # Initialize scheduler to check status
        scheduler = APScheduler()

        # Get all jobs
        jobs = scheduler.get_jobs()

        if not jobs:
            console.print("[yellow]No scheduled jobs found.[/yellow]")
            return

        # Filter jobs for this user (if job ID contains user info)
        user_jobs = [job for job in jobs if str(user.id) in job.id]

        if not user_jobs:
            console.print(f"[yellow]No scheduled jobs found for user {user.id} ({user.username or user.email}).[/yellow]")
            return

        table = Table(title=f"Scheduled Jobs for {user.username or user.email}")
        table.add_column("Job ID", style="cyan")
        table.add_column("Function", style="green")
        table.add_column("Trigger", style="yellow")
        table.add_column("Next Run", style="blue")

        for job in user_jobs:
            table.add_row(
                job.id,
                job.func_ref,
                str(job.trigger),
                str(job.next_run_time) if job.next_run_time else "N/A"
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Failed to get job status: {e}[/red]")
        raise typer.Exit(code=1)


@jobs_app.command("health")
def job_health_check():
    """Perform health check on the job scheduling system."""
    from flask_apscheduler import APScheduler

    console = Console()

    try:
        scheduler = APScheduler()

        # Basic health checks
        health_table = Table(title="Job System Health Check")
        health_table.add_column("Component", style="cyan")
        health_table.add_column("Status", style="green")
        health_table.add_column("Details", style="yellow")

        # Check if scheduler is running
        try:
            jobs = scheduler.get_jobs()
            health_table.add_row("Scheduler", "✓ Running", f"{len(jobs)} jobs scheduled")
        except Exception as e:
            health_table.add_row("Scheduler", "✗ Error", str(e))

        # Check database connectivity
        try:
            from core.db import get_session
            session = get_session()
            session.execute("SELECT 1")
            health_table.add_row("Database", "✓ Connected", "Connection successful")
        except Exception as e:
            health_table.add_row("Database", "✗ Error", str(e))

        console.print(health_table)

    except Exception as e:
        console.print(f"[red]Health check failed: {e}[/red]")
        raise typer.Exit(code=1)
