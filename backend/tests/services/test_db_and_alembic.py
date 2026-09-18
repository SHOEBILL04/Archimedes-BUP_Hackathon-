from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models.operator_note import OperatorNote
from app.db.models.optimization import Optimization
from app.db.models.scenario import Scenario
from app.db.models.schedule_entry import ScheduleEntry


def test_database_models_import_and_instantiate() -> None:
    """Ensure all SQLAlchemy models can be instantiated correctly."""
    scenario = Scenario(name="Test Campus")
    assert scenario.name == "Test Campus"

    note = OperatorNote(
        scenario_id=1,
        note_index=0,
        raw_note="Reduce solar",
        directive_type="solar_reduction",
        structured_adjustment={"percent": 80},
        applies=True,
    )
    assert note.directive_type == "solar_reduction"

    opt = Optimization(
        scenario_id=1,
        total_grid_kwh=150.0,
        total_grid_cost_bdt=1800.0,
        verification_status="verified",
    )
    assert opt.total_grid_kwh == 150.0

    entry = ScheduleEntry(
        optimization_id=1,
        hour=0,
        demand_kwh=30.0,
        effective_solar_kwh=0.0,
        solar_used_kwh=0.0,
        battery_charge_kwh=0.0,
        battery_discharge_kwh=0.0,
        battery_energy_after_kwh=40.0,
        grid_kwh=30.0,
        tariff_bdt_per_kwh=8.0,
        grid_cost_bdt=240.0,
    )
    assert entry.hour == 0
    assert entry.grid_cost_bdt == 240.0


def test_sqlite_session_creation_and_transaction() -> None:
    """Verify SQLite session creation and commit operations in memory."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        scenario = Scenario(name="SQLite Verification Scenario")
        session.add(scenario)
        session.commit()
        session.refresh(scenario)

        assert scenario.id is not None
        assert scenario.name == "SQLite Verification Scenario"


def test_alembic_configuration_loads() -> None:
    """Ensure Alembic configuration and revision scripts can be resolved."""
    backend_root = Path(__file__).resolve().parent.parent.parent
    ini_path = backend_root / "alembic.ini"
    assert ini_path.exists(), "alembic.ini must exist in backend root"

    config = Config(str(ini_path))
    script = ScriptDirectory.from_config(config)
    head_rev = script.get_current_head()
    assert head_rev == "0001_initial_schema"
