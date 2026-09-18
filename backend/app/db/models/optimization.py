from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.scenario import Scenario
    from app.db.models.schedule_entry import ScheduleEntry


class Optimization(Base):
    __tablename__ = "optimizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    total_grid_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_grid_cost_bdt: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="verified"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    scenario: Mapped[Scenario] = relationship("Scenario", back_populates="optimizations")
    schedule_entries: Mapped[list[ScheduleEntry]] = relationship(
        "ScheduleEntry", back_populates="optimization", cascade="all, delete-orphan"
    )
