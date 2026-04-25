"""
M-A1 Market Sizing uchun maxsus jadvallar.

MarketBenchmark  — nisha bo'yicha sanoat normalari (TAM hisoblashda ishlatiladi)
MarketSizeEstimate — hisoblangan TAM/SAM/SOM natijalari keshi
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class MarketBenchmark(Base):
    """
    Nisha va shahar bo'yicha sanoat benchmarklari.

    Bank tranzaksiyalari tahlili va tashqi ma'lumotlar asosida to'ldiriladi.
    M-A1 bottom-up TAM hisoblashda: avg_monthly_revenue × competitor_count → SAM taxmin
    """

    __tablename__ = "market_benchmarks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mcc_code: Mapped[str] = mapped_column(String(4), nullable=False)
    niche: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")

    # Daromad normalari
    avg_monthly_revenue_uzs: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    median_monthly_revenue_uzs: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    p25_monthly_revenue_uzs: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    p75_monthly_revenue_uzs: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Tranzaksiya normalari
    avg_monthly_transactions: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_check_uzs: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Moliyaviy ko'rsatkichlar
    gross_margin_pct: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 – 1.0
    avg_employee_count: Mapped[float] = mapped_column(Float, nullable=False)
    revenue_per_sqm_monthly_uzs: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )

    # O'sish ko'rsatkichi (yillik, %)
    annual_growth_rate_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    data_year: Mapped[int] = mapped_column(Integer, nullable=False)
    data_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="bank_transactions"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("mcc_code", "city", "data_year", name="uq_benchmark_mcc_city_year"),
        Index("ix_market_benchmarks_niche_city", "niche", "city"),
    )

    def __repr__(self) -> str:
        return f"<MarketBenchmark {self.niche} / {self.city} ({self.data_year})>"


class MarketSizeEstimate(Base):
    """
    M-A1 hisoblash natijalari keshi.

    Bir xil (nisha, lokatsiya, radius) kombinatsiyasi uchun
    qayta hisoblashdan saqlanish maqsadida saqlanadi.

    TAM — Total Addressable Market (butun shahar bozori)
    SAM — Serviceable Addressable Market (radius ichidagi bozor)
    SOM — Serviceable Obtainable Market (real qo'lga kiritsa bo'ladigan ulush)
    """

    __tablename__ = "market_size_estimates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    niche: Mapped[str] = mapped_column(String(100), nullable=False)
    mcc_code: Mapped[str] = mapped_column(String(4), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")

    # So'rov parametrlari
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    radius_m: Mapped[float] = mapped_column(Float, nullable=False)

    # Natijalar (yillik, UZS)
    tam_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    sam_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    som_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)

    # Kontekst
    competitor_count: Mapped[int] = mapped_column(Integer, nullable=False)
    market_growth_rate_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # 0.0 – 1.0: ma'lumotlar sifati va to'liqligi
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Qo'shimcha ma'lumotlar (hisoblash tafsilotlari)
    calc_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    calculation_date: Mapped[date] = mapped_column(Date, nullable=False, default=func.current_date())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_market_estimates_niche_city_date", "niche", "city", "calculation_date"),
        Index("ix_market_estimates_lat_lon", "lat", "lon"),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketSizeEstimate {self.niche}: "
            f"TAM={self.tam_uzs:,.0f}, SAM={self.sam_uzs:,.0f}, SOM={self.som_uzs:,.0f}>"
        )
