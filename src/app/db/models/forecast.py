"""
M-B1 Demand Forecasting uchun jadvallar.

NicheMonthlyRevenue  — LSTM/Prophet uchun oylik tarixiy revenue qatori
DemandForecastRun    — bitta forecast hisoblash run'i va uning metadatasi
DemandForecastPoint  — forecast run ichidagi oyma-oy natijalar
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
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


class NicheMonthlyRevenue(Base):
    """
    Nisha bo'yicha oylik tarixiy revenue agregati.

    Asosiy manba transactions jadvali, lekin forecast modellari uchun
    oyma-oy qatorni qayta-qayta hisoblamaslik maqsadida cache sifatida saqlanadi.
    month qiymati oyning birinchi kuni sifatida yoziladi.
    """

    __tablename__ = "niche_monthly_revenues"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mcc_code: Mapped[str] = mapped_column(String(4), nullable=False)
    niche: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")
    month: Mapped[date] = mapped_column(Date, nullable=False)

    revenue_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_check_uzs: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    active_business_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="bank_transactions"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "mcc_code",
            "city",
            "month",
            name="uq_niche_revenue_mcc_city_month",
        ),
        Index("ix_niche_monthly_revenues_niche_city_month", "niche", "city", "month"),
        Index("ix_niche_monthly_revenues_mcc_month", "mcc_code", "month"),
    )

    def __repr__(self) -> str:
        return (
            f"<NicheMonthlyRevenue {self.mcc_code}/{self.city} "
            f"{self.month}: {self.revenue_uzs}>"
        )


class DemandForecastRun(Base):
    """
    M-B1 hisoblash run'i.

    12/24/36 oylik prognozlar bitta run ostida saqlanadi. Model keyinchalik
    LSTM, Prophet yoki ularning ensemble varianti bo'lishi mumkin.
    """

    __tablename__ = "demand_forecast_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    niche: Mapped[str] = mapped_column(String(100), nullable=False)
    mcc_code: Mapped[str] = mapped_column(String(4), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")

    # Ixtiyoriy lokatsiya filtri: shahar bo'yicha forecast uchun null bo'lishi mumkin.
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    radius_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    horizon_months: Mapped[int] = mapped_column(Integer, nullable=False)
    history_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    history_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_start_month: Mapped[date] = mapped_column(Date, nullable=False)

    model_name: Mapped[str] = mapped_column(
        String(50), nullable=False, default="lstm_prophet_ensemble"
    )
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    algorithm: Mapped[str] = mapped_column(
        String(100), nullable=False, default="LSTM + Facebook Prophet"
    )
    confidence_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.95)

    training_sample_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    train_mape_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    train_rmse_uzs: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    anomaly_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_competitor_count_recent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed")
    analysis_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    calc_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    points: Mapped[list["DemandForecastPoint"]] = relationship(
        back_populates="forecast_run",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_demand_forecast_runs_mcc_city_created",
            "mcc_code",
            "city",
            "created_at",
        ),
        Index("ix_demand_forecast_runs_niche_city", "niche", "city"),
        Index("ix_demand_forecast_runs_location", "lat", "lon"),
    )

    def __repr__(self) -> str:
        return f"<DemandForecastRun {self.mcc_code}/{self.city} {self.horizon_months}m>"


class DemandForecastPoint(Base):
    """
    Forecast run uchun bitta oy natijasi.

    predicted_revenue_uzs — forecast markaziy qiymati
    lower/upper           — ishonch intervali chegaralari
    """

    __tablename__ = "demand_forecast_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    forecast_run_id: Mapped[int] = mapped_column(
        ForeignKey("demand_forecast_runs.id", ondelete="CASCADE"), nullable=False
    )
    forecast_month: Mapped[date] = mapped_column(Date, nullable=False)
    horizon_index: Mapped[int] = mapped_column(Integer, nullable=False)

    predicted_revenue_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    lower_revenue_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    upper_revenue_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    trend_component_uzs: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    seasonal_component_uzs: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    macro_adjustment_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    competitor_pressure_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    event_flags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    confidence_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.95)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    forecast_run: Mapped["DemandForecastRun"] = relationship(back_populates="points")

    __table_args__ = (
        UniqueConstraint(
            "forecast_run_id",
            "forecast_month",
            name="uq_demand_forecast_point_run_month",
        ),
        Index(
            "ix_demand_forecast_points_run_horizon",
            "forecast_run_id",
            "horizon_index",
        ),
        Index("ix_demand_forecast_points_month", "forecast_month"),
    )

    def __repr__(self) -> str:
        return (
            f"<DemandForecastPoint run={self.forecast_run_id} "
            f"{self.forecast_month}: {self.predicted_revenue_uzs}>"
        )
