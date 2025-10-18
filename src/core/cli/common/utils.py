import locale
from datetime import date, datetime, timedelta
from typing import Optional, Tuple, List

from core.utilities import uri_utility as uu


# Re-export relevant exceptions so tests can reference them as cu.URIParseError etc.
URIParseError = uu.URIParseError
URIValidationError = uu.URIValidationError


def get_week_start_day() -> int:
    """Return week start day as integer (0=Monday ... 6=Sunday).

    Heuristic: US locales start week on Sunday, most others on Monday.
    """
    try:
        loc = locale.getlocale()[0]
    except Exception:
        loc = None

    if loc and loc.endswith('_US'):
        return 6
    return 0


def get_last_week_range(reference_date: Optional[date] = None) -> Tuple[date, date]:
    """Return start and end date of the previous week relative to reference_date.

    Week start is determined by get_week_start_day(). The returned range covers
    the full previous week (7 days).
    """
    if reference_date is None:
        reference_date = date.today()

    start_day = get_week_start_day()  # 0..6
    # Python weekday(): Monday=0 .. Sunday=6
    ref_wd = reference_date.weekday()
    # Compute start of current week containing reference_date
    days_from_week_start = (ref_wd - start_day) % 7
    current_week_start = reference_date - timedelta(days=days_from_week_start)
    prev_week_start = current_week_start - timedelta(days=7)
    prev_week_end = prev_week_start + timedelta(days=6)
    return prev_week_start, prev_week_end


def get_last_month_range(reference_date: Optional[date] = None) -> Tuple[date, date]:
    """Return (first_day_last_month, last_day_last_month).
    """
    if reference_date is None:
        reference_date = date.today()

    year = reference_date.year
    month = reference_date.month
    # move to first day of current month
    first_current = date(year, month, 1)
    # last day of previous month is day before first_current
    last_prev = first_current - timedelta(days=1)
    first_prev = date(last_prev.year, last_prev.month, 1)
    return first_prev, last_prev


def parse_flexible_date(s: str) -> date:
    """Parse several common human date formats into a date object.

    Supported:
    - ISO: YYYY-MM-DD
    - D-M-YYYY or D/M/YYYY
    - D-MMM (e.g., 1-Oct) (defaults to current year)
    - D-MMM-YYYY or D-MONTH-YYYY
    """
    if not s or not s.strip():
        raise ValueError('Empty date string')

    s = s.strip()
    now_year = date.today().year

    # Try ISO first
    formats = [
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%d-%b-%Y',
        '%d-%B-%Y',
        '%d-%b',
        '%d-%B',
        '%d-%m',
        '%d/%m',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            if '%Y' not in fmt:
                # no year supplied -> use current year
                return date(now_year, dt.month, dt.day)
            return dt.date()
        except Exception:
            continue

    # Final attempt: try parsing with datetime.fromisoformat
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        pass

    raise ValueError(f"Unrecognized date format: {s}")


def parse_date_range(s: str) -> Tuple[date, date]:
    """Parse a date range string like '01-10-2025 to 03-10-2025'.

    Returns (start_date, end_date).
    """
    if not s or not s.strip():
        raise ValueError('Empty range string')

    # Accept separators like ' to ' or '-' with ' to ' preferred
    sep = ' to '
    if sep in s:
        parts = s.split(sep)
    elif ' - ' in s:
        parts = s.split(' - ')
    else:
        # fallback: try single date
        d = parse_flexible_date(s)
        return d, d

    if len(parts) != 2:
        raise ValueError('Range must contain two dates')

    start = parse_flexible_date(parts[0].strip())
    end = parse_flexible_date(parts[1].strip())
    return start, end


def get_account_context_for_user(user) -> str:
    """Return best account context for a user: email, then username, then id."""
    if getattr(user, 'email', None):
        email = str(user.email).strip()
        if email:
            return email
    if getattr(user, 'username', None):
        uname = str(user.username).strip()
        if uname:
            return uname
    return str(getattr(user, 'id', ''))


def suggest_uri_with_account_context(uri: str, user) -> str:
    """If URI lacks an account, return a constructed URI with the user's account context.

    If parsing fails, return the original URI.
    """
    try:
        parsed = parse_resource_uri(uri)
    except Exception:
        # If the caller expects original on parse error, return original
        return uri

    if getattr(parsed, 'account', None):
        return uri

    account = get_account_context_for_user(user)
    try:
        return construct_resource_uri(parsed.scheme, parsed.namespace, parsed.identifier, user_friendly=True, account=account)
    except Exception:
        return uri


def validate_uri_account_context(uri: str, user) -> Tuple[bool, Optional[str]]:
    """Validate that the account in uri (if present) matches the user context.

    Returns (ok, error_message_or_None).
    """
    try:
        parsed = parse_resource_uri(uri)
    except URIParseError as e:
        return False, f"Invalid URI format: {e}"
    except Exception as e:
        return False, f"Invalid URI format: {e}"

    acct = getattr(parsed, 'account', None)
    if not acct:
        # No account in URI -> treat as valid (context-free)
        return True, None

    # Compare against user's email, username, or id
    try:
        user_email = (user.email or '').lower()
    except Exception:
        user_email = ''
    try:
        user_name = (user.username or '').lower()
    except Exception:
        user_name = ''
    try:
        user_id = str(getattr(user, 'id', '') )
    except Exception:
        user_id = ''

    acct_l = str(acct).lower()
    if acct_l == user_email and user_email:
        return True, None
    if acct_l == user_name and user_name:
        return True, None
    if acct == user_id and user_id:
        return True, None

    return False, f"URI account '{acct}' does not match user context"


# Thin wrappers to the uri_utility functions so tests can monkeypatch these names
def parse_resource_uri(uri: str):
    return uu.parse_resource_uri(uri)


def construct_resource_uri(scheme: str, namespace: str, identifier: str, user_friendly: bool = True, account: Optional[str] = None) -> str:
    return uu.construct_resource_uri(scheme, namespace, identifier, user_friendly=user_friendly, account=account)


def get_uri_autocompletion_suggestions(user) -> List[str]:
    suggestions: List[str] = []
    acct = get_account_context_for_user(user)

    # Prefer msgraph suggestions (most common in tests)
    if acct:
        suggestions.append(f"msgraph://{acct}/calendars/primary")
        suggestions.append(f"msgraph://{acct}/calendars/")
        suggestions.append(f"msgraph://{acct}/contacts/")
    # Generic legacy suggestions
    suggestions.append("msgraph://calendars/primary")
    suggestions.append("msgraph://calendars/")

    # Include namespace-only suggestions
    suggestions.append("calendars")
    suggestions.append("contacts")

    return suggestions

