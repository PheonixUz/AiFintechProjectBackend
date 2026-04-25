"""
M-A1 Market Sizing uchun asinxron repository.

TAM  = butun shahar bo'yicha MCC kategoriyasidagi tranzaksiyalar yig'indisi
SAM  = berilgan radius ichidagi tranzaksiyalar yig'indisi (bounding box + Haversine)
SOM  = SAM × (1 / (raqobatchilar + 1)) × quality_factor

Barcha so'rovlar PostGIS talab qilmaydi:
  bounding box (lat/lon ±delta) → qo'pol filtr, keyin Python'da Haversine aniqlik.
"""

import math
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.business import Business
from app.db.models.market import MarketBenchmark, MarketSizeEstimate
from app.db.models.transaction import Transaction


def _bounding_box(
    lat: float, lon: float, radius_m: float
) -> tuple[float, float, float, float]:
    """Radius asosida taxminiy bounding box qaytaradi (lat/lon daraja)."""
    delta_lat = radius_m / 111_000
    delta_lon = radius_m / (111_000 * math.cos(math.radians(lat)))
    return lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Ikki nuqta orasidagi masofani metrda qaytaradi."""
    r = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


class MarketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # TAM — Total Addressable Market
    # ------------------------------------------------------------------

    async def get_tam(
        self,
        mcc_code: str,
        city: str,
        year: int,
    ) -> Decimal:
        """
        Butun shahar bo'yicha yillik TAM (UZS).
        Hisoblash: sum(amount) × 12 / data_months
        """
        stmt = select(func.sum(Transaction.amount_uzs)).where(
            Transaction.mcc_code == mcc_code,
            Transaction.merchant_city == city,
            func.extract("year", Transaction.transaction_date) == year,
        )
        result = await self._session.execute(stmt)
        total = result.scalar_one_or_none()
        return Decimal(total or 0)

    async def get_tam_monthly_breakdown(
        self,
        mcc_code: str,
        city: str,
        year: int,
    ) -> list[dict]:
        """
        Oyma-oy TAM — M-B2 Seasonality Model uchun ham foydali.
        """
        stmt = (
            select(
                func.extract("month", Transaction.transaction_date).label("month"),
                func.sum(Transaction.amount_uzs).label("total_uzs"),
                func.count(Transaction.id).label("transaction_count"),
            )
            .where(
                Transaction.mcc_code == mcc_code,
                Transaction.merchant_city == city,
                func.extract("year", Transaction.transaction_date) == year,
            )
            .group_by(func.extract("month", Transaction.transaction_date))
            .order_by(func.extract("month", Transaction.transaction_date))
        )
        result = await self._session.execute(stmt)
        return [
            {
                "month": int(row.month),
                "total_uzs": Decimal(row.total_uzs or 0),
                "transaction_count": row.transaction_count,
            }
            for row in result.all()
        ]

    # ------------------------------------------------------------------
    # SAM — Serviceable Addressable Market
    # ------------------------------------------------------------------

    async def get_sam_raw(
        self,
        mcc_code: str,
        lat: float,
        lon: float,
        radius_m: float,
        year: int,
    ) -> list[dict]:
        """
        Bounding box ichidagi tranzaksiyalarni qaytaradi.
        Keyingi qadam: Python'da Haversine bilan aniq radius filtr.
        """
        min_lat, max_lat, min_lon, max_lon = _bounding_box(lat, lon, radius_m)

        stmt = select(
            Transaction.id,
            Transaction.amount_uzs,
            Transaction.merchant_lat,
            Transaction.merchant_lon,
            Transaction.transaction_date,
        ).where(
            Transaction.mcc_code == mcc_code,
            Transaction.merchant_lat.between(min_lat, max_lat),
            Transaction.merchant_lon.between(min_lon, max_lon),
            func.extract("year", Transaction.transaction_date) == year,
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        # Haversine bilan aniq radius filtr
        filtered = []
        for row in rows:
            if row.merchant_lat is None or row.merchant_lon is None:
                continue
            dist = _haversine_m(lat, lon, row.merchant_lat, row.merchant_lon)
            if dist <= radius_m:
                filtered.append(
                    {
                        "id": row.id,
                        "amount_uzs": Decimal(row.amount_uzs),
                        "distance_m": dist,
                    }
                )
        return filtered

    async def get_sam(
        self,
        mcc_code: str,
        lat: float,
        lon: float,
        radius_m: float,
        year: int,
    ) -> Decimal:
        """Radius ichidagi yillik SAM yig'indisi (UZS)."""
        rows = await self.get_sam_raw(mcc_code, lat, lon, radius_m, year)
        return sum((r["amount_uzs"] for r in rows), Decimal(0))

    # ------------------------------------------------------------------
    # SOM — Serviceable Obtainable Market
    # ------------------------------------------------------------------

    async def get_competitor_count(
        self,
        mcc_code: str,
        lat: float,
        lon: float,
        radius_m: float,
    ) -> int:
        """Radius ichidagi faol raqobatchilar soni."""
        min_lat, max_lat, min_lon, max_lon = _bounding_box(lat, lon, radius_m)

        stmt = select(Business.id, Business.lat, Business.lon).where(
            Business.mcc_code == mcc_code,
            Business.is_active.is_(True),
            Business.lat.between(min_lat, max_lat),
            Business.lon.between(min_lon, max_lon),
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        count = 0
        for row in rows:
            dist = _haversine_m(lat, lon, row.lat, row.lon)
            if dist <= radius_m:
                count += 1
        return count

    async def get_som(
        self,
        mcc_code: str,
        lat: float,
        lon: float,
        radius_m: float,
        year: int,
        quality_factor: float = 1.0,
    ) -> Decimal:
        """
        SOM = SAM × (1 / (competitors + 1)) × quality_factor

        quality_factor — lokatsiya skori, biznes sifati va boshqa
        afzalliklarga asosida tuzatish koeffitsienti (0.5 – 1.5).
        """
        sam = await self.get_sam(mcc_code, lat, lon, radius_m, year)
        competitors = await self.get_competitor_count(mcc_code, lat, lon, radius_m)
        share = Decimal(1) / Decimal(competitors + 1)
        return sam * share * Decimal(str(quality_factor))

    # ------------------------------------------------------------------
    # Benchmarks
    # ------------------------------------------------------------------

    async def get_benchmarks(self, mcc_code: str, city: str) -> MarketBenchmark | None:
        """Eng yangi benchmark yozuvini qaytaradi."""
        stmt = (
            select(MarketBenchmark)
            .where(
                MarketBenchmark.mcc_code == mcc_code,
                MarketBenchmark.city == city,
            )
            .order_by(MarketBenchmark.data_year.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Kesh — MarketSizeEstimate
    # ------------------------------------------------------------------

    async def get_cached_estimate(
        self,
        mcc_code: str,
        lat: float,
        lon: float,
        radius_m: float,
        calculation_date: date,
    ) -> MarketSizeEstimate | None:
        """Bugungi sana uchun keshdan TAM/SAM/SOM ni qaytaradi."""
        lat_delta = 0.0001
        lon_delta = 0.0001

        stmt = select(MarketSizeEstimate).where(
            MarketSizeEstimate.mcc_code == mcc_code,
            MarketSizeEstimate.radius_m == radius_m,
            MarketSizeEstimate.lat.between(lat - lat_delta, lat + lat_delta),
            MarketSizeEstimate.lon.between(lon - lon_delta, lon + lon_delta),
            MarketSizeEstimate.calculation_date == calculation_date,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_estimate(
        self,
        mcc_code: str,
        city: str,
        lat: float,
        lon: float,
        radius_m: float,
        tam_uzs: Decimal,
        sam_uzs: Decimal,
        som_uzs: Decimal,
        competitor_count: int,
        market_growth_rate_pct: float,
        confidence_score: float,
        metadata: dict,
        calculation_date: date,
    ) -> MarketSizeEstimate:
        estimate = MarketSizeEstimate(
            niche=mcc_code,
            mcc_code=mcc_code,
            city=city,
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            tam_uzs=tam_uzs,
            sam_uzs=sam_uzs,
            som_uzs=som_uzs,
            competitor_count=competitor_count,
            market_growth_rate_pct=market_growth_rate_pct,
            confidence_score=confidence_score,
            calc_metadata=metadata,
            calculation_date=calculation_date,
        )
        self._session.add(estimate)
        await self._session.flush()
        return estimate
