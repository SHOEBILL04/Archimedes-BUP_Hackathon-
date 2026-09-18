# Smart Campus Energy Optimization API

Production-oriented FastAPI service for the BUP CSE Fest 2026 Smart Campus Energy Optimization Challenge.

## Pipeline

```text
POST /optimize-energy
        |
        v
LLM interpreter
        |
        v
Deterministic guardrails
        |
        v
PuLP/CBC linear program
        |
        v
Deterministic replay validator
        |
        v
Strict Pydantic JSON response
```

The LLM is untrusted. It can only propose one of the six supported directive types.
Every directive is validated again before it can affect the optimizer.

## Input contract

```json
{
  "demand_kwh": [24 numbers],
  "base_solar_kwh": [24 numbers],
  "tariff_bdt_per_kwh": [24 numbers],
  "battery": {
    "capacity_kwh": 100,
    "initial_energy_kwh": 40,
    "minimum_energy_kwh": 10,
    "max_charge_kwh_per_hour": 30,
    "max_discharge_kwh_per_hour": 30
  },
  "operator_notes": [
    "Reduce solar from 1 PM to 3 PM by 80%",
    "Do not charge the battery from 18:00 to 20:00"
  ]
}
```

All three hourly arrays must contain exactly 24 values. There must be 1-3 notes.

## Interpretation conflict policy

Overlapping directives are combined deterministically:

- solar reductions: multiply remaining usable factors
- minimum reserves: maximum reserve wins
- no-charge windows: union
- no-discharge windows: union
- max-grid limits: minimum ceiling wins

## Environment

```text
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=8
SOLVER_TIMEOUT_SECONDS=5
API_TIMEOUT_SECONDS=29
HOST=0.0.0.0
PORT=8000
```

If `OPENAI_API_KEY` is missing or the LLM fails, every note safely becomes `no_op`; the deterministic optimizer still runs.

## Run locally

```bash
python3 -m venv .venv
# Creates an isolated Python environment for this service.

source .venv/bin/activate
# Activates the virtual environment in the current shell.

python -m pip install -r requirements.txt
# Installs FastAPI, OpenAI SDK, Pydantic, PuLP and CBC.

export OPENAI_API_KEY="your_key"
# Makes the OpenAI API key available to the application.

uvicorn main:app --host 0.0.0.0 --port 8000
# Starts the FastAPI server on every container/network interface at port 8000.
```

OpenAPI docs: `http://localhost:8000/docs`

Health check:

```bash
curl http://localhost:8000/health
# Sends a GET request to the health endpoint.
```

## Docker

```bash
docker build -t smart-campus-energy .
# Builds the production container image.

docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="your_key" \
  -e OPENAI_MODEL="gpt-4o-mini" \
  smart-campus-energy
# Starts the service and maps host port 8000 to container port 8000.
```

Then:

```bash
curl http://localhost:8000/health
# Verifies that the containerized API is alive.
```

## Production notes

- Keep the API key only in environment/secret management; never commit `.env`.
- Use one Uvicorn process per container and scale containers horizontally.
- The LP has only 24 hourly periods and five continuous variable families, so the optimization model is intentionally small.
- CBC is explicitly time-limited.
- The whole request has a 29-second application budget, leaving a small margin under the 30-second challenge requirement.
- The replay validator independently recomputes all constraints before the response is returned.
