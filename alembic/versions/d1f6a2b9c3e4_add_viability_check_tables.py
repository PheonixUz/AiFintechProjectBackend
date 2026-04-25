"""add viability check tables

Revision ID: d1f6a2b9c3e4
Revises: b3a9d2c4e8f0
Create Date: 2026-04-26 01:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d1f6a2b9c3e4"
down_revision: Union[str, Sequence[str], None] = "b3a9d2c4e8f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sector_financial_benchmarks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mcc_code", sa.String(length=4), nullable=False),
        sa.Column("niche", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("gross_margin_pct", sa.Float(), nullable=False),
        sa.Column("variable_cost_pct", sa.Float(), nullable=False),
        sa.Column("fixed_cost_ratio_pct", sa.Float(), nullable=False),
        sa.Column("payroll_cost_ratio_pct", sa.Float(), nullable=False),
        sa.Column("rent_cost_ratio_pct", sa.Float(), nullable=False),
        sa.Column("marketing_cost_ratio_pct", sa.Float(), nullable=False),
        sa.Column(
            "avg_monthly_revenue_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "median_monthly_revenue_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column("revenue_volatility_pct", sa.Float(), nullable=False),
        sa.Column("monthly_growth_pct", sa.Float(), nullable=False),
        sa.Column(
            "startup_capex_p25_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "startup_capex_median_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "startup_capex_p75_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column("working_capital_months", sa.Float(), nullable=False),
        sa.Column("two_year_failure_rate_pct", sa.Float(), nullable=False),
        sa.Column("data_year", sa.Integer(), nullable=False),
        sa.Column("data_source", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=False),
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
            "data_year",
            name="uq_sector_financial_benchmark_mcc_city_year",
        ),
    )
    op.create_index(
        "ix_sector_financial_benchmarks_niche_city",
        "sector_financial_benchmarks",
        ["niche", "city"],
        unique=False,
    )

    op.create_table(
        "viability_plan_assumptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_name", sa.String(length=200), nullable=True),
        sa.Column("mcc_code", sa.String(length=4), nullable=False),
        sa.Column("niche", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("radius_m", sa.Float(), nullable=True),
        sa.Column(
            "initial_capital_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "startup_capex_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "working_capital_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "loan_amount_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "monthly_loan_payment_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "expected_monthly_revenue_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column("avg_ticket_uzs", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("expected_monthly_transactions", sa.Integer(), nullable=True),
        sa.Column("gross_margin_pct", sa.Float(), nullable=False),
        sa.Column("variable_cost_pct", sa.Float(), nullable=False),
        sa.Column(
            "monthly_fixed_cost_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "monthly_rent_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "monthly_payroll_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "monthly_utilities_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "monthly_marketing_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "monthly_other_fixed_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column("monthly_revenue_growth_pct", sa.Float(), nullable=False),
        sa.Column("revenue_volatility_pct", sa.Float(), nullable=False),
        sa.Column("tax_rate_pct", sa.Float(), nullable=False),
        sa.Column(
            "owner_draw_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column("seasonality_profile", sa.JSON(), nullable=False),
        sa.Column("risk_assumptions", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=True),
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
        "ix_viability_assumptions_created",
        "viability_plan_assumptions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_viability_assumptions_location",
        "viability_plan_assumptions",
        ["lat", "lon"],
        unique=False,
    )
    op.create_index(
        "ix_viability_assumptions_mcc_city",
        "viability_plan_assumptions",
        ["mcc_code", "city"],
        unique=False,
    )

    op.create_table(
        "viability_check_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("assumption_id", sa.Integer(), nullable=True),
        sa.Column("mcc_code", sa.String(length=4), nullable=False),
        sa.Column("niche", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("simulation_months", sa.Integer(), nullable=False),
        sa.Column("monte_carlo_iterations", sa.Integer(), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=True),
        sa.Column("break_even_month", sa.Integer(), nullable=True),
        sa.Column("runway_months", sa.Float(), nullable=False),
        sa.Column("survival_probability_24m", sa.Float(), nullable=False),
        sa.Column("cash_out_probability_24m", sa.Float(), nullable=False),
        sa.Column("probability_break_even_24m", sa.Float(), nullable=False),
        sa.Column(
            "median_final_cash_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "p10_final_cash_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "p90_final_cash_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "worst_month_cash_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "min_required_capital_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column("viability_score", sa.Float(), nullable=False),
        sa.Column("recommendation", sa.String(length=20), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("analysis_summary", sa.String(length=2000), nullable=True),
        sa.Column("calc_metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assumption_id"],
            ["viability_plan_assumptions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_viability_runs_mcc_city_created",
        "viability_check_runs",
        ["mcc_code", "city", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_viability_runs_recommendation",
        "viability_check_runs",
        ["recommendation"],
        unique=False,
    )
    op.create_index(
        "ix_viability_runs_survival",
        "viability_check_runs",
        ["survival_probability_24m"],
        unique=False,
    )

    op.create_table(
        "viability_cashflow_months",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("month_index", sa.Integer(), nullable=False),
        sa.Column(
            "expected_revenue_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "p10_revenue_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "p90_revenue_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "variable_cost_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "fixed_cost_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "loan_payment_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column("tax_uzs", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column(
            "net_cashflow_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "cumulative_cash_p10_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "cumulative_cash_p50_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column(
            "cumulative_cash_p90_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
        ),
        sa.Column("probability_negative_cash", sa.Float(), nullable=False),
        sa.Column("is_break_even_month", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["viability_check_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "month_index",
            name="uq_viability_cashflow_run_month",
        ),
    )
    op.create_index(
        "ix_viability_cashflow_run_month",
        "viability_cashflow_months",
        ["run_id", "month_index"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_viability_cashflow_run_month",
        table_name="viability_cashflow_months",
    )
    op.drop_table("viability_cashflow_months")
    op.drop_index("ix_viability_runs_survival", table_name="viability_check_runs")
    op.drop_index(
        "ix_viability_runs_recommendation",
        table_name="viability_check_runs",
    )
    op.drop_index(
        "ix_viability_runs_mcc_city_created",
        table_name="viability_check_runs",
    )
    op.drop_table("viability_check_runs")
    op.drop_index(
        "ix_viability_assumptions_mcc_city",
        table_name="viability_plan_assumptions",
    )
    op.drop_index(
        "ix_viability_assumptions_location",
        table_name="viability_plan_assumptions",
    )
    op.drop_index(
        "ix_viability_assumptions_created",
        table_name="viability_plan_assumptions",
    )
    op.drop_table("viability_plan_assumptions")
    op.drop_index(
        "ix_sector_financial_benchmarks_niche_city",
        table_name="sector_financial_benchmarks",
    )
    op.drop_table("sector_financial_benchmarks")
