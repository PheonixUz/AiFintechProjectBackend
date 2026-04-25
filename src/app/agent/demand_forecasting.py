"""M-B1 Demand Forecasting agenti."""

import logging
from decimal import Decimal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.demand_forecasting import (
    DemandForecastInput,
    DemandForecastResult,
    MonthlyRevenuePoint,
    run_demand_forecast,
)
from app.config import settings
from app.db.repositories.forecast_repo import ForecastRepository
from app.mcp.tools.forecast import execute_get_forecast_data
from app.schemas.request import DemandForecastRequest
from app.schemas.response import DemandForecastPointOut, DemandForecastResponse

logger = logging.getLogger(__name__)


def _format_money(value: Decimal) -> str:
    return f"{float(value) / 1_000_000:.1f} mln UZS"


def _fallback_summary(
    req: DemandForecastRequest,
    result: DemandForecastResult,
    niche: str,
) -> str:
    first = result.points[0]
    last = result.points[-1]
    direction = (
        "o'sish"
        if last.predicted_revenue_uzs >= first.predicted_revenue_uzs
        else "pasayish"
    )
    return (
        f"{niche} uchun {req.horizon_months} oylik prognoz {direction} "
        f"trendini ko'rsatmoqda. Birinchi oy kutilayotgan revenue "
        f"{_format_money(first.predicted_revenue_uzs)}, oxirgi oy esa "
        f"{_format_money(last.predicted_revenue_uzs)}. Ishonch darajasi "
        f"{result.confidence_score:.0%}; interval kengayishi uzoq muddatli "
        "noaniqlik oshishini bildiradi."
    )


def _build_synthesis_prompt(
    req: DemandForecastRequest,
    result: DemandForecastResult,
    niche: str,
) -> str:
    first = result.points[0]
    last = result.points[-1]
    return (
        f"{req.city} shahrida {niche} uchun "
        f"{req.horizon_months} oylik demand forecast tayyor.\n\n"
        f"1-oy forecast: {_format_money(first.predicted_revenue_uzs)} "
        f"({_format_money(first.lower_revenue_uzs)} - "
        f"{_format_money(first.upper_revenue_uzs)})\n"
        f"Oxirgi oy forecast: {_format_money(last.predicted_revenue_uzs)} "
        f"({_format_money(last.lower_revenue_uzs)} - "
        f"{_format_money(last.upper_revenue_uzs)})\n"
        f"History sample: {result.training_sample_size} oy\n"
        f"MAPE: {result.train_mape_pct}\n"
        f"Ishonch: {result.confidence_score:.0%}\n\n"
        "O'zbek tilida 3-5 gaplik biznes xulosa yoz: trend, mavsumiylik, "
        "xavf va qanday ehtiyotkor qaror qilish kerak."
    )


class DemandForecastAgent:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def run(self, req: DemandForecastRequest) -> DemandForecastResponse:
        data = await execute_get_forecast_data(
            self._session,
            mcc_code=req.mcc_code,
            city=req.city,
            start_month=req.start_month,
            end_month=req.end_month,
            lat=req.lat,
            lon=req.lon,
            radius_m=req.radius_m,
        )

        history_rows = data["history"]
        if not history_rows:
            raise RuntimeError("Forecast uchun tarixiy revenue ma'lumotlari topilmadi")
        resolved_niche = req.niche or history_rows[0].niche

        algo_input = DemandForecastInput(
            history=[
                MonthlyRevenuePoint(
                    month=row.month,
                    revenue_uzs=row.revenue_uzs,
                    transaction_count=row.transaction_count,
                )
                for row in history_rows
            ],
            horizon_months=req.horizon_months,
            confidence_level=req.confidence_level,
            annual_inflation_rate_pct=req.annual_inflation_rate_pct,
            annual_macro_growth_pct=req.annual_macro_growth_pct,
            recent_new_competitor_count=data["recent_new_competitor_count"],
            clean_anomalies=req.clean_anomalies,
            use_holiday_adjustments=req.use_holiday_adjustments,
        )
        algo_result = run_demand_forecast(algo_input)

        analysis_text = _fallback_summary(req, algo_result, resolved_niche)
        if settings.google_api_key:
            llm = ChatGoogleGenerativeAI(
                model=settings.google_model,
                google_api_key=settings.google_api_key,
            )
            synthesis = await llm.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "Sen KMB M-B1 Demand Forecasting agentisan. "
                            "Natijani o'zbek tilida, aniq va qisqa yoz."
                        )
                    ),
                    HumanMessage(
                        content=_build_synthesis_prompt(
                            req,
                            algo_result,
                            resolved_niche,
                        )
                    ),
                ]
            )
            if isinstance(synthesis.content, str) and synthesis.content.strip():
                analysis_text = synthesis.content

        repo = ForecastRepository(self._session)
        saved_run = await repo.save_forecast_run(
            niche=resolved_niche,
            mcc_code=req.mcc_code,
            city=req.city,
            horizon_months=req.horizon_months,
            history_start_date=history_rows[0].month,
            history_end_date=history_rows[-1].month,
            forecast_start_month=algo_result.points[0].forecast_month,
            confidence_level=req.confidence_level,
            training_sample_size=algo_result.training_sample_size,
            train_mape_pct=algo_result.train_mape_pct,
            train_rmse_uzs=algo_result.train_rmse_uzs,
            anomaly_count=algo_result.anomaly_count,
            new_competitor_count_recent=algo_result.new_competitor_count_recent,
            analysis_summary=analysis_text,
            calc_metadata=algo_result.methodology_notes,
            points=[
                {
                    "forecast_month": p.forecast_month,
                    "horizon_index": p.horizon_index,
                    "predicted_revenue_uzs": p.predicted_revenue_uzs,
                    "lower_revenue_uzs": p.lower_revenue_uzs,
                    "upper_revenue_uzs": p.upper_revenue_uzs,
                    "trend_component_uzs": p.trend_component_uzs,
                    "seasonal_component_uzs": p.seasonal_component_uzs,
                    "macro_adjustment_pct": p.macro_adjustment_pct,
                    "competitor_pressure_pct": p.competitor_pressure_pct,
                    "event_flags": p.event_flags,
                    "confidence_level": req.confidence_level,
                }
                for p in algo_result.points
            ],
        )

        return DemandForecastResponse(
            niche=resolved_niche,
            mcc_code=req.mcc_code,
            city=req.city,
            horizon_months=req.horizon_months,
            confidence_level=req.confidence_level,
            confidence_score=algo_result.confidence_score,
            training_sample_size=algo_result.training_sample_size,
            train_mape_pct=algo_result.train_mape_pct,
            train_rmse_uzs=algo_result.train_rmse_uzs,
            anomaly_count=algo_result.anomaly_count,
            new_competitor_count_recent=algo_result.new_competitor_count_recent,
            analysis_summary=analysis_text,
            methodology_notes=algo_result.methodology_notes,
            points=[
                DemandForecastPointOut.model_validate(p)
                for p in sorted(saved_run.points, key=lambda p: p.horizon_index)
            ],
        )
