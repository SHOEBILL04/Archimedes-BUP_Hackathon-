"""Initial schema for scenarios, notes, optimizations, and schedule entries

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-09-18 19:35:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. scenarios table
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. operator_notes table
    op.create_table(
        "operator_notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("note_index", sa.Integer(), nullable=False),
        sa.Column("raw_note", sa.Text(), nullable=False),
        sa.Column("directive_type", sa.String(length=64), nullable=False),
        sa.Column("structured_adjustment", sa.JSON(), nullable=True),
        sa.Column("applies", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operator_notes_scenario_id"), "operator_notes", ["scenario_id"])

    # 3. optimizations table
    op.create_table(
        "optimizations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("total_grid_kwh", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_grid_cost_bdt", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("verification_status", sa.String(length=32), nullable=False, server_default="verified"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_optimizations_scenario_id"), "optimizations", ["scenario_id"])

    # 4. schedule_entries table
    op.create_table(
        "schedule_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("optimization_id", sa.Integer(), nullable=False),
        sa.Column("hour", sa.Integer(), nullable=False),
        sa.Column("demand_kwh", sa.Float(), nullable=False),
        sa.Column("effective_solar_kwh", sa.Float(), nullable=False),
        sa.Column("solar_used_kwh", sa.Float(), nullable=False),
        sa.Column("battery_charge_kwh", sa.Float(), nullable=False),
        sa.Column("battery_discharge_kwh", sa.Float(), nullable=False),
        sa.Column("battery_energy_after_kwh", sa.Float(), nullable=False),
        sa.Column("grid_kwh", sa.Float(), nullable=False),
        sa.Column("tariff_bdt_per_kwh", sa.Float(), nullable=False),
        sa.Column("grid_cost_bdt", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["optimization_id"], ["optimizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schedule_entries_optimization_id"), "schedule_entries", ["optimization_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_schedule_entries_optimization_id"), table_name="schedule_entries")
    op.drop_table("schedule_entries")
    op.drop_index(op.f("ix_optimizations_scenario_id"), table_name="optimizations")
    op.drop_table("optimizations")
    op.drop_index(op.f("ix_operator_notes_scenario_id"), table_name="operator_notes")
    op.drop_table("operator_notes")
    op.drop_table("scenarios")
