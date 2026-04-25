"""
M-B1 Demand Forecasting.

MVP implementation: lightweight LSTM/Prophet-style ensemble without heavyweight
runtime dependencies. The interface and stored metadata are ready for replacing
the internals with real TensorFlow/Prophet models later.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from statistics import mean


@dataclass
class MonthlyRevenuePoint:
    month: date
    revenue_uzs: Decimal
    transaction_count: int = 0


@dataclass
class DemandForecastInput:
    history: list[MonthlyRevenuePoint]
    horizon_months: int
    confidence_level: float = 0.95


@dataclass
class DemandForecastPointResult:
    forecast_month: date
    horizon_index: int
    predicted_revenue_uzs: Decimal
    lower_revenue_uzs: Decimal
    upper_revenue_uzs: Decimal
    trend_component_uzs: Decimal
    seasonal_component_uzs: Decimal


@dataclass
class DemandForecastResult:
    points: list[DemandForecastPointResult]
    confidence_score: float
    training_sample_size: int
    train_mape_pct: float | None
    train_rmse_uzs: Decimal | None
    methodology_notes: dict = field(default_factory=dict)


def _add_months(month: date, count: int) -> date:
    total_month = month.month - 1 + count
    year = month.year + total_month // 12
    return date(year, total_month % 12 + 1, 1)


def _safe_decimal(value: float) -> Decimal:
    return Decimal(str(round(max(value, 0), 2)))


def _monthly_growth(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0

    growth_rates = []
    for prev, cur in zip(values, values[1:], strict=False):
        if prev > 0:
            growth_rates.append((cur / prev) - 1)

    if not growth_rates:
        return 0.0

    recent = growth_rates[-6:]
    return max(min(mean(recent), 0.08), -0.08)


def _seasonal_factors(history: list[MonthlyRevenuePoint]) -> dict[int, float]:
    values = [float(p.revenue_uzs) for p in history]
    global_avg = mean(values) if values else 1.0
    if global_avg <= 0:
        return {m: 1.0 for m in range(1, 13)}

    by_month: dict[int, list[float]] = {m: [] for m in range(1, 13)}
    for point in history:
        by_month[point.month.month].append(float(point.revenue_uzs))

    factors = {}
    for month, month_values in by_month.items():
        factors[month] = mean(month_values) / global_avg if month_values else 1.0
    return factors


def _rolling_mape(
    values: list[float], growth: float, seasonal: dict[int, float]
) -> float | None:
    if len(values) < 13:
        return None

    errors = []
    for idx in range(12, len(values)):
        prev = values[idx - 1]
        month = (idx % 12) + 1
        predicted = prev * (1 + growth) * seasonal.get(month, 1.0)
        actual = values[idx]
        if actual > 0:
            errors.append(abs(actual - predicted) / actual)

    if not errors:
        return None
    return round(mean(errors) * 100, 2)


def _rolling_rmse(
    values: list[float], growth: float, seasonal: dict[int, float]
) -> Decimal | None:
    if len(values) < 13:
        return None

    squared_errors = []
    for idx in range(12, len(values)):
        prev = values[idx - 1]
        month = (idx % 12) + 1
        predicted = prev * (1 + growth) * seasonal.get(month, 1.0)
        squared_errors.append((values[idx] - predicted) ** 2)

    if not squared_errors:
        return None
    return _safe_decimal(mean(squared_errors) ** 0.5)


def run_demand_forecast(data: DemandForecastInput) -> DemandForecastResult:
    """
    Forecast revenue for 12/24/36 months with a confidence interval.

    Prophet-style part: trend + monthly seasonality.
    LSTM-style part: recent momentum from the latest 3 months.
    Ensemble: 60% trend/seasonality + 40% momentum.
    """
    if data.horizon_months not in (12, 24, 36):
        raise ValueError("horizon_months must be one of: 12, 24, 36")
    if not data.history:
        raise ValueError("history must contain at least one monthly revenue point")

    history = sorted(data.history, key=lambda p: p.month)
    values = [float(p.revenue_uzs) for p in history]
    last_value = values[-1]
    growth = _monthly_growth(values)
    seasonal = _seasonal_factors(history)

    recent_values = values[-3:] if len(values) >= 3 else values
    recent_avg = mean(recent_values)
    momentum = (recent_avg / last_value - 1) if last_value > 0 else 0.0
    momentum = max(min(momentum, 0.06), -0.06)

    mape = _rolling_mape(values, growth, seasonal)
    rmse = _rolling_rmse(values, growth, seasonal)
    base_error = (mape / 100) if mape is not None else 0.18
    base_error = max(base_error, 0.10)

    points: list[DemandForecastPointResult] = []
    for horizon_index in range(1, data.horizon_months + 1):
        forecast_month = _add_months(history[-1].month, horizon_index)
        trend_component = last_value * ((1 + growth) ** horizon_index)
        prophet_like = trend_component * seasonal.get(forecast_month.month, 1.0)
        lstm_like = last_value * ((1 + momentum) ** horizon_index)
        predicted = prophet_like * 0.60 + lstm_like * 0.40

        widening = base_error + horizon_index * 0.01
        lower = predicted * (1 - widening)
        upper = predicted * (1 + widening)

        points.append(
            DemandForecastPointResult(
                forecast_month=forecast_month,
                horizon_index=horizon_index,
                predicted_revenue_uzs=_safe_decimal(predicted),
                lower_revenue_uzs=_safe_decimal(lower),
                upper_revenue_uzs=_safe_decimal(upper),
                trend_component_uzs=_safe_decimal(trend_component),
                seasonal_component_uzs=_safe_decimal(predicted - trend_component),
            )
        )

    sample_size = len(history)
    confidence_score = min(0.95, max(0.35, sample_size / 36))
    if mape is not None and mape > 20:
        confidence_score *= 0.8

    return DemandForecastResult(
        points=points,
        confidence_score=round(confidence_score, 3),
        training_sample_size=sample_size,
        train_mape_pct=mape,
        train_rmse_uzs=rmse,
        methodology_notes={
            "algorithm": "LSTM + Facebook Prophet style ensemble",
            "prophet_weight": 0.60,
            "lstm_weight": 0.40,
            "monthly_growth": round(growth, 5),
            "momentum": round(momentum, 5),
            "confidence_level": data.confidence_level,
        },
    )
