"""
app/core/utils.py
-----------------
Shared utility functions reused across multiple services.
"""
from datetime import datetime, timezone


def ensure_utc(dt: datetime) -> datetime:
    """Return a UTC-aware datetime regardless of whether the input is naive or aware.

    SQLite (test database) stores datetimes without timezone info, so ORM
    objects may return naive datetimes.  PostgreSQL returns timezone-aware
    datetimes.  This helper normalises both so we can safely compare them
    with ``datetime.now(timezone.utc)`` without raising TypeError.

    Usage:
        from app.core.utils import ensure_utc

        if datetime.now(timezone.utc) > ensure_utc(record.deadline):
            raise SubmissionDeadlinePassedException(...)
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_expired(dt: datetime) -> bool:
    """Return True if the given datetime has already passed (relative to UTC now)."""
    return datetime.now(timezone.utc) > ensure_utc(dt)
