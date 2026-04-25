from decimal import Decimal

from pydantic import BaseModel


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
