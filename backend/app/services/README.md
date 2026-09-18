# Services Layer (`app/services`)

The services layer implements the domain logic and computational pipeline of the Smart Campus Energy Optimization platform.

---

## Service Architecture

```text
app/services/
├── optimization_service.py   # High-level pipeline coordinator & persistence orchestrator
├── validation_service.py     # Backward-compatible service facade for guardrails & replay
├── llm_service.py            # OpenAI LLM directive interpreter
│
├── optimizer/                # Linear Programming formulation and PuLP / CBC solver
│   ├── __init__.py
│   ├── solver.py             # EnergyOptimizer class & problem formulation
│   ├── exceptions.py         # OptimizationInfeasibleError, SolverExecutionError
│   └── README.md             # Mathematical specification of LP model
│
└── validation/               # Deterministic trust boundaries & physical replay simulator
    ├── __init__.py
    ├── models.py             # CompiledDirectives domain dataclass
    ├── guardrails.py         # LLM trust boundary sanitization
    ├── compiler.py           # Compiles directives into 24-hour constraint arrays
    ├── replay.py             # First-principles hourly physics replay engine
    ├── exceptions.py         # ReplayValidationError, GuardrailValidationError
    └── README.md             # Guardrail specification & physics verification rules
```

---

## Execution Pipeline Flow

1. **Directive Parsing** (`llm_service.py`): Translates 1 to 3 operator notes into structured candidate directives.
2. **Deterministic Guardrails** (`validation/guardrails.py`): Validates candidates against physical limits and sanitizes inputs.
3. **Directive Compilation** (`validation/compiler.py`): Resolves overlapping directives and computes 24-hour constraint arrays.
4. **Linear Programming Solver** (`optimizer/solver.py`): PuLP formulation executed via CBC to compute optimal cost dispatch.
5. **Replay Validation** (`validation/replay.py`): Hour-by-hour physical simulation guaranteeing zero constraint violations.
6. **Persistence** (`repositories/optimization_repository.py`): Stores scenarios and dispatch results in SQLite.
