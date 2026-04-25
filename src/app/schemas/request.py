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
