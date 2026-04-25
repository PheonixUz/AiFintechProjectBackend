"""
Geografik zonalar va qiziqish nuqtalari (POI).

M-A1 uchun: bottom-up TAM hisoblash → aholi soni × xarid kuchi
M-C1 uchun: anchor effect, traffic, isochrone demand
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
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


class PopulationZone(Base):
    """
    Aholi ma'lumotlari geografik zona bo'yicha.

    Bottom-up TAM hisoblash uchun:
      TAM_bottomup = population × penetration_rate × avg_annual_spending_per_capita
    """

    __tablename__ = "population_zones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    zone_name: Mapped[str] = mapped_column(String(200), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")

    # Zona markazi va qamrovi
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    radius_m: Mapped[float] = mapped_column(Float, nullable=False, default=500.0)

    # Demografiya
    total_population: Mapped[int] = mapped_column(Integer, nullable=False)
    working_age_population: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 18–65
    youth_population: Mapped[int] = mapped_column(Integer, nullable=False)  # 18–35

    # Iqtisodiy ko'rsatkichlar
    avg_monthly_income_uzs: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False
    )
    # O'rtacha oylik iste'mol xarajatlari (daromadning ~70%)
    avg_monthly_spending_uzs: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False
    )

    data_year: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_population_zones_city_district", "city", "district"),
        Index("ix_population_zones_lat_lon", "lat", "lon"),
    )

    def __repr__(self) -> str:
        return f"<PopulationZone {self.zone_name}: {self.total_population:,} kishi>"


class PointOfInterest(Base):
    """
    Qiziqish nuqtalari — anchor effect va traffic modellari uchun.

    M-C1 uchun: bozor, masjid, maktab, savdo markazi kabi anchor ob'ektlar
    traffic va lokatsiya skori hisoblashda ishlatiladi.
    """

    __tablename__ = "points_of_interest"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # "market", "mosque", "school", "mall", "park", "hospital", "university", "transport_hub"
    poi_type: Mapped[str] = mapped_column(String(50), nullable=False)

    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")

    # Anchor kuchi (traffic yaratish qobiliyati)
    capacity_est: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_visitors_est: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_poi_type_city", "poi_type", "city"),
        Index("ix_poi_lat_lon", "lat", "lon"),
    )

    def __repr__(self) -> str:
        return f"<POI {self.poi_type}: {self.name} @ ({self.lat:.3f}, {self.lon:.3f})>"
