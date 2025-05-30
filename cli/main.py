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
from datetime import datetime, timedelta, date
from core.orchestrators.archive_job_runner import ArchiveJobRunner
from core.utilities import get_graph_client
from core.db import get_session
import re

app = typer.Typer(help="Admin Assistant CLI for running calendar and timesheet operations.")
calendar_app = typer.Typer(help="Calendar operations")
timesheet_app = typer.Typer(help="Timesheet operations")

user_id_option = typer.Option(
    ...,
    "--user-id",
    help="User ID to operate on.",
    envvar="ADMIN_ASSISTANT_USER_ID",
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
def main():
    """Admin Assistant CLI."""
    pass

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
        from core.services import UserService
        user_service = UserService()
        user = user_service.get_by_id(user_id)
        if not user:
            typer.echo(f"No user found in user DB for user_id={user_id}.")
            raise typer.Exit(code=1)
        graph_client = get_graph_client(user=user, session=session)
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

calendar_app.add_typer(timesheet_app, name="timesheet")

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

app.add_typer(calendar_app, name="calendar")

if __name__ == "__main__":
    app() 
