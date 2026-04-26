"""M-E2 Churn Prediction algoritmiga unit testlar."""

from decimal import Decimal

from app.algorithms.churn_prediction import ChurnFeatureInput, run_churn_prediction


def _input(**overrides) -> ChurnFeatureInput:
    data = {
        "business_age_months": 30,
        "revenue_3m_avg_uzs": Decimal("30000000"),
        "revenue_6m_avg_uzs": Decimal("32000000"),
        "revenue_12m_avg_uzs": Decimal("35000000"),
        "revenue_trend_6m_pct": -0.05,
        "revenue_volatility_12m_pct": 0.22,
        "revenue_drop_last_3m_pct": 0.10,
        "zero_revenue_months_12m": 1,
        "tx_count_3m_avg": 500,
        "tx_count_12m_avg": 540,
        "tx_count_trend_6m_pct": -0.04,
        "avg_ticket_change_6m_pct": -0.02,
        "inactive_days_last_90d": 10,
        "competitor_density_score": 0.35,
        "nearby_closed_businesses_24m": 2,
        "district_failure_rate_24m_pct": 0.22,
        "macro_risk_score": 0.25,
        "seasonality_risk_score": 0.18,
        "data_quality_score": 0.80,
        "prediction_horizon_months": 24,
    }
    data.update(overrides)
    return ChurnFeatureInput(**data)


def test_churn_returns_probability_and_top_3_factors():
    result = run_churn_prediction(_input())

    assert 0 <= result.closure_probability_24m <= 1
    assert result.survival_probability_24m == round(
        1 - result.closure_probability_24m,
        4,
    )
    assert len(result.top_factors) == 3
    assert result.risk_bucket in {"low", "medium", "high", "critical"}


def test_high_risk_business_scores_higher_than_stable_business():
    stable = run_churn_prediction(
        _input(
            revenue_trend_6m_pct=0.12,
            revenue_drop_last_3m_pct=0.02,
            revenue_volatility_12m_pct=0.12,
            zero_revenue_months_12m=0,
            tx_count_trend_6m_pct=0.08,
            inactive_days_last_90d=2,
            competitor_density_score=0.15,
        )
    )
    risky = run_churn_prediction(
        _input(
            business_age_months=8,
            revenue_trend_6m_pct=-0.55,
            revenue_drop_last_3m_pct=0.70,
            revenue_volatility_12m_pct=0.80,
            zero_revenue_months_12m=7,
            tx_count_trend_6m_pct=-0.60,
            inactive_days_last_90d=72,
            competitor_density_score=0.90,
        )
    )

    assert risky.closure_probability_24m > stable.closure_probability_24m
    assert risky.risk_score > stable.risk_score
    assert risky.risk_bucket in {"high", "critical"}


def test_revenue_drop_is_top_factor_for_drop_scenario():
    result = run_churn_prediction(
        _input(
            revenue_drop_last_3m_pct=0.80,
            revenue_trend_6m_pct=-0.05,
            inactive_days_last_90d=8,
        )
    )

    assert result.top_factors[0].factor_name == "revenue_drop_last_3m_pct"
