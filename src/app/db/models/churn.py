"""M-E2 Churn Prediction uchun DB modellari."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


class ChurnModelVersion(Base):
    """
    XGBoost model registry.

    Har bir prediction qaysi model versiyasi va qaysi training metrikalari
    bilan chiqqanini audit qilish uchun saqlanadi.
    """

    __tablename__ = "churn_model_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="xgboost_smb_churn",
    )
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    algorithm: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="XGBoost",
    )
    training_sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    positive_label_rate: Mapped[float] = mapped_column(Float, nullable=False)
    auc_roc: Mapped[float | None] = mapped_column(Float, nullable=True)
    auc_pr: Mapped[float | None] = mapped_column(Float, nullable=True)
    f1_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    calibration_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    feature_names: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    hyperparameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    training_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    training_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    prediction_runs: Mapped[list["ChurnPredictionRun"]] = relationship(
        back_populates="model_version"
    )

    __table_args__ = (
        UniqueConstraint(
            "model_name",
            "model_version",
            name="uq_churn_model_name_version",
        ),
        Index("ix_churn_model_versions_active", "is_active", "created_at"),
    )


class ChurnFeatureSnapshot(Base):
    """
    Scoring paytidagi SMB feature snapshot.

    XGBoost kirishidagi barcha muhim agregatlar shu yerda saqlanadi:
    revenue trend, volatility, transaction activity, raqobat va lifecycle.
    """

    __tablename__ = "churn_feature_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True,
    )
    mcc_code: Mapped[str] = mapped_column(String(4), nullable=False)
    niche: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    radius_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)

    business_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employee_count_est: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)

    revenue_3m_avg_uzs: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2),
        nullable=True,
    )
    revenue_6m_avg_uzs: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2),
        nullable=True,
    )
    revenue_12m_avg_uzs: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2),
        nullable=True,
    )
    revenue_trend_6m_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue_volatility_12m_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    revenue_drop_last_3m_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    zero_revenue_months_12m: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    tx_count_3m_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    tx_count_12m_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    tx_count_trend_6m_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_ticket_3m_uzs: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )
    avg_ticket_change_6m_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    active_days_last_90d: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inactive_days_last_90d: Mapped[int | None] = mapped_column(Integer, nullable=True)
    online_share_12m_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    competitor_count_radius: Mapped[int | None] = mapped_column(Integer, nullable=True)
    competitor_density_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    nearby_closed_businesses_24m: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    district_failure_rate_24m_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    macro_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    seasonality_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality_score: Mapped[float] = mapped_column(Float, nullable=False)

    target_closed_within_24m: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    target_closed_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    raw_features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    prediction_runs: Mapped[list["ChurnPredictionRun"]] = relationship(
        back_populates="feature_snapshot"
    )

    __table_args__ = (
        Index("ix_churn_features_business_asof", "business_id", "as_of_date"),
        Index("ix_churn_features_mcc_city_asof", "mcc_code", "city", "as_of_date"),
        Index("ix_churn_features_location", "lat", "lon"),
        Index("ix_churn_features_target", "target_closed_within_24m"),
    )


class ChurnPredictionRun(Base):
    """M-E2 XGBoost prediction natijasi."""

    __tablename__ = "churn_prediction_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True,
    )
    feature_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("churn_feature_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("churn_model_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    mcc_code: Mapped[str] = mapped_column(String(4), nullable=False)
    niche: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    prediction_horizon_months: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=24,
    )

    closure_probability_24m: Mapped[float] = mapped_column(Float, nullable=False)
    survival_probability_24m: Mapped[float] = mapped_column(Float, nullable=False)
    risk_bucket: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)

    top_factor_1: Mapped[str | None] = mapped_column(String(100), nullable=True)
    top_factor_2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    top_factor_3: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prediction_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    calc_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    feature_snapshot: Mapped[ChurnFeatureSnapshot] = relationship(
        back_populates="prediction_runs"
    )
    model_version: Mapped[ChurnModelVersion | None] = relationship(
        back_populates="prediction_runs"
    )
    risk_factors: Mapped[list["ChurnRiskFactor"]] = relationship(
        back_populates="prediction_run",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_churn_runs_business_created", "business_id", "created_at"),
        Index("ix_churn_runs_mcc_city_created", "mcc_code", "city", "created_at"),
        Index("ix_churn_runs_risk_bucket", "risk_bucket"),
        Index("ix_churn_runs_probability", "closure_probability_24m"),
    )


class ChurnRiskFactor(Base):
    """Prediction uchun top risk faktorlar va ularning ta'siri."""

    __tablename__ = "churn_risk_factors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    prediction_run_id: Mapped[int] = mapped_column(
        ForeignKey("churn_prediction_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    factor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    factor_group: Mapped[str] = mapped_column(String(50), nullable=False)
    factor_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    baseline_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    explanation: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    prediction_run: Mapped[ChurnPredictionRun] = relationship(
        back_populates="risk_factors"
    )

    __table_args__ = (
        UniqueConstraint(
            "prediction_run_id",
            "rank",
            name="uq_churn_risk_factor_run_rank",
        ),
        Index("ix_churn_risk_factors_run", "prediction_run_id"),
    )
