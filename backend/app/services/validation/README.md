# Validation Service (`app/services/validation`)

The `validation` package provides two critical deterministic reliability layers for the Smart Campus Energy Optimization pipeline:
1. **Deterministic Guardrails (`guardrails.py` & `compiler.py`)**: An untrusted trust boundary isolating LLM interpretations from the solver.
2. **Replay Validation Simulator (`replay.py`)**: An independent physics verification engine simulating the resulting dispatch schedule against first-principles energy equations.

---

## 1. Deterministic Guardrails (`guardrails.py`)

LLMs are treated as inherently untrusted parsers. The guardrail layer validates all `DirectiveInterpretation` instances before any directive is allowed to impact the optimization model.

### Integrity Rules
- **Count & Ordering**: The number of directives must match the scenario's `operator_notes`. `note_index` values must form a contiguous sequence $0, 1, \dots, N-1$. If indices are corrupted or duplicated, the entire interpretation falls back to `no_op`.
- **Allowed Types**: Directive must belong to the supported whitelist:
  - `solar_reduction`: requires `hours` and `factor` $\in [0.0, 1.0]$.
  - `minimum_battery_reserve`: requires `hours` and $0.0 \le \text{minimum\_energy\_kwh} \le \text{battery.capacity\_kwh}$.
  - `no_charge_window`: requires `hours`.
  - `no_discharge_window`: requires `hours`.
  - `max_grid_window`: requires `hours` and $\text{max\_grid\_kwh} \ge 0$.
  - `no_op`: `structured_adjustment` is `None`, `applies` is `False`.
- **Hour Array Sanitization**: `hours` must be a non-empty list of unique integers strictly within $[0, 23]$, sorted ascending.
- **Strict Key Checking**: Any unexpected keys in `structured_adjustment` result in automatic degradation to `no_op`.
- **Graceful Degradation**: Individual malformed directives degrade to `no_op` without aborting the overall optimization request.

---

## 2. Directive Compiler (`compiler.py`)

Translates sanitized directives into strongly typed 24-element hourly vectors (`CompiledDirectives`):

### Overlap Resolution Rules
When multiple operator notes target the same hour:
- **Solar Reductions**: Multiplies remaining factors (e.g., 20% reduction $\times$ 50% reduction $\to 0.8 \times 0.5 = 0.4$).
- **Minimum Battery Reserve**: Selects the maximum reserve required ($\max(\text{reserve}_A, \text{reserve}_B)$).
- **No-Charge & No-Discharge Windows**: Computes the boolean union (OR).
- **Grid Power Ceilings**: Selects the most restrictive minimum ceiling ($\min(\text{ceiling}_A, \text{ceiling}_B)$).

---

## 3. Replay Verification Simulator (`replay.py`)

The replay validator runs completely independently of the PuLP solver, checking the physical consistency of the dispatch schedule against tolerance $\epsilon = 10^{-5}$:

1. **Non-Negativity**: $g_t, s_t, c_t, d_t, e_t \ge -\epsilon$.
2. **Hourly Power Conservation**: $|(g_t + s_t + d_t) - (\text{demand}_t + c_t)| \le \epsilon$.
3. **Solar Availability Bound**: $s_t \le \text{effective\_solar}_t + \epsilon$.
4. **Battery Energy Bounds**: $\text{min\_reserve}_t - \epsilon \le e_t \le \text{capacity} + \epsilon$.
5. **Battery State Dynamics**: $|e_t - (e_{t-1} + c_t - d_t)| \le \epsilon$.
6. **Rate Limit Bounds**: $c_t \le c_{\text{limit}, t} + \epsilon$ and $d_t \le d_{\text{limit}, t} + \epsilon$.
7. **Grid Import Ceilings**: $g_t \le g_{\text{max}, t} + \epsilon$.
8. **End-of-Day Neutrality**: $|e_{23} - e_{\text{initial}}| \le \epsilon$.
9. **Objective Value Reconciliation**: $|\sum (g_t \times \text{tariff}_t) - \text{reported\_cost}| \le \epsilon$.

### Exceptions Raised
* `ReplayValidationError`: Raised if any physical constraint violation exceeds tolerance $\epsilon = 10^{-5}$. Contains the exact hour and magnitude of violation.
