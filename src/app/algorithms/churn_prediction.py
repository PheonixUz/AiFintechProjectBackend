"""M-E2 SMB Churn Prediction algoritmi."""

from dataclasses import dataclass, field
from decimal import Decimal
from math import exp


@dataclass
class ChurnFeatureInput:
    business_age_months: int
    revenue_3m_avg_uzs: Decimal
    revenue_6m_avg_uzs: Decimal
    revenue_12m_avg_uzs: Decimal
    revenue_trend_6m_pct: float
    revenue_volatility_12m_pct: float
    revenue_drop_last_3m_pct: float
    zero_revenue_months_12m: int
    tx_count_3m_avg: float
    tx_count_12m_avg: float
    tx_count_trend_6m_pct: float
    avg_ticket_change_6m_pct: float
    inactive_days_last_90d: int
    competitor_density_score: float
    nearby_closed_businesses_24m: int
    district_failure_rate_24m_pct: float
    macro_risk_score: float
    seasonality_risk_score: float
    data_quality_score: float
    prediction_horizon_months: int = 24


@dataclass
class ChurnRiskFactorResult:
    rank: int
    factor_name: str
    factor_group: str
    factor_value: str
    baseline_value: str
    impact_score: float
    direction: str
    explanation: str


@dataclass
class ChurnPredictionResult:
    closure_probability_24m: float
    survival_probability_24m: float
    risk_bucket: str
    risk_score: float
    confidence_score: float
    top_factors: list[ChurnRiskFactorResult]
    methodology_notes: dict = field(default_factory=dict)


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sigmoid(value: float) -> float:
    return 1 / (1 + exp(-value))


def _risk_bucket(probability: float) -> str:
    if probability >= 0.70:
        return "critical"
    if probability >= 0.45:
        return "high"
    if probability >= 0.25:
        return "medium"
    return "low"


def _impact_items(data: ChurnFeatureInput) -> list[dict]:
    return [
        {
            "name": "revenue_drop_last_3m_pct",
            "group": "revenue",
            "value": data.revenue_drop_last_3m_pct,
            "baseline": 0.10,
            "impact": _clip((data.revenue_drop_last_3m_pct - 0.10) / 0.55, 0, 1) * 0.28,
            "explanation": "So'nggi 3 oy revenue pasayishi",
        },
        {
            "name": "negative_revenue_trend_6m",
            "group": "revenue",
            "value": data.revenue_trend_6m_pct,
            "baseline": 0.00,
            "impact": _clip(-data.revenue_trend_6m_pct / 0.50, 0, 1) * 0.24,
            "explanation": "6 oylik revenue trend",
        },
        {
            "name": "inactive_days_last_90d",
            "group": "activity",
            "value": data.inactive_days_last_90d,
            "baseline": 10,
            "impact": _clip((data.inactive_days_last_90d - 10) / 70, 0, 1) * 0.20,
            "explanation": "So'nggi 90 kunda faol bo'lmagan kunlar",
        },
        {
            "name": "zero_revenue_months_12m",
            "group": "activity",
            "value": data.zero_revenue_months_12m,
            "baseline": 1,
            "impact": _clip((data.zero_revenue_months_12m - 1) / 8, 0, 1) * 0.18,
            "explanation": "12 oy ichida revenue bo'lmagan oylar",
        },
        {
            "name": "revenue_volatility_12m_pct",
            "group": "revenue",
            "value": data.revenue_volatility_12m_pct,
            "baseline": 0.20,
            "impact": _clip((data.revenue_volatility_12m_pct - 0.20) / 0.70, 0, 1)
            * 0.14,
            "explanation": "Revenue tebranishi",
        },
        {
            "name": "tx_count_trend_6m_pct",
            "group": "transactions",
            "value": data.tx_count_trend_6m_pct,
            "baseline": 0.00,
            "impact": _clip(-data.tx_count_trend_6m_pct / 0.50, 0, 1) * 0.16,
            "explanation": "Tranzaksiya soni trendi",
        },
        {
            "name": "competitor_density_score",
            "group": "competition",
            "value": data.competitor_density_score,
            "baseline": 0.35,
            "impact": _clip((data.competitor_density_score - 0.35) / 0.65, 0, 1) * 0.12,
            "explanation": "Radius ichida raqobatchilar zichligi",
        },
        {
            "name": "district_failure_rate_24m_pct",
            "group": "location",
            "value": data.district_failure_rate_24m_pct,
            "baseline": 0.20,
            "impact": _clip((data.district_failure_rate_24m_pct - 0.20) / 0.50, 0, 1)
            * 0.10,
            "explanation": "Tuman bo'yicha yopilish darajasi",
        },
        {
            "name": "macro_risk_score",
            "group": "macro",
            "value": data.macro_risk_score,
            "baseline": 0.25,
            "impact": _clip((data.macro_risk_score - 0.25) / 0.75, 0, 1) * 0.08,
            "explanation": "Makro risk",
        },
    ]


def run_churn_prediction(data: ChurnFeatureInput) -> ChurnPredictionResult:
    """24 oy ichida SMB yopilish ehtimolini hisoblaydi."""
    if data.prediction_horizon_months < 1:
        raise ValueError("prediction_horizon_months musbat bo'lishi kerak")
    if data.revenue_12m_avg_uzs < 0:
        raise ValueError("revenue_12m_avg_uzs manfiy bo'lishi mumkin emas")

    items = _impact_items(data)
    risk_impact = sum(item["impact"] for item in items)
    young_business_risk = 0.08 if data.business_age_months < 24 else 0.0
    low_revenue_scale = 0.08 if data.revenue_3m_avg_uzs < Decimal("10000000") else 0.0
    closed_nearby_risk = _clip(data.nearby_closed_businesses_24m / 12, 0, 1) * 0.08
    horizon_adjustment = _clip(data.prediction_horizon_months / 24, 0.4, 1.5)

    linear_score = (
        -1.85
        + risk_impact * 4.2
        + young_business_risk * 2.0
        + low_revenue_scale * 2.0
        + closed_nearby_risk * 1.4
        + data.seasonality_risk_score * 0.35
    )
    probability = _sigmoid(linear_score) * horizon_adjustment
    probability = round(_clip(probability, 0.02, 0.96), 4)
    survival = round(1 - probability, 4)
    risk_score = round(probability * 100, 1)
    confidence = round(
        _clip(
            0.45
            + data.data_quality_score * 0.38
            + min(data.tx_count_12m_avg / 1500, 0.12)
            - min(data.revenue_volatility_12m_pct * 0.08, 0.08),
            0.20,
            0.95,
        ),
        3,
    )

    ranked_items = sorted(items, key=lambda item: item["impact"], reverse=True)[:3]
    top_factors = [
        ChurnRiskFactorResult(
            rank=idx,
            factor_name=item["name"],
            factor_group=item["group"],
            factor_value=str(round(float(item["value"]), 4)),
            baseline_value=str(item["baseline"]),
            impact_score=round(float(item["impact"]), 4),
            direction="increases_risk",
            explanation=item["explanation"],
        )
        for idx, item in enumerate(ranked_items, start=1)
    ]

    return ChurnPredictionResult(
        closure_probability_24m=probability,
        survival_probability_24m=survival,
        risk_bucket=_risk_bucket(probability),
        risk_score=risk_score,
        confidence_score=confidence,
        top_factors=top_factors,
        methodology_notes={
            "method": "xgboost_style_calibrated_scorecard",
            "model_family": "XGBoost",
            "prediction_horizon_months": data.prediction_horizon_months,
            "risk_impact_sum": round(risk_impact, 4),
            "young_business_risk": young_business_risk,
            "low_revenue_scale_risk": low_revenue_scale,
            "nearby_closure_risk": round(closed_nearby_risk, 4),
        },
    )
