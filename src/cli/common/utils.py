"""Common CLI utilities for date parsing, user resolution, and other shared functions."""

import calendar
import locale
import re
from datetime import date, datetime, timedelta
from typing import Optional, Tuple

import typer
from core.models.user import User
from core.utilities.user_resolution import get_user_identifier_source, resolve_user


def resolve_cli_user(cli_user_input: Optional[str] = None) -> User:
    """
    Resolve user from CLI input with proper error handling.

    Args:
        cli_user_input: User identifier from CLI (username or user ID)

    Returns:
        User object

    Raises:
        typer.Exit: If user cannot be resolved
    """
    try:
        user = resolve_user(cli_user_input)
        if not user:
            source = get_user_identifier_source(cli_user_input)
            typer.echo(f"No user identifier found from {source}.")
            typer.echo(
                "Please specify --user <username_or_id> or set ADMIN_ASSISTANT_USER environment variable."
            )
            raise typer.Exit(code=1)
        return user
    except ValueError as e:
        source = get_user_identifier_source(cli_user_input)
        typer.echo(f"Error resolving user from {source}: {e}")
        raise typer.Exit(code=1)


def get_week_start_day() -> int:
    """
    Get the first day of the week based on locale settings.
    Returns 0 for Monday, 6 for Sunday (Python calendar module convention).
    Falls back to Monday if locale detection fails.
    """
    try:
        # Try to get locale-specific first day of week
        # This is a bit tricky as Python's locale module doesn't directly expose this
        # We'll use a simple heuristic: if locale is US-based, assume Sunday start
        current_locale = locale.getlocale()[0] or ""
        if "US" in current_locale.upper() or "en_US" in current_locale:
            return 6  # Sunday
        else:
            return 0  # Monday (ISO standard)
    except:
        return 0  # Default to Monday


def get_last_week_range(reference_date: date = None) -> tuple[date, date]:
    """
    Get the date range for the previous calendar week.

    Args:
        reference_date: Reference date (defaults to yesterday)

    Returns:
        Tuple of (start_date, end_date) for the previous week
    """
    if reference_date is None:
        reference_date = datetime.now().date() - timedelta(days=1)

    # Get the first day of the week (0=Monday, 6=Sunday)
    week_start = get_week_start_day()

    # Find the start of the current week
    days_since_week_start = (reference_date.weekday() - week_start) % 7
    current_week_start = reference_date - timedelta(days=days_since_week_start)

    # Previous week is 7 days before current week start
    last_week_start = current_week_start - timedelta(days=7)
    last_week_end = last_week_start + timedelta(days=6)

    return last_week_start, last_week_end


def get_last_month_range(reference_date: date = None) -> tuple[date, date]:
    """
    Get the date range for the previous calendar month.

    Args:
        reference_date: Reference date (defaults to yesterday)

    Returns:
        Tuple of (start_date, end_date) for the previous month
    """
    if reference_date is None:
        reference_date = datetime.now().date() - timedelta(days=1)

    # Get the first day of the current month
    current_month_start = reference_date.replace(day=1)

    # Get the last day of the previous month
    last_month_end = current_month_start - timedelta(days=1)

    # Get the first day of the previous month
    last_month_start = last_month_end.replace(day=1)

    return last_month_start, last_month_end


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

    Note:
    - 'last X days' periods are calculated backward from yesterday
    - 'last week' refers to the previous calendar week (Sunday-Saturday or Monday-Sunday based on locale)
    - 'last month' refers to the previous calendar month

    Returns (start_date, end_date) as date objects.
    """
    date_str = (date_str or "yesterday").strip().lower()
    now = datetime.now().date()
    yesterday = now - timedelta(days=1)
    # Phrases
    if date_str in ("today",):
        return now, now
    if date_str in ("yesterday",):
        return yesterday, yesterday
    if date_str in ("last 7 days",):
        end = yesterday
        start = yesterday - timedelta(days=6)
        return start, end
    if date_str in ("last week",):
        return get_last_week_range(yesterday)
    if date_str in ("last 30 days",):
        end = yesterday
        start = yesterday - timedelta(days=29)
        return start, end
    if date_str in ("last month",):
        return get_last_month_range(yesterday)
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
