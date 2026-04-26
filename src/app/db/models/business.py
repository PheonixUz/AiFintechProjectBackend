"""
Ro'yxatdan o'tgan bizneslar (SMB registri).

M-A1 uchun: raqobatchilar soni → SOM hisoblash
M-A3 uchun: to'yinganlik indeksi
M-E2 uchun: yopilish statistikasi
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
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


class Business(Base):
    """
    Faol va yopilgan SMB bizneslar reestri.

    Bank registri + davlat soliq ma'lumotlari asosida to'ldiriladi.
    """

    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Identifikatsiya (anonymlashtirilgan)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mcc_code: Mapped[str] = mapped_column(String(4), nullable=False)
    niche: Mapped[str] = mapped_column(String(100), nullable=False)  # human-readable

    # Joylashuv
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Hayot sikli
    registered_date: Mapped[date] = mapped_column(Date, nullable=False)
    closed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_observed_active_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    closure_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    closure_confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Operatsional ma'lumotlar (taxminiy)
    employee_count_est: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_revenue_est_uzs: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Meta
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="bank_registry"
    )  # "bank_registry", "tax_committee", "manual"
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
        # Raqobatchilar spatial so'rovi: nisha + koordinata bounding box
        Index("ix_businesses_niche_lat_lon", "niche", "lat", "lon"),
        Index("ix_businesses_mcc_city_active", "mcc_code", "city", "is_active"),
        # Yopilish statistikasi so'rovi
        Index("ix_businesses_mcc_closed", "mcc_code", "closed_date"),
        Index(
            "ix_businesses_lifecycle_observed",
            "is_active",
            "last_observed_active_date",
        ),
    )

    def __repr__(self) -> str:
        status = "faol" if self.is_active else "yopilgan"
        return (
            f"<Business {self.id}: {self.niche} "
            f"[{status}] @ ({self.lat:.3f}, {self.lon:.3f})>"
        )
