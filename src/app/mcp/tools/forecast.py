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
) -> dict:
    repo = ForecastRepository(session)

    history = await repo.get_monthly_revenue_history(
        mcc_code=mcc_code,
        city=city,
        start_month=start_month,
        end_month=end_month,
    )

    return {
        "history": history,
    }
