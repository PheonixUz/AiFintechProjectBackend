"""
GET API endpointlari uchun umumiy data repository.

Barcha read-only so'rovlar shu joyda — MCC, benchmarks, raqobatchilar,
tranzaksiyalar, aholi, POI, mijoz segmentlari va bozor tahminlari.
"""

import math
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.business import Business
from app.db.models.customer import CustomerSegment
from app.db.models.location import PointOfInterest, PopulationZone
from app.db.models.market import MarketBenchmark, MarketSizeEstimate
from app.db.models.transaction import MCCCategory, Transaction


def _bounding_box(lat: float, lon: float, radius_m: float) -> tuple[float, float, float, float]:
    delta_lat = radius_m / 111_000
    delta_lon = radius_m / (111_000 * math.cos(math.radians(lat)))
    return lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class DataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── MCC Kategoriyalar ──────────────────────────────────────────────────────

    async def get_mcc_categories(self, active_only: bool = True) -> list[MCCCategory]:
        stmt = select(MCCCategory).order_by(MCCCategory.mcc_code)
        if active_only:
            stmt = stmt.where(MCCCategory.is_active.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_mcc_by_parent(self, parent_category: str) -> list[MCCCategory]:
        stmt = (
            select(MCCCategory)
            .where(MCCCategory.parent_category == parent_category)
            .order_by(MCCCategory.mcc_code)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Benchmarklar ───────────────────────────────────────────────────────────

    async def get_benchmarks(
        self,
        city: str,
        mcc_code: str | None = None,
        niche: str | None = None,
    ) -> list[MarketBenchmark]:
        stmt = select(MarketBenchmark).where(MarketBenchmark.city == city)
        if mcc_code:
            stmt = stmt.where(MarketBenchmark.mcc_code == mcc_code)
        if niche:
            stmt = stmt.where(MarketBenchmark.niche == niche)
        stmt = stmt.order_by(MarketBenchmark.data_year.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Raqobatchilar ──────────────────────────────────────────────────────────

    async def get_competitors(
        self,
        niche: str,
        lat: float,
        lon: float,
        radius_m: float,
        active_only: bool = True,
    ) -> list[dict]:
        min_lat, max_lat, min_lon, max_lon = _bounding_box(lat, lon, radius_m)
        stmt = select(Business).where(
            Business.niche == niche,
            Business.lat.between(min_lat, max_lat),
            Business.lon.between(min_lon, max_lon),
        )
        if active_only:
            stmt = stmt.where(Business.is_active.is_(True))
        result = await self._session.execute(stmt)
        businesses = result.scalars().all()

        out = []
        for b in businesses:
            dist = _haversine_m(lat, lon, b.lat, b.lon)
            if dist <= radius_m:
                out.append({"business": b, "distance_m": dist})
        out.sort(key=lambda x: x["distance_m"])
        return out

    # ── Tranzaksiya statistikasi ───────────────────────────────────────────────

    async def get_transaction_annual_total(
        self, mcc_code: str, city: str, year: int
    ) -> Decimal:
        stmt = select(func.sum(Transaction.amount_uzs)).where(
            Transaction.mcc_code == mcc_code,
            Transaction.merchant_city == city,
            func.extract("year", Transaction.transaction_date) == year,
        )
        result = await self._session.execute(stmt)
        total = result.scalar_one_or_none()
        return Decimal(total or 0)

    async def get_transaction_monthly_breakdown(
        self, mcc_code: str, city: str, year: int
    ) -> list[dict]:
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

    # ── Aholi zonalari ─────────────────────────────────────────────────────────

    async def get_population_zones(
        self,
        lat: float,
        lon: float,
        radius_m: float,
        city: str | None = None,
    ) -> list[PopulationZone]:
        min_lat, max_lat, min_lon, max_lon = _bounding_box(lat, lon, radius_m)
        stmt = select(PopulationZone).where(
            PopulationZone.lat.between(min_lat, max_lat),
            PopulationZone.lon.between(min_lon, max_lon),
        )
        if city:
            stmt = stmt.where(PopulationZone.city == city)
        result = await self._session.execute(stmt)
        zones = result.scalars().all()

        return [z for z in zones if _haversine_m(lat, lon, z.lat, z.lon) <= radius_m]

    # ── POI ────────────────────────────────────────────────────────────────────

    async def get_pois(
        self,
        lat: float,
        lon: float,
        radius_m: float,
        poi_type: str | None = None,
        city: str | None = None,
    ) -> list[dict]:
        min_lat, max_lat, min_lon, max_lon = _bounding_box(lat, lon, radius_m)
        stmt = select(PointOfInterest).where(
            PointOfInterest.lat.between(min_lat, max_lat),
            PointOfInterest.lon.between(min_lon, max_lon),
            PointOfInterest.is_active.is_(True),
        )
        if poi_type:
            stmt = stmt.where(PointOfInterest.poi_type == poi_type)
        if city:
            stmt = stmt.where(PointOfInterest.city == city)
        result = await self._session.execute(stmt)
        pois = result.scalars().all()

        out = []
        for p in pois:
            dist = _haversine_m(lat, lon, p.lat, p.lon)
            if dist <= radius_m:
                out.append({"poi": p, "distance_m": dist})
        out.sort(key=lambda x: x["distance_m"])
        return out

    # ── Mijoz segmentlari ──────────────────────────────────────────────────────

    async def get_customer_segments(
        self,
        lat: float,
        lon: float,
        radius_m: float,
        city: str | None = None,
    ) -> list[CustomerSegment]:
        min_lat, max_lat, min_lon, max_lon = _bounding_box(lat, lon, radius_m)
        stmt = select(CustomerSegment).where(
            CustomerSegment.lat.between(min_lat, max_lat),
            CustomerSegment.lon.between(min_lon, max_lon),
        )
        if city:
            stmt = stmt.where(CustomerSegment.city == city)
        result = await self._session.execute(stmt)
        segments = result.scalars().all()

        return [s for s in segments if _haversine_m(lat, lon, s.lat, s.lon) <= radius_m]

    # ── Bozor tahminlari ───────────────────────────────────────────────────────

    async def get_market_estimates(
        self,
        niche: str,
        city: str | None = None,
        limit: int = 10,
    ) -> list[MarketSizeEstimate]:
        stmt = (
            select(MarketSizeEstimate)
            .where(MarketSizeEstimate.niche == niche)
            .order_by(MarketSizeEstimate.calculation_date.desc())
            .limit(limit)
        )
        if city:
            stmt = stmt.where(MarketSizeEstimate.city == city)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_market_estimate_by_location(
        self,
        niche: str,
        lat: float,
        lon: float,
        radius_m: float,
        calculation_date: date | None = None,
    ) -> MarketSizeEstimate | None:
        lat_delta, lon_delta = 0.0001, 0.0001
        stmt = select(MarketSizeEstimate).where(
            MarketSizeEstimate.niche == niche,
            MarketSizeEstimate.radius_m == radius_m,
            MarketSizeEstimate.lat.between(lat - lat_delta, lat + lat_delta),
            MarketSizeEstimate.lon.between(lon - lon_delta, lon + lon_delta),
        )
        if calculation_date:
            stmt = stmt.where(MarketSizeEstimate.calculation_date == calculation_date)
        stmt = stmt.order_by(MarketSizeEstimate.calculation_date.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
