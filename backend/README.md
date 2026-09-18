# Smart Campus Energy Optimization Platform - Backend

Production-grade FastAPI service providing 24-hour campus energy dispatch optimization, SQLite persistence, and extensible service interfaces for LLM directive interpretation and PuLP/CBC linear programming.

## Architecture

- **`app/api/`**: HTTP layer exposing `/health` and `/api/v1/optimize-energy`.
- **`app/schemas/`**: Pydantic v2 data transfer models.
- **`app/services/`**: Orchestration logic for optimization, LLM interpretation, and verification.
- **`app/repositories/`**: SQLAlchemy persistence layer isolating SQLite operations.
- **`app/db/`**: Database models (`Scenario`, `OperatorNote`, `Optimization`, `ScheduleEntry`) and Alembic migrations.
- **`app/core/`**: Pydantic Settings configuration, logging, and custom exception types.

## Local Development

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 2. Run Database Migrations

```bash
alembic upgrade head
```

### 3. Run the Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access Swagger UI documentation at: `http://localhost:8000/docs`

### 4. Run Tests & Linting

```bash
pytest
ruff check .
```
