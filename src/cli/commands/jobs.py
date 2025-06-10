"""Background job management commands."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cli.common.options import user_option
from cli.common.utils import resolve_cli_user

jobs_app = typer.Typer(help="Background job management")


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
