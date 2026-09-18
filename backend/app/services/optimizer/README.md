# Optimization Workstream — Integration Guide

Guardrails, the LP optimizer, and the replay validator. Pure computation: no
HTTP, no SQL, no OpenAI. The orchestration layer calls three functions in order
and never needs to import `pulp`.

```
EnergyScenario + DirectiveInterpretation[]
            │
            ▼  normalize_directives()
      GuardrailReport → NormalizedDirectives
            │
            ▼  solve_dispatch()
      OptimizationOutcome
            │
            ▼  replay_validate()
      ReplayValidationResult
```

---

## 1. Guardrails

```python
from app.services.validation import normalize_directives
```

| | |
|---|---|
| **Input** | `scenario: EnergyScenario`, `directives: list[DirectiveInterpretation]` |
| **Output** | `GuardrailReport` |
| **Raises** | nothing |

`GuardrailReport` fields:

| Field | Type | Meaning |
|---|---|---|
| `normalized` | `NormalizedDirectives` | per-hour constraint arrays, feeds the optimizer |
| `accepted` | `tuple[int, ...]` | `note_index` of directives that passed |
| `rejections` | `tuple[DirectiveRejection, ...]` | `note_index`, `directive_type`, `reason` |

**Failure behavior:** a directive violating any rule is *rejected and recorded*,
never coerced and never reinterpreted as another type. One malformed directive
cannot fail the request; it also cannot leak an unchecked constraint into the LP.
Surface `rejections` to the operator — a silently dropped instruction is worse
than a rejected one.

`NormalizedDirectives` — five arrays, each exactly 24 entries, indexed by hour:

| Field | Type | Neutral value |
|---|---|---|
| `solar_factors` | `tuple[float, ...]` | `1.0` |
| `minimum_reserve` | `tuple[float, ...]` | `0.0` |
| `no_charge` | `tuple[bool, ...]` | `False` |
| `no_discharge` | `tuple[bool, ...]` | `False` |
| `max_grid` | `tuple[float \| None, ...]` | `None` |

Use `NormalizedDirectives.identity()` to optimize with no directives at all.

### Expected `structured_adjustment` payloads

```text
solar_reduction          {"hours": [int, ...], "factor": float}   factor = fraction REMAINING
minimum_battery_reserve  {"hours": [int, ...], "minimum_energy_kwh": float}
no_charge_window         {"hours": [int, ...]}
no_discharge_window      {"hours": [int, ...]}
max_grid_window          {"hours": [int, ...], "max_grid_kwh": float}
no_op                    null
```

`hours` must be integers in `0..23`, unique and strictly ascending.
An "80% reduction" is `factor = 0.2`.

---

## 2. Optimizer

```python
from app.services.optimizer import solve_dispatch
```

| | |
|---|---|
| **Input** | `scenario: EnergyScenario`, `normalized: NormalizedDirectives` |
| **Keyword-only** | `settings`, `charge_efficiency=1.0`, `discharge_efficiency=1.0` |
| **Output** | `OptimizationOutcome` |
| **Raises** | `ValueError` only for an efficiency outside `(0, 1]` |

`OptimizationOutcome` fields:

| Field | Type |
|---|---|
| `status` | `SolverStatus` — `OPTIMAL`, `INFEASIBLE`, `UNBOUNDED`, `UNDEFINED`, `NOT_SOLVED`, `ERROR` |
| `succeeded` | `bool` — `OPTIMAL` **and** 24 rows |
| `schedule` | `tuple[HourSchedule, ...]` — reuses the existing API schema |
| `effective_solar_kwh` | `tuple[float, ...]` |
| `total_grid_kwh`, `total_grid_cost_bdt`, `objective_value` | `float` |
| `message` | `str` |

**Failure behavior:** solver failures are returned, never raised. A non-optimal
run always carries `schedule == ()` and zeroed totals, so an invalid schedule can
never be mistaken for success. **Always branch on `outcome.succeeded`.**
`SOLVER_TIMEOUT_SECONDS` from settings is passed to CBC as a time limit.

---

## 3. Replay validator

```python
from app.services.validation import replay_validate
```

| | |
|---|---|
| **Input** | `scenario`, `normalized`, `schedule: Sequence[HourSchedule]` |
| **Keyword-only** | `reported_total_cost_bdt`, `reported_total_grid_kwh`, `charge_efficiency`, `discharge_efficiency`, `tolerance` |
| **Output** | `ReplayValidationResult` |
| **Raises** | nothing |

| Field | Type | Meaning |
|---|---|---|
| `valid` | `bool` | true when `errors` is empty |
| `errors` | `tuple[ValidationIssue, ...]` | `rule`, `message`, `hour`, `actual`, `expected`, `unit` |
| `warnings` | `tuple[ValidationIssue, ...]` | non-fatal (e.g. simultaneous charge/discharge) |
| `max_constraint_error` | `float` | largest **physical** violation, kWh → `VerificationResult.max_constraint_error` |
| `max_cost_error_bdt` | `float` | largest **monetary** discrepancy, BDT |
| `total_grid_kwh`, `total_grid_cost_bdt` | `float` | independently recomputed — prefer these |

**Tolerance:** `TOLERANCE = 1e-6`. Absolute for energy (1 mWh, far below anything
physical, well above CBC noise around 1e-10..1e-12). Monetary checks use
`tolerance * (1 + |expected|)`, because a cost is energy × tariff and its
floating-point error scales with magnitude — an absolute BDT bound would make the
check tariff-sensitive.

**Failure behavior:** never raises and never short-circuits; every failing hour is
reported so one corruption does not mask another. Pass the reported totals to have
them cross-checked. Treat `valid is False` as a bug in the optimizer, not as a bad
request.

### Independence

The validator never calls the solver and never re-solves the LP. It recomputes
from the **original request**:

| Quantity | Source |
|---|---|
| effective solar | `base_solar × normalized.solar_factors` — *not* the reported value |
| energy balance | original `demand` — *not* `row.demand_kwh` |
| battery trajectory | replayed from `initial_energy_kwh` — *not* `battery_energy_after_kwh` |
| cost | original `tariff × grid` — *not* the reported cost |

`demand_integrity` and `tariff_integrity` additionally assert the schedule restates
its inputs faithfully, so the optimizer cannot redefine the problem it was given.

---

## 4. Worked example

Runnable as written; mirrors `tests/services/test_end_to_end.py::run_pipeline`.

```python
from app.services.optimizer import solve_dispatch
from app.services.validation import normalize_directives, replay_validate

def run(scenario, directives):
    # 1. Guardrails — untrusted LLM output becomes safe per-hour constraints.
    report = normalize_directives(scenario, directives)
    if report.rejections:
        logger.warning("Dropped %d directive(s)", len(report.rejections))

    # 2. Optimizer — cheapest feasible 24-hour dispatch.
    outcome = solve_dispatch(scenario, report.normalized)
    if not outcome.succeeded:
        raise OptimizationException(outcome.message)  # app.core.exceptions

    # 3. Validator — independent physical and financial re-derivation.
    validation = replay_validate(
        scenario,
        report.normalized,
        outcome.schedule,
        reported_total_cost_bdt=outcome.total_grid_cost_bdt,
        reported_total_grid_kwh=outcome.total_grid_kwh,
    )
    return report, outcome, validation
```

Mapping onto the API response (`app.schemas.optimization`):

```python
OptimizationResponse(
    directive_interpretation=directives,          # from the LLM layer
    schedule=list(outcome.schedule),              # already HourSchedule
    total_grid_cost_bdt=validation.total_grid_cost_bdt,   # independently recomputed
    total_grid_kwh=validation.total_grid_kwh,
    verification=VerificationResult(
        verified=validation.valid,
        max_constraint_error=validation.max_constraint_error,
        total_grid_cost_bdt=validation.total_grid_cost_bdt,
    ),
    status_message=outcome.message,
)
```

---

## 5. Physical model

Per hour `h` in `0..23`, five continuous variables: `grid`, `solar_used`,
`battery_charge`, `battery_discharge`, `battery_energy_after` (all ≥ 0).

```text
objective   minimize Σ grid[h] × tariff[h]
balance     grid[h] + solar_used[h] + discharge[h] == demand[h] + charge[h]
battery     E[h] = E[h-1] + charge[h]×η_c − discharge[h]/η_d      (E[-1] = initial)
solar       0 ≤ solar_used[h] ≤ effective_solar[h]                 (surplus curtailed)
capacity    0 ≤ E[h] ≤ capacity_kwh
rates       charge[h] ≤ max_charge,  discharge[h] ≤ max_discharge
reserve     E[h] ≥ max(battery.minimum_energy_kwh, normalized.minimum_reserve[h])
grid cap    grid[h] ≤ normalized.max_grid[h]      (when not None)
neutrality  E[23] == initial_energy_kwh
```

The optimizer and the validator share these definitions through
`app.services.validation.physics` (`required_reserve_kwh`, efficiency constants)
so the two layers cannot drift apart.

**No export.** Energy leaves the battery only by serving demand, so
`discharge[h] − charge[h] ≤ demand[h] + solar_used[h]` in every hour. A late
full-capacity reserve can therefore be infeasible not because of the discharge
*rate*, but because too little demand remains to absorb the energy before
end-of-day neutrality applies.

**Simultaneous charge/discharge.** No binary variable; the model is a pure LP.
Adding δ to both charge and discharge leaves the balance and the state equation
unchanged, so it is cost-*neutral*, never cost-*improving* — there is no incentive
to use it. Below unit efficiency it would strictly destroy energy and be actively
penalized. Because it is neutral rather than forbidden, the validator reports it
as a **warning** rather than an error. Adopting a MILP was considered and
deliberately rejected.

**Efficiency = 1.0.** `BatteryParameters` exposes no efficiency fields and is
`extra="forbid"`, so a lossless round trip is the current documented semantics.
Both layers accept the terms as parameters — if you pass a non-default efficiency
to `solve_dispatch`, pass the *same* value to `replay_validate`, or the
independent replay will correctly report a `battery_state_replay` mismatch.
