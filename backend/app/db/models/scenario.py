from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.operator_note import OperatorNote
    from app.db.models.optimization import Optimization


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Default Scenario")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    operator_notes: Mapped[list[OperatorNote]] = relationship(
        "OperatorNote", back_populates="scenario", cascade="all, delete-orphan"
    )
    optimizations: Mapped[list[Optimization]] = relationship(
        "Optimization", back_populates="scenario", cascade="all, delete-orphan"
    )
