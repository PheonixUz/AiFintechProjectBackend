"""M-B1 Demand Forecasting repository."""

import math
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.business import Business
from app.db.models.forecast import (
    DemandForecastPoint,
    DemandForecastRun,
    NicheMonthlyRevenue,
)
from app.db.models.transaction import MCCCategory, Transaction


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


class ForecastRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_monthly_revenue_history(
        self,
        *,
        mcc_code: str,
        city: str,
        start_month: date | None = None,
        end_month: date | None = None,
    ) -> list[NicheMonthlyRevenue]:
        stmt = (
            select(NicheMonthlyRevenue)
            .where(
                NicheMonthlyRevenue.mcc_code == mcc_code,
                NicheMonthlyRevenue.city == city,
            )
            .order_by(NicheMonthlyRevenue.month)
        )
        if start_month:
            stmt = stmt.where(NicheMonthlyRevenue.month >= start_month)
        if end_month:
            stmt = stmt.where(NicheMonthlyRevenue.month <= end_month)

        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        if rows:
            return rows

        return await self._build_history_from_transactions(
            mcc_code=mcc_code,
            city=city,
            start_month=start_month,
            end_month=end_month,
        )

    async def get_recent_new_competitor_count(
        self,
        *,
        mcc_code: str,
        city: str,
        since_month: date,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
    ) -> int:
        stmt = select(Business).where(
            Business.mcc_code == mcc_code,
            Business.city == city,
            Business.registered_date >= since_month,
        )
        if lat is not None and lon is not None and radius_m is not None:
            min_lat, max_lat, min_lon, max_lon = _bounding_box(lat, lon, radius_m)
            stmt = stmt.where(
                Business.lat.between(min_lat, max_lat),
                Business.lon.between(min_lon, max_lon),
            )

        result = await self._session.execute(stmt)
        businesses = list(result.scalars().all())
        if lat is None or lon is None or radius_m is None:
            return len(businesses)
        return sum(
            1
            for business in businesses
            if _haversine_m(lat, lon, business.lat, business.lon) <= radius_m
        )

    async def save_forecast_run(
        self,
        *,
        niche: str,
        mcc_code: str,
        city: str,
        horizon_months: int,
        history_start_date: date,
        history_end_date: date,
        forecast_start_month: date,
        confidence_level: float,
        training_sample_size: int,
        train_mape_pct: float | None,
        train_rmse_uzs,
        anomaly_count: int,
        new_competitor_count_recent: int,
        analysis_summary: str,
        calc_metadata: dict,
        points: list[dict],
    ) -> DemandForecastRun:
        run = DemandForecastRun(
            niche=niche,
            mcc_code=mcc_code,
            city=city,
            horizon_months=horizon_months,
            history_start_date=history_start_date,
            history_end_date=history_end_date,
            forecast_start_month=forecast_start_month,
            confidence_level=confidence_level,
            training_sample_size=training_sample_size,
            train_mape_pct=train_mape_pct,
            train_rmse_uzs=train_rmse_uzs,
            anomaly_count=anomaly_count,
            new_competitor_count_recent=new_competitor_count_recent,
            analysis_summary=analysis_summary,
            calc_metadata=calc_metadata,
            model_name="lstm_prophet_ensemble",
            model_version="mvp-v1",
            algorithm="LSTM + Facebook Prophet",
            status="completed",
        )
        self._session.add(run)
        await self._session.flush()

        for point in points:
            self._session.add(DemandForecastPoint(forecast_run_id=run.id, **point))
        await self._session.flush()
        await self._session.refresh(run, ["points"])
        return run

    async def _build_history_from_transactions(
        self,
        *,
        mcc_code: str,
        city: str,
        start_month: date | None,
        end_month: date | None,
    ) -> list[NicheMonthlyRevenue]:
        month_expr = func.date_trunc("month", Transaction.transaction_date).label(
            "month"
        )
        stmt = (
            select(
                month_expr,
                func.sum(Transaction.amount_uzs).label("revenue_uzs"),
                func.count(Transaction.id).label("transaction_count"),
                MCCCategory.niche_name_uz.label("niche"),
            )
            .join(MCCCategory, MCCCategory.mcc_code == Transaction.mcc_code)
            .where(
                Transaction.mcc_code == mcc_code,
                Transaction.merchant_city == city,
            )
            .group_by(month_expr, MCCCategory.niche_name_uz)
            .order_by(month_expr)
        )
        if start_month:
            stmt = stmt.where(Transaction.transaction_date >= start_month)
        if end_month:
            stmt = stmt.where(Transaction.transaction_date <= end_month)

        result = await self._session.execute(stmt)
        rows = []
        for row in result.all():
            revenue = row.revenue_uzs or 0
            tx_count = row.transaction_count or 0
            avg_check = revenue / tx_count if tx_count else None
            rows.append(
                NicheMonthlyRevenue(
                    mcc_code=mcc_code,
                    niche=row.niche,
                    city=city,
                    month=row.month.date(),
                    revenue_uzs=revenue,
                    transaction_count=tx_count,
                    avg_check_uzs=avg_check,
                    source="transactions_runtime_aggregate",
                )
            )
        return rows
