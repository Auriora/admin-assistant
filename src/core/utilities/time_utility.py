from datetime import datetime

import pytz


def to_utc(dt: datetime) -> datetime:
    """
    Convert a datetime to UTC.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=pytz.UTC)
    return dt.astimezone(pytz.UTC)
