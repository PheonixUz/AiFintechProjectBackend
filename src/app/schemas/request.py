from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class MarketSizingRequest(BaseModel):
    mcc_code: str = Field(
        ..., min_length=4, max_length=4, description="MCC kod (4 raqam)"
    )
    lat: float = Field(..., ge=-90, le=90, description="Kenglik (latitude)")
    lon: float = Field(..., ge=-180, le=180, description="Uzunlik (longitude)")
    radius_m: float = Field(
        default=1000, ge=100, le=10_000, description="Tahlil radiusi (metr)"
    )
    city: str = Field(default="Toshkent", description="Shahar nomi")
    capital_uzs: Decimal = Field(..., gt=0, description="Boshlang'ich kapital (UZS)")
    year: int = Field(default=2025, ge=2020, le=2030, description="Tahlil yili")


class DemandForecastRequest(BaseModel):
    mcc_code: str = Field(
        ..., min_length=4, max_length=4, description="MCC kod (4 raqam)"
    )
    city: str = Field(default="Toshkent", description="Shahar nomi")
    lat: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Ixtiyoriy lokatsiya latitude; local competitor pressure uchun",
    )
    lon: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Ixtiyoriy lokatsiya longitude; local competitor pressure uchun",
    )
    radius_m: float | None = Field(
        default=None,
        ge=100,
        le=20_000,
        description="Ixtiyoriy lokatsiya radiusi; local competitor pressure uchun",
    )
    horizon_months: int = Field(
        default=12,
        description="Prognoz gorizonti: 12, 24 yoki 36 oy",
    )

    @model_validator(mode="after")
    def normalize_and_validate(self) -> "DemandForecastRequest":
        location_values = [
            self.lat is not None,
            self.lon is not None,
            self.radius_m is not None,
        ]
        if any(location_values) and not all(location_values):
            raise ValueError("lat, lon va radius_m birga berilishi kerak")
        return self


class ViabilityCheckRequest(BaseModel):
    """M-D1 Financial Viability Check request."""

    plan_name: str | None = Field(
        default=None,
        max_length=200,
        description="Biznes-plan nomi yoki scenario nomi",
    )
    niche: str | None = Field(
        default=None,
        description="Biznes nishasi; berilmasa mcc_code orqali aniqlanadi",
    )
    mcc_code: str = Field(
        ..., min_length=4, max_length=4, description="MCC kod (4 raqam)"
    )
    city: str = Field(default="Toshkent", description="Shahar nomi")
    lat: float | None = Field(default=None, ge=-90, le=90, description="Latitude")
    lon: float | None = Field(default=None, ge=-180, le=180, description="Longitude")
    radius_m: float | None = Field(
        default=None,
        ge=100,
        le=20_000,
        description="Raqobatchi va lokatsiya riskini baholash radiusi",
    )

    simulation_months: int = Field(
        default=24,
        ge=12,
        le=36,
        description="Moliyaviy model davri; odatda 24 oy",
    )
    monte_carlo_iterations: int = Field(
        default=2000,
        ge=500,
        le=20_000,
        description="Monte Carlo simulyatsiya soni",
    )
    random_seed: int | None = Field(
        default=None,
        description="Deterministik test uchun seed; productionda bermasa ham bo'ladi",
    )

    initial_capital_uzs: Decimal = Field(
        ..., gt=0, description="Boshlang'ich mavjud kapital"
    )
    startup_capex_uzs: Decimal | None = Field(
        default=None,
        ge=0,
        description="Ish boshlash uchun bir martalik CAPEX",
    )
    loan_amount_uzs: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Kredit summasi",
    )
    monthly_loan_payment_uzs: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Har oylik kredit to'lovi",
    )

    expected_monthly_revenue_uzs: Decimal | None = Field(
        default=None,
        gt=0,
        description="1-oy kutilayotgan oylik revenue",
    )
    avg_ticket_uzs: Decimal | None = Field(
        default=None,
        gt=0,
        description="O'rtacha chek",
    )
    expected_monthly_transactions: int | None = Field(
        default=None,
        gt=0,
        description="Oylik tranzaksiyalar soni",
    )

    gross_margin_pct: float | None = Field(
        default=None,
        gt=0,
        lt=1,
        description="Yalpi marja, masalan 0.35 = 35%",
    )
    variable_cost_pct: float | None = Field(
        default=None,
        ge=0,
        lt=1,
        description="Revenuega nisbatan variable cost",
    )
    monthly_fixed_cost_uzs: Decimal | None = Field(
        default=None,
        ge=0,
        description="Jami oylik fixed cost",
    )
    monthly_rent_uzs: Decimal = Field(default=Decimal("0"), ge=0)
    monthly_payroll_uzs: Decimal = Field(default=Decimal("0"), ge=0)
    monthly_utilities_uzs: Decimal = Field(default=Decimal("0"), ge=0)
    monthly_marketing_uzs: Decimal = Field(default=Decimal("0"), ge=0)
    monthly_other_fixed_uzs: Decimal = Field(default=Decimal("0"), ge=0)
    owner_draw_uzs: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Founder/owner har oy biznesdan oladigan summa",
    )

    monthly_revenue_growth_pct: float | None = Field(
        default=None,
        ge=-0.50,
        le=0.50,
        description="Oylik revenue o'sishi, masalan 0.015 = 1.5%",
    )
    revenue_volatility_pct: float | None = Field(
        default=None,
        ge=0.01,
        le=2.0,
        description="Revenue noaniqligi/std, masalan 0.20 = 20%",
    )
    annual_inflation_rate_pct: float = Field(
        default=0.12,
        ge=-0.20,
        le=1.00,
        description="Yillik inflatsiya taxmini",
    )
    annual_macro_growth_pct: float = Field(
        default=0.03,
        ge=-0.50,
        le=0.50,
        description="Yillik makro talab o'sishi",
    )
    tax_rate_pct: float = Field(default=0.04, ge=0, le=0.50)
    seasonality_profile: dict[str, float] | None = Field(
        default=None,
        description="Oy bo'yicha seasonality: {'1': 0.95, '12': 1.15}",
    )
    risk_assumptions: dict | None = Field(
        default=None,
        description="Qo'shimcha risk sozlamalari",
    )
    clean_anomalies: bool = Field(
        default=True,
        description="Ekstremal simulyatsiya natijalarini winsorize qilish",
    )

    @model_validator(mode="after")
    def validate_financial_assumptions(self) -> "ViabilityCheckRequest":
        location_values = [
            self.lat is not None,
            self.lon is not None,
            self.radius_m is not None,
        ]
        if any(location_values) and not all(location_values):
            raise ValueError("lat, lon va radius_m birga berilishi kerak")
        if self.variable_cost_pct is None and self.gross_margin_pct is None:
            return self
        if self.variable_cost_pct is None and self.gross_margin_pct is not None:
            self.variable_cost_pct = round(1 - self.gross_margin_pct, 6)
        if self.gross_margin_pct is None and self.variable_cost_pct is not None:
            self.gross_margin_pct = round(1 - self.variable_cost_pct, 6)
        total = (self.gross_margin_pct or 0) + (self.variable_cost_pct or 0)
        if abs(total - 1.0) > 0.08:
            raise ValueError(
                "gross_margin_pct + variable_cost_pct taxminan 1.0 bo'lishi kerak"
            )
        if self.seasonality_profile:
            for key, value in self.seasonality_profile.items():
                if not key.isdigit() or int(key) < 1 or int(key) > 12:
                    raise ValueError(
                        "seasonality_profile oy kalitlari 1..12 bo'lishi kerak"
                    )
                if value <= 0 or value > 3:
                    raise ValueError(
                        "seasonality_profile qiymatlari 0 dan katta bo'lishi kerak"
                    )
        return self


class ChurnPredictionRequest(BaseModel):
    """M-E2 SMB Churn Prediction request."""

    business_id: int | None = Field(
        default=None,
        gt=0,
        description="Mavjud biznes IDsi. Berilsa biznes DBdan olinadi.",
    )
    mcc_code: str | None = Field(
        default=None,
        min_length=4,
        max_length=4,
        description="MCC kod. business_id berilmasa majburiy.",
    )
    niche: str | None = Field(
        default=None,
        description="Biznes nishasi. Berilmasa MCC yoki business orqali aniqlanadi.",
    )
    city: str = Field(default="Toshkent", description="Shahar nomi")
    district: str | None = Field(default=None, description="Tuman nomi")
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    radius_m: float | None = Field(default=1000, ge=100, le=20_000)
    as_of_date: date | None = Field(
        default=None,
        description="Scoring sanasi. Berilmasa bugungi sana ishlatiladi.",
    )
    prediction_horizon_months: int = Field(
        default=24,
        ge=6,
        le=36,
        description="Yopilish ehtimoli gorizonti. M-E2 uchun odatda 24 oy.",
    )

    business_age_months: int | None = Field(default=None, ge=0, le=600)
    employee_count_est: int | None = Field(default=None, ge=0, le=500)
    area_sqm: float | None = Field(default=None, ge=1, le=100_000)

    revenue_3m_avg_uzs: Decimal | None = Field(default=None, ge=0)
    revenue_6m_avg_uzs: Decimal | None = Field(default=None, ge=0)
    revenue_12m_avg_uzs: Decimal | None = Field(default=None, ge=0)
    revenue_trend_6m_pct: float | None = Field(default=None, ge=-1.0, le=2.0)
    revenue_volatility_12m_pct: float | None = Field(default=None, ge=0, le=3.0)
    revenue_drop_last_3m_pct: float | None = Field(default=None, ge=0, le=1.0)
    zero_revenue_months_12m: int | None = Field(default=None, ge=0, le=12)

    tx_count_3m_avg: float | None = Field(default=None, ge=0)
    tx_count_12m_avg: float | None = Field(default=None, ge=0)
    tx_count_trend_6m_pct: float | None = Field(default=None, ge=-1.0, le=2.0)
    avg_ticket_3m_uzs: Decimal | None = Field(default=None, ge=0)
    avg_ticket_change_6m_pct: float | None = Field(default=None, ge=-1.0, le=2.0)

    active_days_last_90d: int | None = Field(default=None, ge=0, le=90)
    inactive_days_last_90d: int | None = Field(default=None, ge=0, le=90)
    online_share_12m_pct: float | None = Field(default=None, ge=0, le=1)

    competitor_count_radius: int | None = Field(default=None, ge=0, le=10_000)
    competitor_density_score: float | None = Field(default=None, ge=0, le=1)
    nearby_closed_businesses_24m: int | None = Field(default=None, ge=0, le=10_000)
    district_failure_rate_24m_pct: float | None = Field(default=None, ge=0, le=1)
    macro_risk_score: float | None = Field(default=None, ge=0, le=1)
    seasonality_risk_score: float | None = Field(default=None, ge=0, le=1)
    data_quality_score: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_churn_request(self) -> "ChurnPredictionRequest":
        if self.business_id is None and self.mcc_code is None:
            raise ValueError("business_id yoki mcc_code dan kamida bittasi kerak")
        location_values = [self.lat is not None, self.lon is not None]
        if any(location_values) and not all(location_values):
            raise ValueError("lat va lon birga berilishi kerak")
        if (
            self.active_days_last_90d is not None
            and self.inactive_days_last_90d is not None
            and self.active_days_last_90d + self.inactive_days_last_90d > 90
        ):
            raise ValueError("active_days_last_90d + inactive_days_last_90d <= 90")
        return self
