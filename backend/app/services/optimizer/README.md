# Optimization Service (`app/services/optimizer`)

The `optimizer` package provides the mathematical formulation, linear program construction, and solver execution engine for the Smart Campus Energy Dispatch platform using **PuLP** and the **CBC** (Coin-or branch and cut) open-source solver.

---

## 1. Mathematical Formulation

The optimization is modeled as a 24-hour deterministic continuous Linear Program (LP) that minimizes total grid electricity cost over the planning horizon $T = 24$ (indices $t \in [0, 23]$).

### Decision Variables

For each hour $t \in \{0, \dots, 23\}$:

| Variable | Description | Domain |
|---|---|---|
| $g_t$ | Power imported from the municipal electrical grid (kWh) | $g_t \ge 0$, optionally $g_t \le \text{max\_grid}_t$ |
| $s_t$ | Solar generation utilized by the campus (kWh) | $0 \le s_t \le \text{effective\_solar}_t$ |
| $c_t$ | Energy routed into the battery storage system (kWh) | $0 \le c_t \le \text{charge\_limit}_t$ |
| $d_t$ | Energy discharged from the battery system (kWh) | $0 \le d_t \le \text{discharge\_limit}_t$ |
| $e_t$ | Battery stored energy at the end of hour $t$ (kWh) | $\text{min\_reserve}_t \le e_t \le \text{capacity}$ |

### Objective Function

$$\min \sum_{t=0}^{23} \left( g_t \times \text{tariff}_t \right)$$

where $\text{tariff}_t$ is the hourly grid tariff in BDT/kWh.

### Constraints

1. **Hourly Campus Energy Conservation**:
   $$g_t + s_t + d_t = \text{demand}_t + c_t \quad \forall t \in \{0, \dots, 23\}$$
   Campus demand and battery charging must be exactly met by the combination of grid imports, solar generation, and battery discharge.

2. **Solar Generation Availability**:
   $$s_t \le \text{base\_solar}_t \times \text{solar\_factor}_t \quad \forall t \in \{0, \dots, 23\}$$

3. **Battery State-of-Charge Dynamics**:
   - For hour $t = 0$:
     $$e_0 = e_{\text{initial}} + c_0 - d_0$$
   - For hours $t \in \{1, \dots, 23\}$:
     $$e_t = e_{t-1} + c_t - d_t$$

4. **Charge and Discharge Rate Limits & Operator Window Overrides**:
   $$c_t \le \begin{cases} 0 & \text{if } \text{no\_charge}_t = \text{True} \\ \text{max\_charge\_rate} & \text{otherwise} \end{cases}$$
   $$d_t \le \begin{cases} 0 & \text{if } \text{no\_discharge}_t = \text{True} \\ \text{max\_discharge\_rate} & \text{otherwise} \end{cases}$$

5. **Grid Power Ceilings**:
   $$g_t \le \text{max\_grid}_t \quad \text{if } \text{max\_grid}_t \text{ is defined}$$

6. **24-Hour End-of-Day Neutrality**:
   $$e_{23} = e_{\text{initial}}$$
   Ensures the battery returns to its starting energy level, preventing artificial depletion for cost arbitrage and ensuring sustainable multi-day cyclic operation.

---

## 2. Solver Configuration

- **Engine**: PuLP with `PULP_CBC_CMD` (COIN-OR CBC).
- **Execution**: Synchronous C executable. When invoked inside FastAPI async endpoints, wrap calls in `asyncio.to_thread()` to prevent blocking the event loop.
- **Timeout**: Enforced via `timeLimit` parameter (defaults to `Settings.solver_timeout_seconds = 5`).
- **Threading**: Single-threaded deterministic execution (`threads=1`).

---

## 3. Public Interface

```python
from app.services.optimizer.solver import EnergyOptimizer
from app.services.validation.compiler import compile_directives

optimizer = EnergyOptimizer(timeout_seconds=5.0)
schedules, total_grid_cost, total_grid_kwh = optimizer.solve(
    scenario=scenario,
    directives=compiled_directives,
)
```

### Exceptions Raised

* `OptimizationInfeasibleError`: Raised when the linear program is mathematically infeasible (e.g. impossible grid ceiling with zero battery and solar).
* `OptimizationTimeoutError`: Raised when solver time budget is exceeded.
* `SolverExecutionError`: Raised if the CBC binary fails to execute or crashes.
