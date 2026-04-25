from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MarketSizingResponse(BaseModel):
    mcc_code: str
    city: str

    # Asosiy natijalar (yillik, UZS)
    tam_uzs: Decimal
    sam_uzs: Decimal
    som_uzs: Decimal

    # Ishonch oralig'i
    tam_low_uzs: Decimal
    tam_high_uzs: Decimal
    sam_low_uzs: Decimal
    sam_high_uzs: Decimal
    som_low_uzs: Decimal
    som_high_uzs: Decimal

    # Kontekst ko'rsatkichlari
    market_share_pct: float
    market_growth_rate_pct: float
    gross_margin_pct: float
    competitor_count_radius: int
    confidence_score: float

    # Metodologiya
    data_weight: float
    methodology_notes: dict

    # Claude tahlili (o'zbek tilida)
    analysis_summary: str

    # Keshdan kelganmi
    from_cache: bool = False


class DemandForecastPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    forecast_month: date
    horizon_index: int
    predicted_revenue_uzs: Decimal
    lower_revenue_uzs: Decimal
    upper_revenue_uzs: Decimal
    trend_component_uzs: Decimal | None = None
    seasonal_component_uzs: Decimal | None = None
    macro_adjustment_pct: float = 0.0
    competitor_pressure_pct: float = 0.0
    event_flags: list[str] = []
    confidence_level: float


class DemandForecastResponse(BaseModel):
    niche: str
    mcc_code: str
    city: str
    horizon_months: int
    confidence_level: float
    confidence_score: float
    training_sample_size: int
    train_mape_pct: float | None = None
    train_rmse_uzs: Decimal | None = None
    anomaly_count: int = 0
    new_competitor_count_recent: int = 0
    analysis_summary: str
    methodology_notes: dict
    points: list[DemandForecastPointOut]


class ViabilityCashflowMonthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    month_index: int
    expected_revenue_uzs: Decimal
    p10_revenue_uzs: Decimal
    p90_revenue_uzs: Decimal
    variable_cost_uzs: Decimal
    fixed_cost_uzs: Decimal
    loan_payment_uzs: Decimal
    tax_uzs: Decimal
    net_cashflow_uzs: Decimal
    cumulative_cash_p10_uzs: Decimal
    cumulative_cash_p50_uzs: Decimal
    cumulative_cash_p90_uzs: Decimal
    probability_negative_cash: float
    is_break_even_month: bool


class ViabilityCheckResponse(BaseModel):
    run_id: int
    assumption_id: int | None
    niche: str
    mcc_code: str
    city: str
    simulation_months: int
    monte_carlo_iterations: int
    break_even_month: int | None
    runway_months: float
    survival_probability_24m: float
    cash_out_probability_24m: float
    probability_break_even_24m: float
    median_final_cash_uzs: Decimal
    p10_final_cash_uzs: Decimal
    p90_final_cash_uzs: Decimal
    worst_month_cash_uzs: Decimal
    min_required_capital_uzs: Decimal
    viability_score: float
    recommendation: str
    confidence_score: float
    analysis_summary: str
    methodology_notes: dict
    cashflow_months: list[ViabilityCashflowMonthOut]
