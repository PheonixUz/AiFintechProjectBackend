"""M-B1 Demand Forecasting uchun DB ma'lumot olish funksiyalari."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.forecast_repo import ForecastRepository


async def execute_get_forecast_data(
    session: AsyncSession,
    *,
    mcc_code: str,
    city: str,
    start_month: date | None = None,
    end_month: date | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_m: float | None = None,
) -> dict:
    repo = ForecastRepository(session)

    history = await repo.get_monthly_revenue_history(
        mcc_code=mcc_code,
        city=city,
        start_month=start_month,
        end_month=end_month,
    )
    recent_new_competitor_count = 0
    if history:
        recent_since = history[-12].month if len(history) >= 12 else history[0].month
        recent_new_competitor_count = await repo.get_recent_new_competitor_count(
            mcc_code=mcc_code,
            city=city,
            since_month=recent_since,
            lat=lat,
            lon=lon,
            radius_m=radius_m,
        )

    return {
        "history": history,
        "recent_new_competitor_count": recent_new_competitor_count,
    }
