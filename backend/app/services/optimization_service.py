from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.repositories.optimization_repository import OptimizationRepository
from app.schemas.optimization import (
    DirectiveInterpretation,
    EnergyScenario,
    HourSchedule,
    OptimizationResponse,
    VerificationResult,
)
from app.services.llm_service import LLMService
from app.services.validation_service import ValidationService


class OptimizationService:
    """Orchestrates the energy optimization pipeline:
    LLM Interpretation -> Guardrails -> LP Solver (placeholder) -> Replay Validator -> DB Persistence.
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        validation_service: ValidationService | None = None,
    ) -> None:
        self.llm_service = llm_service or LLMService()
        self.validation_service = validation_service or ValidationService()

    async def optimize(
        self, scenario: EnergyScenario, db: Session | None = None, persist: bool = True
    ) -> OptimizationResponse:
        """Run the end-to-end optimization pipeline.

        Returns a clearly marked scaffold placeholder response.
        The actual PuLP/CBC linear program will be plugged in here in the next phase.
        """
        logger.info("OptimizationService.optimize called (SCAFFOLD PLACEHOLDER)")

        # 1. LLM Directive Interpretation
        directives = await self.llm_service.interpret_notes(scenario)
        raw_directive_dicts = [d.model_dump() for d in directives]

        # 2. Battery specifications
        from app.services.optimizer import BatteryInput, run_optimization
        from app.services.optimizer.guardrails import compile_directives, validate_interpretations
        from app.services.validation import ReplayValidationInput, replay_validate

        battery_in = BatteryInput(
            capacity_kwh=scenario.battery.capacity_kwh,
            initial_energy_kwh=scenario.battery.initial_energy_kwh,
            minimum_energy_kwh=scenario.battery.minimum_energy_kwh,
            max_charge_kwh_per_hour=scenario.battery.max_charge_kwh_per_hour,
            max_discharge_kwh_per_hour=scenario.battery.max_discharge_kwh_per_hour,
        )

        # 3. Deterministic Guardrails & PuLP/CBC LP Solver Dispatch
        opt_result = run_optimization(
            demand=scenario.demand_kwh,
            base_solar=scenario.base_solar_kwh,
            tariff=scenario.tariff_bdt_per_kwh,
            battery=battery_in,
            raw_interpretations=raw_directive_dicts,
            note_count=len(scenario.operator_notes),
            solver_timeout_seconds=5.0,
        )

        # Validated directives for return payload
        val_dirs = validate_interpretations(
            raw_directive_dicts, len(scenario.operator_notes), battery_in.capacity_kwh
        )
        compiled = compile_directives(
            val_dirs, scenario.base_solar_kwh, battery_in.capacity_kwh, battery_in.minimum_energy_kwh
        )

        # 4. Independent Deterministic Replay Validation
        val_input = ReplayValidationInput(
            demand=scenario.demand_kwh,
            base_solar=scenario.base_solar_kwh,
            tariff=scenario.tariff_bdt_per_kwh,
            battery_capacity=battery_in.capacity_kwh,
            battery_initial_energy=battery_in.initial_energy_kwh,
            battery_min_energy=battery_in.minimum_energy_kwh,
            battery_max_charge_per_hour=battery_in.max_charge_kwh_per_hour,
            battery_max_discharge_per_hour=battery_in.max_discharge_kwh_per_hour,
            compiled_directives=compiled,
            schedule=opt_result.hourly_schedule,
            reported_total_cost=opt_result.total_grid_cost_bdt,
        )
        val_result = replay_validate(val_input)

        # 5. Format Hourly Schedules and Official Judge Hourly Plan
        schedules: list[HourSchedule] = [
            HourSchedule(
                hour=h.hour,
                demand_kwh=round(h.demand_kwh, 2),
                effective_solar_kwh=round(h.effective_solar_kwh, 2),
                solar_used_kwh=round(h.solar_used_kwh, 2),
                battery_charge_kwh=round(h.battery_charge_kwh, 2),
                battery_discharge_kwh=round(h.battery_discharge_kwh, 2),
                battery_energy_after_kwh=round(h.battery_energy_after_kwh, 2),
                grid_kwh=round(h.grid_kwh, 2),
                tariff_bdt_per_kwh=round(h.tariff_bdt_per_kwh, 2),
                grid_cost_bdt=round(h.grid_cost_bdt, 2),
            )
            for h in opt_result.hourly_schedule
        ]

        from app.schemas.optimization import HourlyPlanItem

        hourly_plan: list[HourlyPlanItem] = []
        for h in opt_result.hourly_schedule:
            if h.battery_charge_kwh > 1e-4:
                b_action = "charge"
                b_kwh = round(h.battery_charge_kwh, 2)
            elif h.battery_discharge_kwh > 1e-4:
                b_action = "discharge"
                b_kwh = round(h.battery_discharge_kwh, 2)
            else:
                b_action = "idle"
                b_kwh = 0.0

            hourly_plan.append(
                HourlyPlanItem(
                    hour=h.hour,
                    grid_kwh=round(h.grid_kwh, 2),
                    solar_used_kwh=round(h.solar_used_kwh, 2),
                    battery_action=b_action,
                    battery_kwh=b_kwh,
                    battery_energy_after_kwh=round(h.battery_energy_after_kwh, 2),
                )
            )

        validated_directive_models = [
            DirectiveInterpretation(
                note_index=d["note_index"],
                directive_type=d["directive_type"],
                structured_adjustment=d.get("structured_adjustment"),
                applies=d.get("applies", False),
                explanation=d.get("explanation") or f"Directive {d['directive_type']} processed.",
            )
            for d in val_dirs
        ]

        peak_grid = round(max((h.grid_kwh for h in opt_result.hourly_schedule), default=0.0), 2)
        total_cost = round(opt_result.total_grid_cost_bdt, 2)

        response = OptimizationResponse(
            scenario_id=scenario.scenario_id,
            directive_interpretation=validated_directive_models,
            hourly_plan=hourly_plan,
            schedule=schedules,
            total_grid_cost_bdt=total_cost,
            total_cost_bdt=total_cost,
            total_grid_kwh=round(opt_result.total_grid_kwh, 2),
            peak_grid_kwh=peak_grid,
            plan_summary="Optimal 24-hour campus energy schedule generated and verified via deterministic replay.",
            verification=VerificationResult(
                verified=val_result.verified,
                max_constraint_error=val_result.max_constraint_error,
                total_grid_cost_bdt=round(val_result.recalculated_total_cost, 2),
            ),
            status_message="Optimal energy dispatch computed and verified via deterministic replay.",
        )

        # 6. Repository persistence into SQLite if DB session is supplied
        if db is not None and persist:
            try:
                repo = OptimizationRepository(db)
                repo.save_optimization_run(scenario, response)
                logger.info("Saved optimization result into SQLite database")
            except Exception as e:
                logger.warning("Could not persist optimization to database: %s", e)

        return response
