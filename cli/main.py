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

app = typer.Typer(help="Admin Assistant CLI")
calendar_app = typer.Typer(help="Calendar operations")
timesheet_app = typer.Typer(help="Timesheet operations")

@app.callback()
def main():
    """Admin Assistant CLI."""
    pass

@calendar_app.command("archive")
def archive(
    start_date: Optional[str] = typer.Argument(None, help="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Argument(None, help="End date (YYYY-MM-DD)")
):
    """Manually trigger calendar archiving."""
    typer.echo(f"Archiving from {start_date or 'today'} to {end_date or 'today'}")

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