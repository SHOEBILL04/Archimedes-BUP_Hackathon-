# Optimization Workstream Integration Guide

This guide documents the integrated internal optimization pipeline facade for the orchestration layer developer.

---

## 1. Architectural Pipeline

The optimization engine executes the full end-to-end deterministic pipeline:

```
Validated Directives (NormalizedDirective)
                 ↓
Deterministic Directive Preprocessing (DeterministicDirectiveCompiler)
  - Calculates effective solar (multiplicative factors)
  - Enforces minimum reserve (highest reserve ceiling)
  - Assembles no-charge & no-discharge window masks
  - Sets max grid import ceilings
                 ↓
OptimizationInput Domain Model
                 ↓
PuLP + CBC LP Optimizer (PuLpEnergyOptimizer)
  - Minimizes sum(grid[h] * tariff[h])
  - Solves continuous hourly energy balance & storage state equations
                 ↓
Candidate Dispatch Schedule (HourlyScheduleOutput)
                 ↓
Independent Deterministic Replay Validator (DeterministicReplayValidator)
  - 11 physical, contractual, and battery state-space equations audited
  - Pure first-principles simulation (tolerance = 1e-4)
                 ↓
OptimizationPipelineResult
  - Verified schedule, total grid cost, objective value
  - On failure: structured error reporting with schedule = [] (NEVER fakes values)
```

---

## 2. Interface Contract

### Import

```python
from app.services.optimizer import (
    OptimizationEngine,
    OptimizationPipelineInput,
    OptimizationPipelineResult,
    optimize_and_validate,
)
```

### Input Payload (`OptimizationPipelineInput`)

| Field | Type | Description |
|---|---|---|
| `demand_kwh` | `list[float]` | 24 non-negative finite hourly campus demand values |
| `base_solar_kwh` | `list[float]` | 24 non-negative finite hourly base solar forecast values |
| `tariff_bdt_per_kwh` | `list[float]` | 24 non-negative finite hourly electricity tariff values |
| `battery` | `BatteryConfig` | Battery technical specs (`capacity_kwh`, `initial_energy_kwh`, `max_charge_kwh_per_hour`, etc.) |
| `directives` | `list[NormalizedDirective]` | Validated, normalized directives from guardrail stage |
| `solver_timeout_seconds` | `float` (default `10.0`) | CBC solver time limit |
| `tolerance` | `float` (default `1e-4`) | Numerical floating-point tolerance |
| `enforce_eod_neutrality` | `bool` (default `True`) | Enforce end-of-day battery neutrality |
| `strict` | `bool` (default `False`) | If `True`, raises exception on failure instead of returning structured result |

### Output Contract (`OptimizationPipelineResult`)

| Attribute | Type | Description |
|---|---|---|
| `success` | `bool` | `True` only if solver found optimal solution **and** replay validation passed |
| `status` | `SolverStatus` | `OPTIMAL`, `INFEASIBLE`, `TIMEOUT`, `ERROR` |
| `schedule` | `list[HourlyScheduleOutput]` | 24 hourly rows if successful; **empty `[]` on failure** (never manufactured) |
| `total_grid_kwh` | `float` | Sum of grid energy imported across the day |
| `total_grid_cost_bdt` | `float` | Sum of hourly grid electricity costs (`grid * tariff`) |
| `objective_value` | `float` | Exact LP solver objective value |
| `validation_result` | `ReplayValidationResult` | Detailed audit record with max constraint error and error strings |
| `compiled_directives` | `CompiledDirectives` | Preprocessed hourly constraint vectors |
| `errors` | `list[str]` | Human-readable explanation if solving or validation failed |
| `to_dict()` | `dict` | JSON-serializable dictionary representation |

---

## 3. Orchestration Layer Usage Example

In `backend/app/services/optimization_service.py`, the orchestration developer can replace the legacy call with:

```python
from app.services.optimizer import (
    BatteryConfig,
    OptimizationEngine,
    OptimizationPipelineInput,
)

# 1. Map scenario parameters
battery = BatteryConfig(
    capacity_kwh=scenario.battery.capacity_kwh,
    initial_energy_kwh=scenario.battery.initial_energy_kwh,
    minimum_energy_kwh=scenario.battery.minimum_energy_kwh,
    max_charge_kwh_per_hour=scenario.battery.max_charge_kwh_per_hour,
    max_discharge_kwh_per_hour=scenario.battery.max_discharge_kwh_per_hour,
)

# 2. Package pipeline input
pipeline_input = OptimizationPipelineInput.from_arrays(
    demand_kwh=scenario.demand_kwh,
    base_solar_kwh=scenario.base_solar_kwh,
    tariff_bdt_per_kwh=scenario.tariff_bdt_per_kwh,
    battery=battery,
    directives=validated_normalized_directives,  # list[NormalizedDirective]
)

# 3. Execute integrated optimization and independent replay audit
engine = OptimizationEngine()
result = engine.optimize_and_validate(pipeline_input)

# 4. Handle result
if not result.is_success:
    # Handle failure gracefully:
    # result.schedule is guaranteed empty []
    # result.errors contains actionable error messages
    logger.error("Optimization pipeline failed: %s", result.errors)
else:
    # Validated schedule is ready:
    schedule = result.schedule
    total_cost = result.total_grid_cost_bdt
```

Alternatively, raw arrays can be passed directly:

```python
result = engine.optimize_arrays(
    demand=scenario.demand_kwh,
    base_solar=scenario.base_solar_kwh,
    tariff=scenario.tariff_bdt_per_kwh,
    battery=battery,
    directives=validated_directives,
)
```
