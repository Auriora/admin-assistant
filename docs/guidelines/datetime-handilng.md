# UTC DateTime Handling in admin-assistant

## Project-wide Rule
All datetimes in the database must be stored in UTC and always returned as UTC-aware (with tzinfo=timezone.utc), regardless of the database backend (SQLite, Postgres, MySQL, etc.).

## Implementation
A custom SQLAlchemy type, `UTCDateTime`, is used for all datetime columns. This type:
- Converts all datetimes to UTC before storing (removes tzinfo for DB storage).
- Attaches tzinfo=timezone.utc to all datetimes when loading from the DB.
- Ensures consistent, portable datetime handling across all environments.

## Usage
In all models, use:
```python
from core.models.appointment import UTCDateTime
start_time = Column(UTCDateTime(), nullable=False)
```

## Rationale
- SQLite does not store timezone info, so naive datetimes are returned by default.
- This approach guarantees that all datetimes in the app are UTC-aware, preventing subtle bugs and making code portable.
- All contributors must use `UTCDateTime` for any new datetime columns.

## References
- See `core/models/appointment.py` for the implementation.
- See the AI code generation guidelines for further requirements. 