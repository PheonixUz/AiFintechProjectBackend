"""M-E2 SMB Churn Prediction agenti."""

import logging
from datetime import date
from decimal import Decimal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.churn_prediction import (
    ChurnFeatureInput,
    ChurnPredictionResult,
    run_churn_prediction,
)
from app.config import settings
from app.db.models.business import Business
from app.db.models.churn import ChurnFeatureSnapshot
from app.db.repositories.churn_repo import (
    DEFAULT_CHURN_FEATURES,
    ChurnRepository,
    months_between,
)
from app.schemas.request import ChurnPredictionRequest
from app.schemas.response import ChurnPredictionResponse, ChurnRiskFactorOut

logger = logging.getLogger(__name__)


def _money(value: Decimal) -> str:
    return f"{float(value) / 1_000_000:.1f} mln UZS"


def _risk_label(bucket: str) -> str:
    return {
        "low": "past",
        "medium": "o'rta",
        "high": "yuqori",
        "critical": "kritik",
    }.get(bucket, bucket)


def _field_value(
    req: ChurnPredictionRequest,
    snapshot: ChurnFeatureSnapshot | None,
    field: str,
):
    req_value = getattr(req, field, None)
    if req_value is not None:
        return req_value
    if snapshot is not None:
        snapshot_value = getattr(snapshot, field, None)
        if snapshot_value is not None:
            return snapshot_value
    return DEFAULT_CHURN_FEATURES[field]


def _fallback_summary(
    result: ChurnPredictionResult,
    niche: str,
) -> str:
    if result.risk_bucket == "low" and all(
        factor.impact_score < 0.02 for factor in result.top_factors
    ):
        factors = "sezilarli kuchli risk faktor aniqlanmadi"
    else:
        factors = ", ".join(
            f"{factor.explanation} (impact {factor.impact_score:.2f})"
            for factor in result.top_factors
        )
    return (
        f"{niche} uchun 24 oy ichida yopilish ehtimoli "
        f"{result.closure_probability_24m:.0%}. Risk darajasi "
        f"{_risk_label(result.risk_bucket)} ({result.risk_score:.1f}/100). "
        f"Top risk faktorlar: {factors}."
    )


def _build_synthesis_prompt(
    result: ChurnPredictionResult,
    niche: str,
    city: str,
) -> str:
    factor_lines = "\n".join(
        f"{factor.rank}. {factor.explanation}: impact={factor.impact_score}"
        for factor in result.top_factors
    )
    return (
        f"{city} shahrida {niche} SMB uchun M-E2 Churn Prediction tayyor.\n\n"
        f"Yopilish ehtimoli 24 oy: {result.closure_probability_24m:.0%}\n"
        f"Yashab qolish ehtimoli: {result.survival_probability_24m:.0%}\n"
        f"Risk bucket: {result.risk_bucket}\n"
        f"Risk score: {result.risk_score:.1f}/100\n"
        f"Top faktorlar:\n{factor_lines}\n\n"
        "O'zbek tilida bank analitigi sifatida 4-5 gaplik xulosa yoz: "
        "risk sabablari, monitoring signallari va qaror tavsiyasi."
    )


class ChurnPredictionAgent:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ChurnRepository(session)

    async def run(self, req: ChurnPredictionRequest) -> ChurnPredictionResponse:
        as_of_date = req.as_of_date or date.today()
        business: Business | None = None
        latest_snapshot: ChurnFeatureSnapshot | None = None

        if req.business_id is not None:
            business = await self._repo.get_business(req.business_id)
            if business is None:
                raise RuntimeError("Business topilmadi")
            latest_snapshot = await self._repo.get_latest_feature_snapshot(business.id)

        mcc_code = req.mcc_code or (business.mcc_code if business else None)
        if mcc_code is None:
            raise RuntimeError("MCC kodi aniqlanmadi")

        category = await self._repo.get_mcc_category(mcc_code)
        niche = (
            req.niche
            or (business.niche if business else None)
            or (category.niche_name_uz if category else None)
        )
        if niche is None:
            raise RuntimeError("Niche aniqlanmadi")

        city = req.city or (business.city if business else "Toshkent")
        district = req.district or (business.district if business else None)
        lat = req.lat if req.lat is not None else (business.lat if business else None)
        lon = req.lon if req.lon is not None else (business.lon if business else None)

        competitor_count = (
            req.competitor_count_radius
            if req.competitor_count_radius is not None
            else await self._repo.get_competitor_count(mcc_code=mcc_code, city=city)
        )
        district_failure = (
            req.district_failure_rate_24m_pct
            if req.district_failure_rate_24m_pct is not None
            else await self._repo.get_district_failure_rate(
                mcc_code=mcc_code,
                city=city,
                district=district,
            )
        )
        competitor_density = (
            req.competitor_density_score
            if req.competitor_density_score is not None
            else min(1.0, competitor_count / 40)
        )

        business_age_months = int(
            req.business_age_months
            if req.business_age_months is not None
            else months_between(business.registered_date, as_of_date)
            if business
            else _field_value(req, latest_snapshot, "business_age_months")
        )
        inactive_days = int(
            _field_value(req, latest_snapshot, "inactive_days_last_90d")
        )
        active_days = (
            req.active_days_last_90d
            if req.active_days_last_90d is not None
            else max(0, 90 - inactive_days)
        )

        revenue_3m = Decimal(
            str(_field_value(req, latest_snapshot, "revenue_3m_avg_uzs"))
        )
        revenue_6m = Decimal(
            str(_field_value(req, latest_snapshot, "revenue_6m_avg_uzs"))
        )
        revenue_12m = Decimal(
            str(_field_value(req, latest_snapshot, "revenue_12m_avg_uzs"))
        )
        avg_ticket = req.avg_ticket_3m_uzs
        if avg_ticket is None and latest_snapshot is not None:
            avg_ticket = latest_snapshot.avg_ticket_3m_uzs
        if avg_ticket is None:
            tx_3m = float(_field_value(req, latest_snapshot, "tx_count_3m_avg"))
            avg_ticket = revenue_3m / Decimal(str(max(tx_3m, 1)))

        data_quality = float(_field_value(req, latest_snapshot, "data_quality_score"))
        algo_input = ChurnFeatureInput(
            business_age_months=business_age_months,
            revenue_3m_avg_uzs=revenue_3m,
            revenue_6m_avg_uzs=revenue_6m,
            revenue_12m_avg_uzs=revenue_12m,
            revenue_trend_6m_pct=float(
                _field_value(req, latest_snapshot, "revenue_trend_6m_pct")
            ),
            revenue_volatility_12m_pct=float(
                _field_value(req, latest_snapshot, "revenue_volatility_12m_pct")
            ),
            revenue_drop_last_3m_pct=float(
                _field_value(req, latest_snapshot, "revenue_drop_last_3m_pct")
            ),
            zero_revenue_months_12m=int(
                _field_value(req, latest_snapshot, "zero_revenue_months_12m")
            ),
            tx_count_3m_avg=float(
                _field_value(req, latest_snapshot, "tx_count_3m_avg")
            ),
            tx_count_12m_avg=float(
                _field_value(req, latest_snapshot, "tx_count_12m_avg")
            ),
            tx_count_trend_6m_pct=float(
                _field_value(req, latest_snapshot, "tx_count_trend_6m_pct")
            ),
            avg_ticket_change_6m_pct=float(
                _field_value(req, latest_snapshot, "avg_ticket_change_6m_pct")
            ),
            inactive_days_last_90d=inactive_days,
            competitor_density_score=float(competitor_density),
            nearby_closed_businesses_24m=int(
                _field_value(req, latest_snapshot, "nearby_closed_businesses_24m")
            ),
            district_failure_rate_24m_pct=float(district_failure),
            macro_risk_score=float(
                _field_value(req, latest_snapshot, "macro_risk_score")
            ),
            seasonality_risk_score=float(
                _field_value(req, latest_snapshot, "seasonality_risk_score")
            ),
            data_quality_score=data_quality,
            prediction_horizon_months=req.prediction_horizon_months,
        )
        result = run_churn_prediction(algo_input)

        analysis_text = _fallback_summary(result, niche)
        if settings.google_api_key:
            llm = ChatGoogleGenerativeAI(
                model=settings.google_model,
                google_api_key=settings.google_api_key,
            )
            synthesis = await llm.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "Sen bank uchun M-E2 Churn Prediction agentisan. "
                            "Natijani o'zbek tilida, sabablar va risklar bilan yoz."
                        )
                    ),
                    HumanMessage(content=_build_synthesis_prompt(result, niche, city)),
                ]
            )
            if isinstance(synthesis.content, str) and synthesis.content.strip():
                analysis_text = synthesis.content

        model_version = await self._repo.get_active_model_version()
        snapshot_payload = {
            "business_id": business.id if business else None,
            "mcc_code": mcc_code,
            "niche": niche,
            "city": city,
            "district": district,
            "lat": lat,
            "lon": lon,
            "radius_m": req.radius_m,
            "as_of_date": as_of_date,
            "business_age_months": business_age_months,
            "employee_count_est": req.employee_count_est
            or (business.employee_count_est if business else None),
            "area_sqm": req.area_sqm or (business.area_sqm if business else None),
            "revenue_3m_avg_uzs": revenue_3m,
            "revenue_6m_avg_uzs": revenue_6m,
            "revenue_12m_avg_uzs": revenue_12m,
            "revenue_trend_6m_pct": algo_input.revenue_trend_6m_pct,
            "revenue_volatility_12m_pct": algo_input.revenue_volatility_12m_pct,
            "revenue_drop_last_3m_pct": algo_input.revenue_drop_last_3m_pct,
            "zero_revenue_months_12m": algo_input.zero_revenue_months_12m,
            "tx_count_3m_avg": algo_input.tx_count_3m_avg,
            "tx_count_12m_avg": algo_input.tx_count_12m_avg,
            "tx_count_trend_6m_pct": algo_input.tx_count_trend_6m_pct,
            "avg_ticket_3m_uzs": avg_ticket,
            "avg_ticket_change_6m_pct": algo_input.avg_ticket_change_6m_pct,
            "active_days_last_90d": active_days,
            "inactive_days_last_90d": inactive_days,
            "online_share_12m_pct": float(
                _field_value(req, latest_snapshot, "online_share_12m_pct")
            ),
            "competitor_count_radius": competitor_count,
            "competitor_density_score": algo_input.competitor_density_score,
            "nearby_closed_businesses_24m": algo_input.nearby_closed_businesses_24m,
            "district_failure_rate_24m_pct": algo_input.district_failure_rate_24m_pct,
            "macro_risk_score": algo_input.macro_risk_score,
            "seasonality_risk_score": algo_input.seasonality_risk_score,
            "data_quality_score": data_quality,
            "target_closed_within_24m": None,
            "target_closed_date": None,
            "raw_features": {
                "source": "churn_prediction_agent",
                "latest_snapshot_used": latest_snapshot.id if latest_snapshot else None,
            },
        }
        top_names = [factor.factor_name for factor in result.top_factors]
        saved_run = await self._repo.save_prediction(
            snapshot_payload=snapshot_payload,
            run_payload={
                "business_id": business.id if business else None,
                "model_version_id": model_version.id if model_version else None,
                "mcc_code": mcc_code,
                "niche": niche,
                "city": city,
                "as_of_date": as_of_date,
                "prediction_horizon_months": req.prediction_horizon_months,
                "closure_probability_24m": result.closure_probability_24m,
                "survival_probability_24m": result.survival_probability_24m,
                "risk_bucket": result.risk_bucket,
                "risk_score": result.risk_score,
                "confidence_score": result.confidence_score,
                "top_factor_1": top_names[0],
                "top_factor_2": top_names[1],
                "top_factor_3": top_names[2],
                "prediction_summary": analysis_text,
                "calc_metadata": result.methodology_notes,
            },
            risk_factor_payloads=[
                {
                    "rank": factor.rank,
                    "factor_name": factor.factor_name,
                    "factor_group": factor.factor_group,
                    "factor_value": factor.factor_value,
                    "baseline_value": factor.baseline_value,
                    "impact_score": factor.impact_score,
                    "direction": factor.direction,
                    "explanation": factor.explanation,
                }
                for factor in result.top_factors
            ],
        )
        ordered_factors = sorted(saved_run.risk_factors, key=lambda item: item.rank)
        return ChurnPredictionResponse(
            run_id=saved_run.id,
            feature_snapshot_id=saved_run.feature_snapshot_id,
            model_version_id=saved_run.model_version_id,
            business_id=saved_run.business_id,
            niche=saved_run.niche,
            mcc_code=saved_run.mcc_code,
            city=saved_run.city,
            as_of_date=saved_run.as_of_date,
            prediction_horizon_months=saved_run.prediction_horizon_months,
            closure_probability_24m=saved_run.closure_probability_24m,
            survival_probability_24m=saved_run.survival_probability_24m,
            risk_bucket=saved_run.risk_bucket,
            risk_score=saved_run.risk_score,
            confidence_score=saved_run.confidence_score,
            top_factors=[
                ChurnRiskFactorOut.model_validate(factor) for factor in ordered_factors
            ],
            prediction_summary=analysis_text,
            methodology_notes=saved_run.calc_metadata,
        )
