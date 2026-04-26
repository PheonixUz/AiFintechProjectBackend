"""add churn prediction tables

Revision ID: e2c7a8b9d1f0
Revises: d1f6a2b9c3e4
Create Date: 2026-04-26 02:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e2c7a8b9d1f0"
down_revision: Union[str, Sequence[str], None] = "d1f6a2b9c3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "businesses",
        sa.Column("last_observed_active_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "businesses",
        sa.Column("closure_reason", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "businesses",
        sa.Column("closure_confidence_score", sa.Float(), nullable=True),
    )
    op.create_index(
        "ix_businesses_lifecycle_observed",
        "businesses",
        ["is_active", "last_observed_active_date"],
        unique=False,
    )

    op.create_table(
        "churn_model_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("algorithm", sa.String(length=100), nullable=False),
        sa.Column("training_sample_size", sa.Integer(), nullable=False),
        sa.Column("positive_label_rate", sa.Float(), nullable=False),
        sa.Column("auc_roc", sa.Float(), nullable=True),
        sa.Column("auc_pr", sa.Float(), nullable=True),
        sa.Column("f1_score", sa.Float(), nullable=True),
        sa.Column("calibration_error", sa.Float(), nullable=True),
        sa.Column("feature_names", sa.JSON(), nullable=False),
        sa.Column("hyperparameters", sa.JSON(), nullable=False),
        sa.Column("training_period_start", sa.Date(), nullable=True),
        sa.Column("training_period_end", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "model_name",
            "model_version",
            name="uq_churn_model_name_version",
        ),
    )
    op.create_index(
        "ix_churn_model_versions_active",
        "churn_model_versions",
        ["is_active", "created_at"],
        unique=False,
    )

    op.create_table(
        "churn_feature_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=True),
        sa.Column("mcc_code", sa.String(length=4), nullable=False),
        sa.Column("niche", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("radius_m", sa.Float(), nullable=True),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("business_age_months", sa.Integer(), nullable=True),
        sa.Column("employee_count_est", sa.Integer(), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column(
            "revenue_3m_avg_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
        ),
        sa.Column(
            "revenue_6m_avg_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
        ),
        sa.Column(
            "revenue_12m_avg_uzs",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
        ),
        sa.Column("revenue_trend_6m_pct", sa.Float(), nullable=True),
        sa.Column("revenue_volatility_12m_pct", sa.Float(), nullable=True),
        sa.Column("revenue_drop_last_3m_pct", sa.Float(), nullable=True),
        sa.Column("zero_revenue_months_12m", sa.Integer(), nullable=False),
        sa.Column("tx_count_3m_avg", sa.Float(), nullable=True),
        sa.Column("tx_count_12m_avg", sa.Float(), nullable=True),
        sa.Column("tx_count_trend_6m_pct", sa.Float(), nullable=True),
        sa.Column(
            "avg_ticket_3m_uzs",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
        ),
        sa.Column("avg_ticket_change_6m_pct", sa.Float(), nullable=True),
        sa.Column("active_days_last_90d", sa.Integer(), nullable=True),
        sa.Column("inactive_days_last_90d", sa.Integer(), nullable=True),
        sa.Column("online_share_12m_pct", sa.Float(), nullable=True),
        sa.Column("competitor_count_radius", sa.Integer(), nullable=True),
        sa.Column("competitor_density_score", sa.Float(), nullable=True),
        sa.Column("nearby_closed_businesses_24m", sa.Integer(), nullable=True),
        sa.Column("district_failure_rate_24m_pct", sa.Float(), nullable=True),
        sa.Column("macro_risk_score", sa.Float(), nullable=True),
        sa.Column("seasonality_risk_score", sa.Float(), nullable=True),
        sa.Column("data_quality_score", sa.Float(), nullable=False),
        sa.Column("target_closed_within_24m", sa.Boolean(), nullable=True),
        sa.Column("target_closed_date", sa.Date(), nullable=True),
        sa.Column("raw_features", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_churn_features_business_asof",
        "churn_feature_snapshots",
        ["business_id", "as_of_date"],
        unique=False,
    )
    op.create_index(
        "ix_churn_features_location",
        "churn_feature_snapshots",
        ["lat", "lon"],
        unique=False,
    )
    op.create_index(
        "ix_churn_features_mcc_city_asof",
        "churn_feature_snapshots",
        ["mcc_code", "city", "as_of_date"],
        unique=False,
    )
    op.create_index(
        "ix_churn_features_target",
        "churn_feature_snapshots",
        ["target_closed_within_24m"],
        unique=False,
    )

    op.create_table(
        "churn_prediction_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=True),
        sa.Column("feature_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("model_version_id", sa.Integer(), nullable=True),
        sa.Column("mcc_code", sa.String(length=4), nullable=False),
        sa.Column("niche", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("prediction_horizon_months", sa.Integer(), nullable=False),
        sa.Column("closure_probability_24m", sa.Float(), nullable=False),
        sa.Column("survival_probability_24m", sa.Float(), nullable=False),
        sa.Column("risk_bucket", sa.String(length=20), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("top_factor_1", sa.String(length=100), nullable=True),
        sa.Column("top_factor_2", sa.String(length=100), nullable=True),
        sa.Column("top_factor_3", sa.String(length=100), nullable=True),
        sa.Column("prediction_summary", sa.String(length=2000), nullable=True),
        sa.Column("calc_metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["feature_snapshot_id"],
            ["churn_feature_snapshots.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["churn_model_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_churn_runs_business_created",
        "churn_prediction_runs",
        ["business_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_churn_runs_mcc_city_created",
        "churn_prediction_runs",
        ["mcc_code", "city", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_churn_runs_probability",
        "churn_prediction_runs",
        ["closure_probability_24m"],
        unique=False,
    )
    op.create_index(
        "ix_churn_runs_risk_bucket",
        "churn_prediction_runs",
        ["risk_bucket"],
        unique=False,
    )

    op.create_table(
        "churn_risk_factors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("prediction_run_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("factor_name", sa.String(length=100), nullable=False),
        sa.Column("factor_group", sa.String(length=50), nullable=False),
        sa.Column("factor_value", sa.String(length=200), nullable=True),
        sa.Column("baseline_value", sa.String(length=200), nullable=True),
        sa.Column("impact_score", sa.Float(), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("explanation", sa.String(length=1000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["prediction_run_id"],
            ["churn_prediction_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "prediction_run_id",
            "rank",
            name="uq_churn_risk_factor_run_rank",
        ),
    )
    op.create_index(
        "ix_churn_risk_factors_run",
        "churn_risk_factors",
        ["prediction_run_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_churn_risk_factors_run", table_name="churn_risk_factors")
    op.drop_table("churn_risk_factors")
    op.drop_index("ix_churn_runs_risk_bucket", table_name="churn_prediction_runs")
    op.drop_index("ix_churn_runs_probability", table_name="churn_prediction_runs")
    op.drop_index(
        "ix_churn_runs_mcc_city_created",
        table_name="churn_prediction_runs",
    )
    op.drop_index(
        "ix_churn_runs_business_created",
        table_name="churn_prediction_runs",
    )
    op.drop_table("churn_prediction_runs")
    op.drop_index("ix_churn_features_target", table_name="churn_feature_snapshots")
    op.drop_index(
        "ix_churn_features_mcc_city_asof",
        table_name="churn_feature_snapshots",
    )
    op.drop_index("ix_churn_features_location", table_name="churn_feature_snapshots")
    op.drop_index(
        "ix_churn_features_business_asof",
        table_name="churn_feature_snapshots",
    )
    op.drop_table("churn_feature_snapshots")
    op.drop_index(
        "ix_churn_model_versions_active",
        table_name="churn_model_versions",
    )
    op.drop_table("churn_model_versions")
    op.drop_index("ix_businesses_lifecycle_observed", table_name="businesses")
    op.drop_column("businesses", "closure_confidence_score")
    op.drop_column("businesses", "closure_reason")
    op.drop_column("businesses", "last_observed_active_date")
