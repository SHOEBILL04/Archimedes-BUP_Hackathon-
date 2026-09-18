from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.operator_note import OperatorNote
from app.db.models.optimization import Optimization
from app.db.models.scenario import Scenario
from app.db.models.schedule_entry import ScheduleEntry
from app.schemas.optimization import EnergyScenario, OptimizationResponse


class OptimizationRepository:
    """Encapsulates all database operations for energy scenarios and optimization runs."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def save_optimization_run(
        self,
        scenario_data: EnergyScenario,
        result: OptimizationResponse,
        scenario_name: str = "Campus Baseline Scenario",
    ) -> Optimization:
        """Persists scenario, parsed directives, optimization header, and 24-hr schedule entries."""
        # 1. Create Scenario
        scenario = Scenario(name=scenario_name)
        self.db.add(scenario)
        self.db.flush()

        # 2. Save Operator Notes
        for interp in result.directive_interpretation:
            raw_text = (
                scenario_data.operator_notes[interp.note_index]
                if interp.note_index < len(scenario_data.operator_notes)
                else ""
            )
            note = OperatorNote(
                scenario_id=scenario.id,
                note_index=interp.note_index,
                raw_note=raw_text,
                directive_type=interp.directive_type,
                structured_adjustment=interp.structured_adjustment,
                applies=interp.applies,
            )
            self.db.add(note)

        # 3. Save Optimization Record
        optimization = Optimization(
            scenario_id=scenario.id,
            total_grid_kwh=result.total_grid_kwh,
            total_grid_cost_bdt=result.total_grid_cost_bdt,
            verification_status="verified" if result.verification.verified else "unverified",
        )
        self.db.add(optimization)
        self.db.flush()

        # 4. Save 24-hour Schedule Entries
        for entry in result.schedule:
            db_entry = ScheduleEntry(
                optimization_id=optimization.id,
                hour=entry.hour,
                demand_kwh=entry.demand_kwh,
                effective_solar_kwh=entry.effective_solar_kwh,
                solar_used_kwh=entry.solar_used_kwh,
                battery_charge_kwh=entry.battery_charge_kwh,
                battery_discharge_kwh=entry.battery_discharge_kwh,
                battery_energy_after_kwh=entry.battery_energy_after_kwh,
                grid_kwh=entry.grid_kwh,
                tariff_bdt_per_kwh=entry.tariff_bdt_per_kwh,
                grid_cost_bdt=entry.grid_cost_bdt,
            )
            self.db.add(db_entry)

        self.db.commit()
        self.db.refresh(optimization)
        return optimization

    def get_optimization_by_id(self, optimization_id: int) -> Optimization | None:
        """Retrieve an optimization by primary key."""
        return self.db.query(Optimization).filter(Optimization.id == optimization_id).first()
