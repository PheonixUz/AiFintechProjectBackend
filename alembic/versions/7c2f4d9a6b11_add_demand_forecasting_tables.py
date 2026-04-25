"""add demand forecasting tables

Revision ID: 7c2f4d9a6b11
Revises: 13f388a64569
Create Date: 2026-04-25 23:40:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c2f4d9a6b11"
down_revision: Union[str, Sequence[str], None] = "13f388a64569"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "niche_monthly_revenues",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mcc_code", sa.String(length=4), nullable=False),
        sa.Column("niche", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("revenue_uzs", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("transaction_count", sa.Integer(), nullable=False),
        sa.Column("avg_check_uzs", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("active_business_count", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mcc_code",
            "city",
            "month",
            name="uq_niche_revenue_mcc_city_month",
        ),
    )
    op.create_index(
        "ix_niche_monthly_revenues_mcc_month",
        "niche_monthly_revenues",
        ["mcc_code", "month"],
        unique=False,
    )
    op.create_index(
        "ix_niche_monthly_revenues_niche_city_month",
        "niche_monthly_revenues",
        ["niche", "city", "month"],
        unique=False,
    )

    op.create_table(
        "demand_forecast_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("niche", sa.String(length=100), nullable=False),
        sa.Column("mcc_code", sa.String(length=4), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("radius_m", sa.Float(), nullable=True),
        sa.Column("horizon_months", sa.Integer(), nullable=False),
        sa.Column("history_start_date", sa.Date(), nullable=False),
        sa.Column("history_end_date", sa.Date(), nullable=False),
        sa.Column("forecast_start_month", sa.Date(), nullable=False),
        sa.Column("model_name", sa.String(length=50), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("algorithm", sa.String(length=100), nullable=False),
        sa.Column("confidence_level", sa.Float(), nullable=False),
        sa.Column("training_sample_size", sa.Integer(), nullable=False),
        sa.Column("train_mape_pct", sa.Float(), nullable=True),
        sa.Column("train_rmse_uzs", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("analysis_summary", sa.String(length=2000), nullable=True),
        sa.Column("calc_metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_demand_forecast_runs_location",
        "demand_forecast_runs",
        ["lat", "lon"],
        unique=False,
    )
    op.create_index(
        "ix_demand_forecast_runs_mcc_city_created",
        "demand_forecast_runs",
        ["mcc_code", "city", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_demand_forecast_runs_niche_city",
        "demand_forecast_runs",
        ["niche", "city"],
        unique=False,
    )

    op.create_table(
        "demand_forecast_points",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("forecast_run_id", sa.Integer(), nullable=False),
        sa.Column("forecast_month", sa.Date(), nullable=False),
        sa.Column("horizon_index", sa.Integer(), nullable=False),
        sa.Column(
            "predicted_revenue_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "lower_revenue_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "upper_revenue_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "trend_component_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
        ),
        sa.Column(
            "seasonal_component_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
        ),
        sa.Column("confidence_level", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["forecast_run_id"],
            ["demand_forecast_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "forecast_run_id",
            "forecast_month",
            name="uq_demand_forecast_point_run_month",
        ),
    )
    op.create_index(
        "ix_demand_forecast_points_month",
        "demand_forecast_points",
        ["forecast_month"],
        unique=False,
    )
    op.create_index(
        "ix_demand_forecast_points_run_horizon",
        "demand_forecast_points",
        ["forecast_run_id", "horizon_index"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_demand_forecast_points_run_horizon",
        table_name="demand_forecast_points",
    )
    op.drop_index(
        "ix_demand_forecast_points_month",
        table_name="demand_forecast_points",
    )
    op.drop_table("demand_forecast_points")
    op.drop_index(
        "ix_demand_forecast_runs_niche_city",
        table_name="demand_forecast_runs",
    )
    op.drop_index(
        "ix_demand_forecast_runs_mcc_city_created",
        table_name="demand_forecast_runs",
    )
    op.drop_index(
        "ix_demand_forecast_runs_location",
        table_name="demand_forecast_runs",
    )
    op.drop_table("demand_forecast_runs")
    op.drop_index(
        "ix_niche_monthly_revenues_niche_city_month",
        table_name="niche_monthly_revenues",
    )
    op.drop_index(
        "ix_niche_monthly_revenues_mcc_month",
        table_name="niche_monthly_revenues",
    )
    op.drop_table("niche_monthly_revenues")
