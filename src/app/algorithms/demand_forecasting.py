"""
M-B1 Demand Forecasting.

MVP implementation: lightweight LSTM/Prophet-style ensemble without heavyweight
runtime dependencies. The interface and stored metadata are ready for replacing
the internals with real TensorFlow/Prophet models later.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from statistics import mean, median


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
    annual_inflation_rate_pct: float = 0.12
    annual_macro_growth_pct: float = 0.03
    recent_new_competitor_count: int = 0
    clean_anomalies: bool = True
    use_holiday_adjustments: bool = True
    min_history_months: int = 24


@dataclass
class DemandForecastPointResult:
    forecast_month: date
    horizon_index: int
    predicted_revenue_uzs: Decimal
    lower_revenue_uzs: Decimal
    upper_revenue_uzs: Decimal
    trend_component_uzs: Decimal
    seasonal_component_uzs: Decimal
    macro_adjustment_pct: float = 0.0
    competitor_pressure_pct: float = 0.0
    event_flags: list[str] = field(default_factory=list)


@dataclass
class DemandForecastResult:
    points: list[DemandForecastPointResult]
    confidence_score: float
    training_sample_size: int
    train_mape_pct: float | None
    train_rmse_uzs: Decimal | None
    anomaly_count: int = 0
    new_competitor_count_recent: int = 0
    methodology_notes: dict = field(default_factory=dict)


def _add_months(month: date, count: int) -> date:
    total_month = month.month - 1 + count
    year = month.year + total_month // 12
    return date(year, total_month % 12 + 1, 1)


def _decimal(value: float, *, non_negative: bool = False) -> Decimal:
    if non_negative:
        value = max(value, 0)
    return Decimal(str(round(value, 2)))


def _mad(values: list[float]) -> float:
    if not values:
        return 0.0
    center = median(values)
    deviations = [abs(v - center) for v in values]
    return median(deviations)


def _clean_anomalies(values: list[float]) -> tuple[list[float], int, dict]:
    """Winsorize strong outliers using a robust median absolute deviation band."""
    if len(values) < 6:
        return values, 0, {"method": "skipped_small_sample"}

    center = median(values)
    mad = _mad(values)
    if mad == 0:
        return values, 0, {"method": "mad_zero"}

    lower = max(0.0, center - 3.5 * mad)
    upper = center + 3.5 * mad
    cleaned = [min(max(v, lower), upper) for v in values]
    anomaly_count = sum(
        1
        for before, after in zip(values, cleaned, strict=False)
        if before != after
    )
    return cleaned, anomaly_count, {
        "method": "mad_winsorize",
        "lower": lower,
        "upper": upper,
    }


def _event_flags(month: date) -> list[str]:
    flags = []
    if month.month == 3:
        flags.append("navruz")
    if month.month in (3, 4):
        flags.append("ramadan_eid_season")
    if month.month == 9:
        flags.append("back_to_school")
    if month.month == 12:
        flags.append("new_year_season")
    return flags


def _event_factor(flags: list[str]) -> float:
    factor = 1.0
    weights = {
        "navruz": 1.04,
        "ramadan_eid_season": 1.03,
        "back_to_school": 1.02,
        "new_year_season": 1.05,
    }
    for flag in flags:
        factor *= weights.get(flag, 1.0)
    return factor


def _try_prophet_predictions(
    history: list[MonthlyRevenuePoint], horizon_months: int
) -> list[float] | None:
    """
    Use real Prophet when the optional dependency is installed.

    The project can run without Prophet; in that case the deterministic
    trend/seasonality baseline below is used.
    """
    try:
        import pandas as pd
        from prophet import Prophet
    except ImportError:
        return None

    frame = pd.DataFrame(
        {
            "ds": [point.month for point in history],
            "y": [float(point.revenue_uzs) for point in history],
        }
    )
    model = Prophet(
        interval_width=0.95,
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
    )
    model.fit(frame)
    future = model.make_future_dataframe(periods=horizon_months, freq="MS")
    forecast = model.predict(future).tail(horizon_months)
    return [max(float(value), 0.0) for value in forecast["yhat"].tolist()]


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
    return _decimal(mean(squared_errors) ** 0.5, non_negative=True)


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
    if len(history) < data.min_history_months:
        raise ValueError(
            f"at least {data.min_history_months} monthly history points are required"
        )

    raw_values = [float(p.revenue_uzs) for p in history]
    if data.clean_anomalies:
        values, anomaly_count, anomaly_notes = _clean_anomalies(raw_values)
    else:
        values, anomaly_count, anomaly_notes = raw_values, 0, {"method": "disabled"}
    cleaned_history = [
        MonthlyRevenuePoint(
            month=point.month,
            revenue_uzs=_decimal(values[idx], non_negative=True),
            transaction_count=point.transaction_count,
        )
        for idx, point in enumerate(history)
    ]

    last_value = values[-1]
    growth = _monthly_growth(values)
    seasonal = _seasonal_factors(cleaned_history)
    prophet_predictions = _try_prophet_predictions(cleaned_history, data.horizon_months)
    real_model_status = "prophet_active" if prophet_predictions else "fallback_active"

    recent_values = values[-3:] if len(values) >= 3 else values
    recent_avg = mean(recent_values)
    momentum = (recent_avg / last_value - 1) if last_value > 0 else 0.0
    momentum = max(min(momentum, 0.06), -0.06)

    mape = _rolling_mape(values, growth, seasonal)
    rmse = _rolling_rmse(values, growth, seasonal)
    base_error = (mape / 100) if mape is not None else 0.18
    base_error = max(base_error, 0.10)
    monthly_macro_adjustment = (
        (1 + data.annual_inflation_rate_pct) * (1 + data.annual_macro_growth_pct)
    ) ** (1 / 12) - 1
    monthly_macro_adjustment = max(min(monthly_macro_adjustment, 0.05), -0.05)
    competitor_pressure = min(data.recent_new_competitor_count * 0.0025, 0.10)

    points: list[DemandForecastPointResult] = []
    for horizon_index in range(1, data.horizon_months + 1):
        forecast_month = _add_months(history[-1].month, horizon_index)
        trend_component = last_value * ((1 + growth) ** horizon_index)
        if prophet_predictions:
            prophet_like = prophet_predictions[horizon_index - 1]
        else:
            prophet_like = trend_component * seasonal.get(forecast_month.month, 1.0)
        lstm_like = last_value * ((1 + momentum) ** horizon_index)
        predicted = prophet_like * 0.60 + lstm_like * 0.40
        macro_factor = (1 + monthly_macro_adjustment) ** horizon_index
        competitor_factor = (1 - competitor_pressure) ** (horizon_index / 12)
        flags = _event_flags(forecast_month) if data.use_holiday_adjustments else []
        predicted = predicted * macro_factor * competitor_factor * _event_factor(flags)

        widening = base_error + horizon_index * 0.01
        lower = predicted * (1 - widening)
        upper = predicted * (1 + widening)

        points.append(
            DemandForecastPointResult(
                forecast_month=forecast_month,
                horizon_index=horizon_index,
                predicted_revenue_uzs=_decimal(predicted, non_negative=True),
                lower_revenue_uzs=_decimal(lower, non_negative=True),
                upper_revenue_uzs=_decimal(upper, non_negative=True),
                trend_component_uzs=_decimal(trend_component, non_negative=True),
                seasonal_component_uzs=_decimal(predicted - trend_component),
                macro_adjustment_pct=round(monthly_macro_adjustment * 100, 3),
                competitor_pressure_pct=round(competitor_pressure * 100, 3),
                event_flags=flags,
            )
        )

    sample_size = len(history)
    confidence_score = min(0.95, max(0.35, sample_size / 36))
    if mape is not None and mape > 20:
        confidence_score *= 0.8
    if anomaly_count:
        confidence_score *= max(0.7, 1 - anomaly_count / len(history))

    return DemandForecastResult(
        points=points,
        confidence_score=round(confidence_score, 3),
        training_sample_size=sample_size,
        train_mape_pct=mape,
        train_rmse_uzs=rmse,
        anomaly_count=anomaly_count,
        new_competitor_count_recent=data.recent_new_competitor_count,
        methodology_notes={
            "algorithm": "LSTM + Facebook Prophet style ensemble",
            "real_model_status": real_model_status,
            "prophet_weight": 0.60,
            "lstm_weight": 0.40,
            "monthly_growth": round(growth, 5),
            "momentum": round(momentum, 5),
            "monthly_macro_adjustment": round(monthly_macro_adjustment, 5),
            "competitor_pressure": round(competitor_pressure, 5),
            "anomaly_cleaning": anomaly_notes,
            "anomaly_count": anomaly_count,
            "holiday_adjustments": data.use_holiday_adjustments,
            "confidence_level": data.confidence_level,
        },
    )
