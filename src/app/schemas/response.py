from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MarketSizingResponse(BaseModel):
    niche: str
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
    analysis_summary: str
    methodology_notes: dict
    points: list[DemandForecastPointOut]
