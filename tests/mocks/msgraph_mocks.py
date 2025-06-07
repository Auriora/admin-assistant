"""
Mocks for Microsoft Graph API objects and client for testing purposes.
"""
from typing import Any, List, Optional
import re

class MockEventObj:
    """
    Mock object to simulate an event returned by the MS Graph API.
    """
    def __init__(self, data: dict) -> None:
        self.__dict__.update(data)

class MockEvents:
    """
    Mock object to simulate a paginated list of events from the MS Graph API.
    """
    def __init__(self, events: List[Any], odata_next_link: Optional[str] = None) -> None:
        self.value = [MockEventObj(e) if isinstance(e, dict) else e for e in events]
        self.odata_next_link = odata_next_link
        print(f"[MOCK DEBUG] MockEvents initialized with {len(self.value)} events. odata_next_link={self.odata_next_link}")
    async def get(self, *args, **kwargs) -> 'MockEvents':
        print(f"[MOCK DEBUG] MockEvents.get() called. Returning {len(self.value)} events. odata_next_link={self.odata_next_link}")
        return self

class MockCalendarView:
    """
    Mock object to simulate the calendarView endpoint with pagination.
    """
    def __init__(self, events: List[Any]) -> None:
        self._all_events = events
        self._url = None
        self._page_size = 5
        self._page_index = 0
        print(f"[MOCK DEBUG] MockCalendarView initialized.")
    def with_url(self, url: Optional[str]) -> 'MockCalendarView':
        self._url = url
        print(f"[MOCK DEBUG] MockCalendarView.with_url({url}) called.")
        if url and "mock://next_page/" in url:
            match = re.search(r"mock://next_page/(\d+)", url)
            if match:
                self._page_index = int(match.group(1))
            else:
                self._page_index = 0
        else:
            self._page_index = 0
        return self
    async def get(self, *args, **kwargs) -> MockEvents:
        print(f"[MOCK DEBUG] MockCalendarView.get() called for url={self._url} page_index={self._page_index}")
        page_size = self._page_size
        start = self._page_index * page_size
        end = start + page_size
        page_events = self._all_events[start:end]
        next_link = None
        if end < len(self._all_events):
            next_link = f"mock://next_page/{self._page_index+1}"
        return MockEvents(page_events, odata_next_link=next_link)

class MockCalendar:
    """
    Mock object to simulate a user's calendar with events and calendarView.
    """
    def __init__(self, events: List[Any]) -> None:
        print(f"[MOCK DEBUG] MockCalendar initialized.")
        self.events = MockEvents(events)
        self.calendar_view = MockCalendarView(events)

class MockCalendarItem:
    """
    Mock object to simulate a single calendar item for get, patch, delete.
    """
    def __init__(self, calendar_id=None, data=None):
        self.calendar_id = calendar_id
        self.data = data or {}
        self.get_called = False
        self.patch_called = False
        self.delete_called = False
    def get(self):
        self.get_called = True
        print(f"[MOCK DEBUG] MockCalendarItem.get() called for id={self.calendar_id}")
        # Return a simple namespace with expected calendar fields
        return type('MsCal', (), {
            'id': self.calendar_id,
            'name': self.data.get('name', 'Mock Calendar'),
            'description': self.data.get('description', 'Mock Desc'),
            'is_default': self.data.get('is_default', False)
        })()
    def patch(self, body):
        self.patch_called = True
        print(f"[MOCK DEBUG] MockCalendarItem.patch() called for id={self.calendar_id} body={body}")
    def delete(self):
        self.delete_called = True
        print(f"[MOCK DEBUG] MockCalendarItem.delete() called for id={self.calendar_id}")

class MockCalendars:
    """
    Mock object to simulate the calendars collection for a user.
    """
    def __init__(self):
        self._calendars = {}
        self.get_called = False
        self.post_called = False
    async def get(self, request_configuration=None):
        self.get_called = True
        print(f"[MOCK DEBUG] MockCalendars.get() called with request_configuration={request_configuration}")
        # Return a mock response with a 'value' attribute (list of calendars)
        return type('MsCalendars', (), {
            'value': [
                type('MsCal', (), {
                    'id': 'abc123',
                    'name': 'Mock Calendar',
                    'description': 'Mock Desc',
                    'is_default_calendar': True
                })()
            ]
        })()
    async def post(self, body):
        self.post_called = True
        print(f"[MOCK DEBUG] MockCalendars.post() called with body={body}")
        # Simulate adding a calendar
        cal_id = getattr(body, 'id', 'newid')
        self._calendars[cal_id] = body
    def by_calendar_id(self, calendar_id):
        print(f"[MOCK DEBUG] MockCalendars.by_calendar_id({calendar_id}) called.")
        return MockCalendarItem(calendar_id, self._calendars.get(calendar_id, {}))

class MockUser:
    """
    Mock object to simulate a user with a calendar.
    """
    def __init__(self, events: List[Any]) -> None:
        print(f"[MOCK DEBUG] MockUser initialized.")
        self.calendar = MockCalendar(events)
        self.calendars = MockCalendars()

class MockUsers:
    """
    Mock object to simulate the users endpoint for MS Graph API.
    """
    def __init__(self, events: List[Any]) -> None:
        self._events = events
        print(f"[MOCK DEBUG] MockUsers initialized.")
    def by_user_id(self, user_email: str) -> MockUser:
        print(f"[MOCK DEBUG] MockUsers.by_user_id({user_email}) called.")
        return MockUser(self._events)

class MockMSGraphClient:
    """
    Mock client to simulate the MS Graph API client for testing.
    """
    def __init__(self, events: List[Any]) -> None:
        print(f"[MOCK DEBUG] MockMSGraphClient initialized.")
        self.users = MockUsers(events) 