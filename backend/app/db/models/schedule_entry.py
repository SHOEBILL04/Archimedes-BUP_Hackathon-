from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.optimization import Optimization


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    optimization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("optimizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hour: Mapped[int] = mapped_column(Integer, nullable=False)
    demand_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    effective_solar_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    solar_used_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    battery_charge_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    battery_discharge_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    battery_energy_after_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    grid_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    tariff_bdt_per_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    grid_cost_bdt: Mapped[float] = mapped_column(Float, nullable=False)

    optimization: Mapped[Optimization] = relationship(
        "Optimization", back_populates="schedule_entries"
    )
