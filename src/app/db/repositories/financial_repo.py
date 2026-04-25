"""M-D1 Viability Check repository."""

import math
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.business import Business
from app.db.models.financial import (
    SectorFinancialBenchmark,
    ViabilityCashflowMonth,
    ViabilityCheckRun,
    ViabilityPlanAssumption,
)
from app.db.models.transaction import MCCCategory


def _bounding_box(
    lat: float, lon: float, radius_m: float
) -> tuple[float, float, float, float]:
    delta_lat = radius_m / 111_000
    delta_lon = radius_m / (111_000 * math.cos(math.radians(lat)))
    return lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


class FinancialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_mcc_category(self, mcc_code: str) -> MCCCategory | None:
        result = await self._session.execute(
            select(MCCCategory).where(MCCCategory.mcc_code == mcc_code)
        )
        return result.scalar_one_or_none()

    async def get_latest_benchmark(
        self,
        *,
        mcc_code: str,
        city: str,
    ) -> SectorFinancialBenchmark | None:
        result = await self._session.execute(
            select(SectorFinancialBenchmark)
            .where(
                SectorFinancialBenchmark.mcc_code == mcc_code,
                SectorFinancialBenchmark.city == city,
            )
            .order_by(desc(SectorFinancialBenchmark.data_year))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_competitor_count(
        self,
        *,
        mcc_code: str,
        city: str,
        lat: float | None,
        lon: float | None,
        radius_m: float | None,
    ) -> int:
        stmt = select(Business).where(
            Business.mcc_code == mcc_code,
            Business.city == city,
            Business.is_active.is_(True),
        )
        if lat is None or lon is None or radius_m is None:
            result = await self._session.execute(stmt)
            return len(result.scalars().all())

        min_lat, max_lat, min_lon, max_lon = _bounding_box(lat, lon, radius_m)
        stmt = stmt.where(
            Business.lat.between(min_lat, max_lat),
            Business.lon.between(min_lon, max_lon),
        )
        result = await self._session.execute(stmt)
        candidates = list(result.scalars().all())
        return sum(
            1
            for business in candidates
            if _haversine_m(lat, lon, business.lat, business.lon) <= radius_m
        )

    async def save_viability_result(
        self,
        *,
        assumption_payload: dict,
        run_payload: dict,
        cashflow_payloads: list[dict],
    ) -> ViabilityCheckRun:
        assumption = ViabilityPlanAssumption(**assumption_payload)
        self._session.add(assumption)
        await self._session.flush()

        run = ViabilityCheckRun(
            assumption_id=assumption.id,
            **run_payload,
        )
        self._session.add(run)
        await self._session.flush()

        self._session.add_all(
            [
                ViabilityCashflowMonth(run_id=run.id, **cashflow)
                for cashflow in cashflow_payloads
            ]
        )
        await self._session.flush()
        await self._session.refresh(run, ["assumption", "cashflow_months"])
        return run


DEFAULT_FINANCIAL_BENCHMARK = {
    "gross_margin_pct": 0.38,
    "variable_cost_pct": 0.62,
    "fixed_cost_ratio_pct": 0.24,
    "payroll_cost_ratio_pct": 0.12,
    "rent_cost_ratio_pct": 0.08,
    "marketing_cost_ratio_pct": 0.04,
    "avg_monthly_revenue_uzs": Decimal("80000000"),
    "median_monthly_revenue_uzs": Decimal("70000000"),
    "revenue_volatility_pct": 0.24,
    "monthly_growth_pct": 0.01,
    "startup_capex_median_uzs": Decimal("180000000"),
    "working_capital_months": 3.0,
    "two_year_failure_rate_pct": 0.35,
}
