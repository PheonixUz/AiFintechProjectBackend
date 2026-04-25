"""
Mijoz segmentlari va xarid xulq-atvori.

M-A1 uchun: SOM hisoblashda target segment penetration rate
M-G1 uchun: Customer Segment Profiler
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class CustomerSegment(Base):
    """
    Geografik mikro-zona bo'yicha mijoz segmenti profili.

    K-means/DBSCAN klasterizatsiyasi natijasida hosil bo'ladi.
    """

    __tablename__ = "customer_segments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    segment_name: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "premium", "mass_market", "youth", "bargain_hunter"

    district: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")

    # Segment markazi (geografik)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    radius_m: Mapped[float] = mapped_column(Float, nullable=False, default=500.0)

    # Xarid profili
    avg_monthly_spending_uzs: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False
    )
    purchase_frequency_monthly: Mapped[float] = mapped_column(Float, nullable=False)
    avg_check_uzs: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Top MCC kategoriyalar (JSON array of mcc_codes)
    top_mcc_categories: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Spending taqsimoti kategoriyalar bo'yicha (JSON: {mcc_code: pct})
    spending_distribution: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )

    # Segment hajmi
    estimated_count: Mapped[int] = mapped_column(Integer, nullable=False)

    data_year: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_customer_segments_city_district", "city", "district"),
        Index("ix_customer_segments_name_city", "segment_name", "city"),
        Index("ix_customer_segments_lat_lon", "lat", "lon"),
    )

    def __repr__(self) -> str:
        return f"<CustomerSegment {self.segment_name}: {self.district}, ~{self.estimated_count:,} kishi>"
