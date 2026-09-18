# Optimizer Module Interface & Integration Guide

This document defines the interface boundary for the mathematical dispatch optimization service of the Smart Campus Energy Optimization backend.

> **CRITICAL ARCHITECTURAL RULE**:  
> The API, database, repository, and orchestration layers **MUST NEVER import PuLP directly**.  
> All interaction with the linear programming engine occurs strictly through the typed interface exposed by `app.services.optimizer`.

---

## 1. Imports

Orchestration services (such as `optimization_service.py`) should import only from:

```python
from app.services.optimizer import (
    BatteryInput,
    OptimizationResult,
    HourResult,
    InfeasibleError,
    SolverError,
    OptimizationError,
    run_optimization,
)
```

---

## 2. Main Entrypoint: `run_optimization()`

```python
def run_optimization(
    demand: list[float],
    base_solar: list[float],
    tariff: list[float],
    battery: BatteryInput,
    raw_interpretations: list[dict[str, Any]],
    note_count: int,
    solver_timeout_seconds: float = 5.0,
) -> OptimizationResult:
    ...
```

### Parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `demand` | `list[float]` | Exactly 24 non-negative finite hourly campus demand values in kWh. |
| `base_solar` | `list[float]` | Exactly 24 non-negative finite hourly baseline solar values in kWh. |
| `tariff` | `list[float]` | Exactly 24 non-negative finite hourly grid electricity tariffs in BDT/kWh. |
| `battery` | `BatteryInput` | Typed battery parameters object (see below). |
| `raw_interpretations` | `list[dict]` | Raw structured directive dictionaries returned by the upstream LLM service. |
| `note_count` | `int` | Expected number of operator notes (1 to 3). |
| `solver_timeout_seconds`| `float` | Maximum solver execution timeout in seconds (default: `5.0`). |

---

## 3. Data Structures

### `BatteryInput`
```python
@dataclass
class BatteryInput:
    capacity_kwh: float
    initial_energy_kwh: float
    minimum_energy_kwh: float
    max_charge_kwh_per_hour: float
    max_discharge_kwh_per_hour: float
```

### `OptimizationResult`
```python
@dataclass
class OptimizationResult:
    hourly_schedule: list[HourResult]  # Exactly 24 hourly dispatch rows
    total_grid_kwh: float              # Sum of grid purchases across all 24 hours
    total_grid_cost_bdt: float         # Total grid cost in BDT across all 24 hours
    peak_grid_kwh: float               # Maximum hourly grid import across all 24 hours
    objective_value: float             # Solver objective value
    solver_status: str                 # Typically "Optimal"
```

### `HourResult`
Each entry in `hourly_schedule`:
```python
@dataclass
class HourResult:
    hour: int                          # 0..23
    demand_kwh: float                  # Hourly demand
    effective_solar_kwh: float         # Solar after operator reduction directives
    solar_used_kwh: float              # Solar consumed (curtailed solar is excluded)
    battery_charge_kwh: float          # Battery charging power
    battery_discharge_kwh: float       # Battery discharge power
    battery_energy_after_kwh: float    # Battery state of charge at end of hour
    grid_kwh: float                    # Grid energy imported
    tariff_bdt_per_kwh: float          # Grid price for this hour
    grid_cost_bdt: float               # Hourly grid cost (grid_kwh * tariff)
```

---

## 4. Format of `raw_interpretations`

The `run_optimization()` function accepts raw directive dicts directly from the LLM service. Guardrails will validate and sanitize them deterministically:

```python
raw_interpretations = [
    {
        "note_index": 0,
        "directive_type": "solar_reduction",
        "structured_adjustment": {"hours": [13, 14], "factor": 0.2},
        "applies": True,
        "explanation": "Panel washing window.",
    },
    {
        "note_index": 1,
        "directive_type": "no_charge_window",
        "structured_adjustment": {"hours": [18, 19]},
        "applies": True,
        "explanation": "Grid peak avoidance.",
    },
    {
        "note_index": 2,
        "directive_type": "no_op",
        "structured_adjustment": None,
        "applies": False,
        "explanation": "Cafeteria schedule notice.",
    },
]
```

---

## 5. Exceptions & Error Handling

| Exception | Base Class | When Raised | Recommended HTTP Status |
| :--- | :--- | :--- | :--- |
| `ValueError` | `Exception` | Invalid array lengths ($\ne 24$), non-finite values, negative inputs, or incompatible battery bounds. | `400 Bad Request` or `422 Unprocessable Entity` |
| `InfeasibleError` | `OptimizationError` | Mathematical constraints cannot be satisfied (e.g. impossible demand under grid caps, impossible reserve). | `422 Unprocessable Entity` |
| `SolverError` | `OptimizationError` | CBC solver crashed, missing binary, or solver timeout exceeded. | `504 Gateway Timeout` or `500 Internal Server Error` |
| `OptimizationError`| `Exception` | General optimization failure. | `500 Internal Server Error` |

---

## 6. Integration Example for `optimization_service.py`

```python
from app.core.exceptions import ServiceException
from app.schemas.optimization import EnergyScenario, OptimizationResponse, HourSchedule, VerificationResult
from app.services.optimizer import (
    BatteryInput,
    InfeasibleError,
    SolverError,
    run_optimization,
)

async def run_energy_dispatch(scenario: EnergyScenario, raw_llm_directives: list[dict]) -> OptimizationResponse:
    battery_input = BatteryInput(
        capacity_kwh=scenario.battery.capacity_kwh,
        initial_energy_kwh=scenario.battery.initial_energy_kwh,
        minimum_energy_kwh=scenario.battery.minimum_energy_kwh,
        max_charge_kwh_per_hour=scenario.battery.max_charge_kwh_per_hour,
        max_discharge_kwh_per_hour=scenario.battery.max_discharge_kwh_per_hour,
    )

    try:
        opt_result = run_optimization(
            demand=scenario.demand_kwh,
            base_solar=scenario.base_solar_kwh,
            tariff=scenario.tariff_bdt_per_kwh,
            battery=battery_input,
            raw_interpretations=raw_llm_directives,
            note_count=len(scenario.operator_notes),
            solver_timeout_seconds=5.0,
        )
    except InfeasibleError as exc:
        raise ServiceException(status_code=422, detail=f"Scenario is mathematically infeasible: {exc}")
    except SolverError as exc:
        raise ServiceException(status_code=504, detail=f"Solver execution timed out or failed: {exc}")
    except ValueError as exc:
        raise ServiceException(status_code=400, detail=str(exc))

    # Convert opt_result.hourly_schedule to your API schema list of HourSchedule
    schedule_entries = [
        HourSchedule(
            hour=h.hour,
            demand_kwh=h.demand_kwh,
            effective_solar_kwh=h.effective_solar_kwh,
            solar_used_kwh=h.solar_used_kwh,
            battery_charge_kwh=h.battery_charge_kwh,
            battery_discharge_kwh=h.battery_discharge_kwh,
            battery_energy_after_kwh=h.battery_energy_after_kwh,
            grid_kwh=h.grid_kwh,
            tariff_bdt_per_kwh=h.tariff_bdt_per_kwh,
            grid_cost_bdt=h.grid_cost_bdt,
        )
        for h in opt_result.hourly_schedule
    ]

    return schedule_entries
```
