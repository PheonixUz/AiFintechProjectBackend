"""M-B1 Demand Forecasting algoritmiga unit testlar."""

from datetime import date
from decimal import Decimal

import pytest

from app.algorithms.demand_forecasting import (
    DemandForecastInput,
    MonthlyRevenuePoint,
    run_demand_forecast,
)


def _history(months: int = 24) -> list[MonthlyRevenuePoint]:
    rows = []
    for idx in range(months):
        year = 2024 + idx // 12
        month = idx % 12 + 1
        revenue = Decimal("100000000") + Decimal(idx * 2_000_000)
        rows.append(
            MonthlyRevenuePoint(
                month=date(year, month, 1),
                revenue_uzs=revenue,
                transaction_count=1000 + idx,
            )
        )
    return rows


def test_forecast_returns_requested_horizon():
    result = run_demand_forecast(
        DemandForecastInput(history=_history(), horizon_months=12)
    )

    assert len(result.points) == 12
    assert result.points[0].horizon_index == 1
    assert result.points[-1].horizon_index == 12


def test_forecast_interval_wraps_prediction():
    result = run_demand_forecast(
        DemandForecastInput(history=_history(), horizon_months=24)
    )

    for point in result.points:
        assert point.lower_revenue_uzs <= point.predicted_revenue_uzs
        assert point.predicted_revenue_uzs <= point.upper_revenue_uzs


def test_invalid_horizon_raises():
    with pytest.raises(ValueError):
        run_demand_forecast(DemandForecastInput(history=_history(), horizon_months=18))


def test_empty_history_raises():
    with pytest.raises(ValueError):
        run_demand_forecast(DemandForecastInput(history=[], horizon_months=12))
