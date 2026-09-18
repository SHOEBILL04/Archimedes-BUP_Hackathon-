# Mathematical Optimization & Deterministic Validation System — Final Report

**Role**: Optimization + Validation Engineer  
**Project**: Smart Campus Energy Optimization Platform (BUP CSE Fest 2026 — GridWise LLM Challenge)  
**Date**: September 18, 2026  
**Status**: Complete, Verified & Passing (72/72 Unit Tests)

---

## 1. Files Created

### Core Service Modules
- **`backend/app/services/optimizer/guardrails.py`**: Deterministic trust boundary validating raw LLM directive interpretations against strict physical/schema boundaries and compiling conflict-resolved 24-hour constraints.
- **`backend/app/services/optimizer/lp_optimizer.py`**: PuLP/CBC linear programming dispatch solver minimizing total grid electricity cost over 24 hours under energy balance, storage dynamics, and operational limits.
- **`backend/app/services/optimizer/optimizer_service.py`**: Public application-layer entrypoint (`run_optimization`) providing input sanitization, zero-demand short-circuiting, and clean exception translation.
- **`backend/app/services/optimizer/__init__.py`**: Controlled package exports exposing only public data structures, exceptions, and `run_optimization`.
- **`backend/app/services/optimizer/INTERFACE.md`**: Integration and contract documentation for the backend orchestration engineer (`optimization_service.py`).
- **`backend/app/services/validation/replay_validator.py`**: Independent deterministic auditor simulating candidate schedules hour-by-hour across 13 physical and directive checks.
- **`backend/app/services/validation/__init__.py`**: Clean exports for `replay_validate`, `validate_and_raise`, and validation data structures.

### Test Suites
- **`backend/tests/services/test_guardrails.py`**: 29 unit tests verifying directive schema validation, boundary enforcement, safe `no_op` fallbacks, and mathematical conflict resolution.
- **`backend/tests/services/test_optimizer.py`**: 25 unit tests evaluating 24-hour LP formulation, tariff-arbitrage battery dispatch, directive enforcement, infeasibility raising, and input guards.
- **`backend/tests/services/test_validator.py`**: 18 unit tests evaluating the independent replay engine against valid schedules and specific injected physical/directive violations.

---

## 2. Public Interface

The backend orchestration layer (`app/services/optimization_service.py`) must import strictly from `app.services.optimizer` and `app.services.validation`:

```python
from app.services.optimizer import (
    BatteryInput,
    HourResult,
    InfeasibleError,
    OptimizationError,
    OptimizationResult,
    SolverError,
    run_optimization,
)
from app.services.validation import (
    ReplayValidationError,
    ReplayValidationInput,
    ValidationResult,
    replay_validate,
    validate_and_raise,
)
```

### Signature:
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
```

---

## 3. Numerical Tolerance

- **Validation Tolerance**: `TOLERANCE = 1e-4` ($0.0001$).
  - **Rationale**: The official BUP challenge evaluation rubric specifies an absolute tolerance of $0.01$ kWh or $0.01$ BDT. Our internal replay tolerance is set to $10^{-4}$—two orders of magnitude stricter than the judge—to ensure zero false-positive verifications while accommodating CBC interior-point/simplex floating-point precision.
- **Solver Value Threshold**: `EPS = 1e-7` ($0.0000001$).
  - **Rationale**: Clamps microscopic solver numerical artifacts (e.g. $-10^{-11}$) to $0.0$ to guarantee strict non-negativity across all physical energy variables.

---

## 4. Solver Behavior

- **Engine**: PuLP abstraction running COIN-OR CBC (`PULP_CBC_CMD`).
- **Configuration**:
  - `msg=False`: Console stdout suppressed to keep server logs clean.
  - `timeLimit=solver_timeout_seconds` (default: 5.0s): Hard solver execution budget to fit well within the 29s application request limit.
  - `threads=1`: Deterministic single-threaded execution.
- **Infeasibility & Error Handling**:
  - If CBC terminates with `Infeasible` or `Unbounded`, the solver raises `InfeasibleError`.
  - If a structural conflict is detected prior to solve (e.g., required reserve exceeding battery capacity), `InfeasibleError` is raised immediately.
  - Solver crashes, binary execution failures, or timeouts raise `SolverError`.
  - **Zero Fake Schedules**: The engine never generates mock or synthetic dispatch values upon failure.

---

## 5. Directive Conflict Resolution Rules

When multiple directives overlap in the same hourly intervals, they are deterministically merged by `compile_directives()`:

1. **`solar_reduction`**: Multiplies remaining usable factors ($\prod \text{factor}_i$).
   - *Example*: Two cleaning directives with factors $0.5$ and $0.6$ on hour 12 yield $\text{effective\_solar} = \text{base\_solar} \times 0.3$.
2. **`minimum_battery_reserve`**: Maximum required reserve wins ($\max \text{reserve}_i$).
   - *Example*: One note requests $30$ kWh and another requests $70$ kWh; the solver enforces $\ge 70$ kWh.
3. **`no_charge_window`**: Union of hours ($\bigcup \text{hours}_i$).
   - Charging is disabled (`charge == 0`) if any active directive prohibits it.
4. **`no_discharge_window`**: Union of hours ($\bigcup \text{hours}_i$).
   - Discharging is disabled (`discharge == 0`) if any active directive prohibits it.
5. **`max_grid_window`**: Minimum grid ceiling wins ($\min \text{limit}_i$).
   - *Example*: Limits of $100$ kWh and $40$ kWh result in a ceiling of $40$ kWh.

---

## 6. Test Results

Executed with `pytest` on Python 3.13:

| Test File | Tests Run | Passed | Failed | Execution Time |
| :--- | :---: | :---: | :---: | :---: |
| `backend/tests/services/test_guardrails.py` | 29 | 29 | 0 | 0.40s |
| `backend/tests/services/test_optimizer.py` | 25 | 25 | 0 | 1.06s |
| `backend/tests/services/test_validator.py` | 18 | 18 | 0 | 0.42s |
| **Total Test Suite** | **72** | **72** | **0** | **1.12s** |

All lint and import-formatting checks passed cleanly via `ruff check` with **0 errors**.

---

## 7. Edge Cases Covered

1. **All Demand Zero**: Direct short-circuit returns optimal zero-cost schedule without invoking solver.
2. **All Solar Zero**: LP successfully optimizes using grid and storage alone.
3. **Blackout / Zero Factor**: `factor=0.0` accepted and correctly forces solar consumption to zero.
4. **Zero Reserve / Zero Grid Ceiling**: Handled gracefully as valid physical boundary limits.
5. **Simultaneous Conflicting Windows**: Overlapping `no_charge` and `no_discharge` correctly forces storage idle.
6. **Impossible Reserve (> Capacity)**: Caught and rejected with `InfeasibleError`.
7. **Impossible Max Grid ($0$ grid with high demand & no solar)**: Correctly identifies infeasibility and raises `InfeasibleError`.
8. **Malformed Inputs**: Caught with descriptive `ValueError` (array length $\ne 24$, negative numbers, `NaN`, $\pm\infty$).
9. **Out-of-Order / Duplicate Notes**: Automatically sorted by `note_index`; duplicates safely downgraded to `no_op`.

---

## 8. Integration Guide for Backend Developer

To wire this into `backend/app/services/optimization_service.py`:

```python
from app.services.optimizer import BatteryInput, run_optimization, InfeasibleError, SolverError
from app.services.validation import ReplayValidationInput, validate_and_raise
from app.schemas.optimization import HourSchedule, VerificationResult

# 1. Instantiate BatteryInput from scenario
battery_in = BatteryInput(
    capacity_kwh=scenario.battery.capacity_kwh,
    initial_energy_kwh=scenario.battery.initial_energy_kwh,
    minimum_energy_kwh=scenario.battery.minimum_energy_kwh,
    max_charge_kwh_per_hour=scenario.battery.max_charge_kwh_per_hour,
    max_discharge_kwh_per_hour=scenario.battery.max_discharge_kwh_per_hour,
)

# 2. Run Optimization (guardrails + solver)
try:
    opt_result = run_optimization(
        demand=scenario.demand_kwh,
        base_solar=scenario.base_solar_kwh,
        tariff=scenario.tariff_bdt_per_kwh,
        battery=battery_in,
        raw_interpretations=[d.model_dump() for d in directives],
        note_count=len(scenario.operator_notes),
        solver_timeout_seconds=5.0,
    )
except InfeasibleError as exc:
    raise HTTPException(status_code=422, detail=str(exc))
except SolverError as exc:
    raise HTTPException(status_code=504, detail="Solver timeout or failure")
except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc))

# 3. Replay Verification
val_input = ReplayValidationInput(
    demand=scenario.demand_kwh,
    base_solar=scenario.base_solar_kwh,
    tariff=scenario.tariff_bdt_per_kwh,
    battery_capacity=battery_in.capacity_kwh,
    battery_initial_energy=battery_in.initial_energy_kwh,
    battery_min_energy=battery_in.minimum_energy_kwh,
    battery_max_charge_per_hour=battery_in.max_charge_kwh_per_hour,
    battery_max_discharge_per_hour=battery_in.max_discharge_kwh_per_hour,
    compiled_directives=..., # or use validate_and_raise()
    schedule=opt_result.hourly_schedule,
    reported_total_cost=opt_result.total_grid_cost_bdt,
)
val_result = validate_and_raise(val_input)
```

---

## 9. Known Assumptions & Limitations

1. **Battery Efficiency**: Formulated with lossless round-trip efficiency ($\eta_{\text{charge}} = 1.0, \eta_{\text{discharge}} = 1.0$) in strict conformance with the challenge specification and reference prototype.
2. **Horizon**: Fixed at 24 discrete hourly periods ($h=0..23$).
3. **No Grid Export**: Curtailment of excess solar is modeled; grid export/feed-in tariffs are not supported per problem statement.
4. **Single-Process Solver**: CBC solver runs in a dedicated thread-safe single process per optimization call.
