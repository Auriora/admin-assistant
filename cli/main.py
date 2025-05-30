"""
CLI entry point for Admin Assistant using Typer.

Commands:
- calendar archive <start_date> <end_date>: Manually trigger calendar archiving
- calendar travel auto-plan: Auto-plan travel
- calendar timesheet export -o [PDF|CSV]: Export timesheet data
- calendar timesheet upload --destination Xero: Upload timesheet

This CLI is intended for both end users and administrators, supporting automation and scripting.
"""
import typer
from typing import Optional
import os
from datetime import datetime
from core.orchestrators.archive_job_runner import ArchiveJobRunner
from core.utilities import get_graph_client
from core.db import get_session

app = typer.Typer(help="Admin Assistant CLI")
calendar_app = typer.Typer(help="Calendar operations")
timesheet_app = typer.Typer(help="Timesheet operations")

@app.callback()
def main():
    """Admin Assistant CLI."""
    pass

@calendar_app.command("archive")
def archive(
    start_date: Optional[str] = typer.Option(None, help="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, help="End date (YYYY-MM-DD)")
):
    """Manually trigger calendar archiving for the configured user (always live)."""
    user_id = int(os.getenv("ADMIN_ASSISTANT_USER_ID", "1"))
    runner = ArchiveJobRunner()
    session = get_session()
    # Parse dates
    start_dt = None
    end_dt = None
    try:
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        # If neither is provided, default to yesterday for both
        if not start_dt and not end_dt:
            from datetime import timedelta
            yesterday = datetime.now().date() - timedelta(days=1)
            start_dt = end_dt = yesterday
    except Exception as e:
        typer.echo(f"Error parsing dates: {e}")
        raise typer.Exit(code=1)
    try:
        from core.services import UserService
        user_service = UserService()
        user = user_service.get_by_id(user_id)
        if not user:
            typer.echo(f"No user found in user DB for user_id={user_id}.")
            raise typer.Exit(code=1)
        graph_client = get_graph_client(user=user, session=session)
        result = runner.run_archive_job(
            user_id=user_id,
            use_live=True,
            graph_client=graph_client,
            session=session,
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

calendar_app.add_typer(timesheet_app, name="timesheet")

@timesheet_app.command("export")
def export(
    output: str = typer.Option("PDF", "--output", "-o", help="Output format: PDF or CSV")
):
    """Export timesheet data."""
    typer.echo(f"Exporting timesheet as {output}")

@timesheet_app.command("upload")
def upload(destination: str = typer.Option(..., help="Upload destination (e.g., Xero)")):
    """Upload timesheet."""
    typer.echo(f"Uploading timesheet to {destination}")

app.add_typer(calendar_app, name="calendar")

if __name__ == "__main__":
    app() 