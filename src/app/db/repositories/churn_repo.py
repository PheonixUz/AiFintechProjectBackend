"""M-E2 Churn Prediction repository."""

from datetime import date

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.business import Business
from app.db.models.churn import (
    ChurnFeatureSnapshot,
    ChurnModelVersion,
    ChurnPredictionRun,
    ChurnRiskFactor,
)
from app.db.models.transaction import MCCCategory


class ChurnRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_business(self, business_id: int) -> Business | None:
        result = await self._session.execute(
            select(Business).where(Business.id == business_id)
        )
        return result.scalar_one_or_none()

    async def get_mcc_category(self, mcc_code: str) -> MCCCategory | None:
        result = await self._session.execute(
            select(MCCCategory).where(MCCCategory.mcc_code == mcc_code)
        )
        return result.scalar_one_or_none()

    async def get_active_model_version(self) -> ChurnModelVersion | None:
        result = await self._session.execute(
            select(ChurnModelVersion)
            .where(ChurnModelVersion.is_active.is_(True))
            .order_by(desc(ChurnModelVersion.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_feature_snapshot(
        self,
        business_id: int,
    ) -> ChurnFeatureSnapshot | None:
        result = await self._session.execute(
            select(ChurnFeatureSnapshot)
            .where(ChurnFeatureSnapshot.business_id == business_id)
            .order_by(desc(ChurnFeatureSnapshot.as_of_date))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_competitor_count(
        self,
        *,
        mcc_code: str,
        city: str,
    ) -> int:
        result = await self._session.execute(
            select(func.count(Business.id)).where(
                Business.mcc_code == mcc_code,
                Business.city == city,
                Business.is_active.is_(True),
            )
        )
        return int(result.scalar() or 0)

    async def get_district_failure_rate(
        self,
        *,
        mcc_code: str,
        city: str,
        district: str | None,
    ) -> float:
        stmt = select(Business).where(
            Business.mcc_code == mcc_code,
            Business.city == city,
        )
        if district:
            stmt = stmt.where(Business.district == district)
        result = await self._session.execute(stmt)
        businesses = list(result.scalars().all())
        if not businesses:
            return 0.25
        closed = sum(1 for business in businesses if not business.is_active)
        return round(closed / len(businesses), 4)

    async def save_prediction(
        self,
        *,
        snapshot_payload: dict,
        run_payload: dict,
        risk_factor_payloads: list[dict],
    ) -> ChurnPredictionRun:
        snapshot = ChurnFeatureSnapshot(**snapshot_payload)
        self._session.add(snapshot)
        await self._session.flush()

        run = ChurnPredictionRun(
            feature_snapshot_id=snapshot.id,
            **run_payload,
        )
        self._session.add(run)
        await self._session.flush()

        self._session.add_all(
            [
                ChurnRiskFactor(prediction_run_id=run.id, **payload)
                for payload in risk_factor_payloads
            ]
        )
        await self._session.flush()
        await self._session.refresh(run, ["risk_factors"])
        return run


DEFAULT_CHURN_FEATURES = {
    "business_age_months": 18,
    "revenue_trend_6m_pct": -0.05,
    "revenue_volatility_12m_pct": 0.24,
    "revenue_drop_last_3m_pct": 0.12,
    "zero_revenue_months_12m": 1,
    "tx_count_3m_avg": 300.0,
    "tx_count_12m_avg": 360.0,
    "tx_count_trend_6m_pct": -0.03,
    "avg_ticket_change_6m_pct": -0.02,
    "inactive_days_last_90d": 12,
    "online_share_12m_pct": 0.12,
    "competitor_density_score": 0.35,
    "nearby_closed_businesses_24m": 2,
    "district_failure_rate_24m_pct": 0.25,
    "macro_risk_score": 0.25,
    "seasonality_risk_score": 0.18,
    "data_quality_score": 0.75,
    "revenue_3m_avg_uzs": 20_000_000,
    "revenue_6m_avg_uzs": 22_000_000,
    "revenue_12m_avg_uzs": 24_000_000,
}


def months_between(start: date, end: date) -> int:
    return max(0, (end.year - start.year) * 12 + end.month - start.month)
