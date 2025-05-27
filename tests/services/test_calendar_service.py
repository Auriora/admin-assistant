import os
import json
from datetime import datetime, timedelta, UTC
import pytest
from app import create_app
from app.services.calendar_service import CalendarService

@pytest.mark.skipif(not os.getenv('RUN_REAL_MS365_TESTS'), reason="Real MS365 test skipped unless RUN_REAL_MS365_TESTS is set.")
def test_fetch_and_save_ms365_calendar_data():
    app = create_app()
    with app.app_context():
        from app.models import User
        user = User.query.first()
        assert user, "No user found in DB."
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=6)
        appointments = CalendarService.fetch_appointments_from_ms365(user, start_date, end_date)
        assert isinstance(appointments, list)
        os.makedirs('tests/data', exist_ok=True)
        with open('tests/data/ms365_calendar_sample.json', 'w') as f:
            json.dump(appointments, f, indent=2, default=str)
        print(f"Saved {len(appointments)} appointments to tests/data/ms365_calendar_sample.json") 