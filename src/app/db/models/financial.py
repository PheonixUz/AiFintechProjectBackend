"""M-D1 Viability Check uchun moliyaviy jadvallar."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
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


class SectorFinancialBenchmark(Base):
    """
    M-D1 uchun nisha bo'yicha moliyaviy benchmarklar.

    Bu jadval biznes-plan assumptions yetarli bo'lmaganda konservativ default
    sifatida ishlatiladi: marja, fixed-cost ratio, volatility, failure rate.
    """

    __tablename__ = "sector_financial_benchmarks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mcc_code: Mapped[str] = mapped_column(String(4), nullable=False)
    niche: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")

    gross_margin_pct: Mapped[float] = mapped_column(Float, nullable=False)
    variable_cost_pct: Mapped[float] = mapped_column(Float, nullable=False)
    fixed_cost_ratio_pct: Mapped[float] = mapped_column(Float, nullable=False)
    payroll_cost_ratio_pct: Mapped[float] = mapped_column(Float, nullable=False)
    rent_cost_ratio_pct: Mapped[float] = mapped_column(Float, nullable=False)
    marketing_cost_ratio_pct: Mapped[float] = mapped_column(Float, nullable=False)

    avg_monthly_revenue_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    median_monthly_revenue_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    revenue_volatility_pct: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_growth_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    startup_capex_p25_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    startup_capex_median_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    startup_capex_p75_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    working_capital_months: Mapped[float] = mapped_column(
        Float, nullable=False, default=3.0
    )

    two_year_failure_rate_pct: Mapped[float] = mapped_column(Float, nullable=False)
    data_year: Mapped[int] = mapped_column(Integer, nullable=False)
    data_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="synthetic_benchmark"
    )
    notes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

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
            "data_year",
            name="uq_sector_financial_benchmark_mcc_city_year",
        ),
        Index("ix_sector_financial_benchmarks_niche_city", "niche", "city"),
    )


class ViabilityPlanAssumption(Base):
    """
    Foydalanuvchi yoki bank kiritgan biznes-plan assumptions.

    Monte Carlo aynan shu assumptions + benchmarklar asosida ishlaydi.
    """

    __tablename__ = "viability_plan_assumptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mcc_code: Mapped[str] = mapped_column(String(4), nullable=False)
    niche: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")

    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    radius_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    initial_capital_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    startup_capex_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    working_capital_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    loan_amount_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, default=0
    )
    monthly_loan_payment_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, default=0
    )

    expected_monthly_revenue_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    avg_ticket_uzs: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    expected_monthly_transactions: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    gross_margin_pct: Mapped[float] = mapped_column(Float, nullable=False)
    variable_cost_pct: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_fixed_cost_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    monthly_rent_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, default=0
    )
    monthly_payroll_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, default=0
    )
    monthly_utilities_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, default=0
    )
    monthly_marketing_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, default=0
    )
    monthly_other_fixed_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, default=0
    )

    monthly_revenue_growth_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    revenue_volatility_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.20
    )
    tax_rate_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.04)
    owner_draw_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, default=0
    )

    seasonality_profile: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    risk_assumptions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    runs: Mapped[list["ViabilityCheckRun"]] = relationship(back_populates="assumption")

    __table_args__ = (
        Index("ix_viability_assumptions_mcc_city", "mcc_code", "city"),
        Index("ix_viability_assumptions_location", "lat", "lon"),
        Index("ix_viability_assumptions_created", "created_at"),
    )


class ViabilityCheckRun(Base):
    """M-D1 Monte Carlo run natijasi."""

    __tablename__ = "viability_check_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    assumption_id: Mapped[int | None] = mapped_column(
        ForeignKey("viability_plan_assumptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    mcc_code: Mapped[str] = mapped_column(String(4), nullable=False)
    niche: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")

    simulation_months: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    monte_carlo_iterations: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1000
    )
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)

    break_even_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    runway_months: Mapped[float] = mapped_column(Float, nullable=False)
    survival_probability_24m: Mapped[float] = mapped_column(Float, nullable=False)
    cash_out_probability_24m: Mapped[float] = mapped_column(Float, nullable=False)
    probability_break_even_24m: Mapped[float] = mapped_column(Float, nullable=False)

    median_final_cash_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    p10_final_cash_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    p90_final_cash_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    worst_month_cash_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    min_required_capital_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )

    viability_score: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    analysis_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    calc_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assumption: Mapped[ViabilityPlanAssumption | None] = relationship(
        back_populates="runs"
    )
    cashflow_months: Mapped[list["ViabilityCashflowMonth"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_viability_runs_mcc_city_created", "mcc_code", "city", "created_at"),
        Index("ix_viability_runs_recommendation", "recommendation"),
        Index("ix_viability_runs_survival", "survival_probability_24m"),
    )


class ViabilityCashflowMonth(Base):
    """M-D1 run uchun oyma-oy cashflow va Monte Carlo quantile natijalari."""

    __tablename__ = "viability_cashflow_months"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("viability_check_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    month_index: Mapped[int] = mapped_column(Integer, nullable=False)

    expected_revenue_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    p10_revenue_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    p90_revenue_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    variable_cost_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    fixed_cost_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    loan_payment_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    tax_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    net_cashflow_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)

    cumulative_cash_p10_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    cumulative_cash_p50_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    cumulative_cash_p90_uzs: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    probability_negative_cash: Mapped[float] = mapped_column(Float, nullable=False)
    is_break_even_month: Mapped[bool] = mapped_column(nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped[ViabilityCheckRun] = relationship(back_populates="cashflow_months")

    __table_args__ = (
        UniqueConstraint(
            "run_id", "month_index", name="uq_viability_cashflow_run_month"
        ),
        Index("ix_viability_cashflow_run_month", "run_id", "month_index"),
    )
