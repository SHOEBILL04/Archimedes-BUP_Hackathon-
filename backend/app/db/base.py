from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """SQLAlchemy 2.x Declarative Base with common attributes."""
