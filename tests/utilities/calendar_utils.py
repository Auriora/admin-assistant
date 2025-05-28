import json
from datetime import datetime, date
from typing import List, Dict, Tuple, Optional


def load_events_from_file(file_path: str) -> List[Dict]:
    """
    Load events from a JSON file.

    Args:
        file_path (str): Path to the JSON file containing event data.

    Returns:
        List[Dict]: List of event dictionaries loaded from the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_event_date_range(events: List[Dict]) -> Optional[Tuple[date, date]]:
    """
    Extract the minimum and maximum date from a list of event dictionaries.
    Assumes event dicts have 'start' and 'end' keys with 'dateTime' in ISO format.

    Args:
        events (List[Dict]): List of event dictionaries.

    Returns:
        Optional[Tuple[date, date]]: (min_date, max_date) if dates found, else None.
    """
    event_dates = []
    for event in events:
        for key in ('start', 'end'):
            dt_str = event.get(key, {}).get('dateTime')
            if dt_str:
                try:
                    # Handle 'Z' (UTC) by replacing with '+00:00'
                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    event_dates.append(dt.date())
                except Exception as e:
                    # Optionally log or handle parse errors
                    continue
    if event_dates:
        return min(event_dates), max(event_dates)
    return None 