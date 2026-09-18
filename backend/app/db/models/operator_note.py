from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.scenario import Scenario


class OperatorNote(Base):
    __tablename__ = "operator_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    note_index: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_note: Mapped[str] = mapped_column(Text, nullable=False)
    directive_type: Mapped[str] = mapped_column(String(64), nullable=False)
    structured_adjustment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    applies: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    scenario: Mapped[Scenario] = relationship("Scenario", back_populates="operator_notes")
