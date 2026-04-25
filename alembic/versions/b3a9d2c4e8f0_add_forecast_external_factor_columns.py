"""add forecast external factor columns

Revision ID: b3a9d2c4e8f0
Revises: 7c2f4d9a6b11
Create Date: 2026-04-26 00:20:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b3a9d2c4e8f0"
down_revision: Union[str, Sequence[str], None] = "7c2f4d9a6b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "demand_forecast_runs",
        sa.Column("anomaly_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "demand_forecast_runs",
        sa.Column(
            "new_competitor_count_recent",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "demand_forecast_points",
        sa.Column(
            "macro_adjustment_pct",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "demand_forecast_points",
        sa.Column(
            "competitor_pressure_pct",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "demand_forecast_points",
        sa.Column("event_flags", sa.JSON(), nullable=False, server_default="[]"),
    )

    op.alter_column("demand_forecast_runs", "anomaly_count", server_default=None)
    op.alter_column(
        "demand_forecast_runs",
        "new_competitor_count_recent",
        server_default=None,
    )
    op.alter_column(
        "demand_forecast_points",
        "macro_adjustment_pct",
        server_default=None,
    )
    op.alter_column(
        "demand_forecast_points",
        "competitor_pressure_pct",
        server_default=None,
    )
    op.alter_column("demand_forecast_points", "event_flags", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("demand_forecast_points", "event_flags")
    op.drop_column("demand_forecast_points", "competitor_pressure_pct")
    op.drop_column("demand_forecast_points", "macro_adjustment_pct")
    op.drop_column("demand_forecast_runs", "new_competitor_count_recent")
    op.drop_column("demand_forecast_runs", "anomaly_count")
