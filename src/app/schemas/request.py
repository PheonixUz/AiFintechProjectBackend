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
    niche: str | None = Field(
        default=None,
        description=(
            "Biznes nishasi. Berilmasa, backend mcc_code orqali "
            "mcc_categories jadvalidan topadi."
        ),
    )
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
    confidence_level: float = Field(
        default=0.95,
        ge=0.80,
        le=0.99,
        description="Ishonch intervali darajasi",
    )
    start_month: date | None = Field(
        default=None,
        description="Tarixiy qator boshlanish oyi (YYYY-MM-01)",
    )
    end_month: date | None = Field(
        default=None,
        description="Tarixiy qator tugash oyi (YYYY-MM-01)",
    )
    annual_inflation_rate_pct: float = Field(
        default=0.12,
        ge=-0.20,
        le=1.00,
        description="Yillik inflatsiya taxmini, masalan 0.12 = 12%",
    )
    annual_macro_growth_pct: float = Field(
        default=0.03,
        ge=-0.50,
        le=0.50,
        description="Makro talab/iqtisodiy o'sish taxmini, masalan 0.03 = 3%",
    )
    use_holiday_adjustments: bool = Field(
        default=True,
        description="Bayram va mavsumiy event flaglarini forecastga qo'shish",
    )
    clean_anomalies: bool = Field(
        default=True,
        description="Tarixiy revenue qatoridagi keskin anomal oylarni winsorize qilish",
    )

    @model_validator(mode="after")
    def normalize_and_validate(self) -> "DemandForecastRequest":
        if self.start_month:
            self.start_month = self.start_month.replace(day=1)
        if self.end_month:
            self.end_month = self.end_month.replace(day=1)
        if self.start_month and self.end_month and self.start_month > self.end_month:
            raise ValueError("start_month end_month dan keyin bo'lishi mumkin emas")
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
